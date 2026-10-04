#!/usr/bin/env python3
"""Generate the open-work board from data the repository already holds.

The repository is the orchestrator and any person or Agent is a worker. This
script derives a machine-readable dispatch surface from files that already
exist (coverage maps, the lessons register, the source-gate queue, staging
READMEs, open deliberation records, and the roadmap execution order). It is a
generator, never a second task database: nothing here assigns, reserves, or
claims work, and the source files stay authoritative.

Usage:
    python scripts/open_work.py --json
    python scripts/open_work.py --markdown
    python scripts/open_work.py --json --output PATH

Board mode skips malformed shapes with warnings. Packet mode (--item WI-nnn)
fails on invalid canonical work-item data and never executes acceptance commands.
Both modes return nonzero for unreadable sources.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCHEMA = "xr-foundry.open_work.v1"

KINDS = (
    "work_item",
    "test_gap",
    "evidence_gap",
    "lesson_gap",
    "family_proposal",
    "staging_promotion",
    "deliberation_open",
    "roadmap_step",
)
BLOCKERS = ("nothing", "unity_editor", "headset", "maintainer", "review_window", "outside_contributor")
LANES = ("routine", "non_routine")
ROUTINE_KINDS = {"work_item", "test_gap", "lesson_gap", "roadmap_step"}
# A work item states what it needs; the board says what that blocks on.
NEEDS_TO_BLOCKER = {
    "none": "nothing",
    "unity_editor": "unity_editor",
    "headset": "headset",
    "maintainer": "maintainer",
    "outside_contributor": "outside_contributor",
}
REPOSITORY_FAMILY = "repository"

COVERAGE_GLOB = "coverage-map*.json"
STANDARDS_DIR = Path("docs") / "standards"
LESSONS_REGISTER = STANDARDS_DIR / "lessons" / "lessons-register.json"
QUEUE_FILE = Path("docs") / "foundry" / "queue" / "next-batch.json"
STAGING_DIR = Path("staging")
DELIBERATIONS_DIR = Path("docs") / "governance" / "deliberations"
ROADMAP_FILE = Path("ROADMAP.md")
CAPABILITY_PROFILES_FILE = Path("docs") / "contributing" / "capability-profiles.json"
WORK_ITEMS_FILE = Path("docs") / "contributing" / "work-items.json"
ROADMAP_HEADING = "Execution order after Inventory"
STAGING_SUMMARY = "needs a Unity run and the maintainer's admission signature"

# Blocker classification, evaluated in this order. The first match wins.
HEADSET_PATTERN = re.compile(r"\bheadsets?\b|\bdevices?\b|device[- ]lab", re.IGNORECASE)
# "Unity" alone also names packages and adapters ("a Core and Unity blueprint"),
# so only the phrases that describe a run, a license, or a consumer count as a
# blocker.
UNITY_PATTERN = re.compile(
    r"unity (?:editor|run|license|consumer|project|tests?)\b|unity-consumer|\bin unity\b"
    r"|\beditor\b|\bcompil|player build|clean consumer"
    r"|consumer (?:run|receipt|upgrade|build|tests?)\b|\bupgrade\b|\brollback\b|\bexercis"
    r"|run_unity_gates",
    re.IGNORECASE,
)
RECEIPT_PATTERN = re.compile(r"\breceipts?\b", re.IGNORECASE)
MAINTAINER_PATTERN = re.compile(
    r"\badmission|\badmit|\bmaintainer|\bsign(?:s|ed|ature|-off)?\b|repository settings?"
    r"|owner-only|\bdecision|\bdecide|\bproposal|\bsteward|\bsecret",
    re.IGNORECASE,
)
WINDOW_PATTERN = re.compile(r"\bwindow", re.IGNORECASE)

# Missing-text classification for coverage clauses.
TEST_PATTERN = re.compile(r"\btests?\b|\bvalidator\b|validation rule", re.IGNORECASE)
EVIDENCE_PATTERN = re.compile(
    r"\breceipts?\b|consumer (?:run|receipt|build|tests?)\b|unity-consumer-tests|player build"
    r"|\bdevices?\b|\bheadsets?\b|\beditor\b|\bexecut|\bupgrade\b|\brollback\b|\breview\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class WorkItem:
    id: str
    kind: str
    family: str
    title: str
    source_path: str
    blocked_on: str
    lane: str
    next_action: str
    evidence_note: str | None = None
    review_not_before: str | None = None
    window_closed: bool | None = None
    pending_dependencies: list[str] = field(default_factory=list)
    source_status: str | None = None


class UnreadableSource(Exception):
    """A source file exists but cannot be read from disk."""


class Collector:
    """Accumulates items and warnings while walking one repository root."""

    def __init__(self, root: Path, now: datetime) -> None:
        self.root = root
        self.now = now
        self.items: list[WorkItem] = []
        self.warnings: list[str] = []

    # -- helpers -----------------------------------------------------------

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except OSError as error:
            raise UnreadableSource(f"{self.rel(path)}: {error}") from error

    def load_json(self, path: Path) -> Any:
        text = self.read_text(path)
        try:
            return json.loads(text)
        except ValueError as error:
            self.warnings.append(f"{self.rel(path)}: invalid JSON ({error})")
            return None

    def warn_shape(self, path: Path, detail: str) -> None:
        self.warnings.append(f"{self.rel(path)}: unexpected shape ({detail})")

    def add(self, **fields: Any) -> None:
        kind = fields["kind"]
        blocked_on = fields["blocked_on"]
        lane = fields.pop("lane", None)
        if lane is None:
            lane = "routine" if blocked_on == "nothing" and kind in ROUTINE_KINDS else "non_routine"
        self.items.append(WorkItem(lane=lane, **fields))

    # -- sources -----------------------------------------------------------

    def collect_coverage_maps(self) -> None:
        base = self.root / STANDARDS_DIR
        if not base.is_dir():
            return
        for path in sorted(base.glob(f"*/{COVERAGE_GLOB}")):
            payload = self.load_json(path)
            if payload is None:
                continue
            if not isinstance(payload, dict):
                self.warn_shape(path, "top level is not an object")
                continue
            family = payload.get("family") or path.parent.name
            gates = payload.get("gates")
            if gates is None and isinstance(payload.get("clauses"), list):
                gates = [{"id": payload.get("package_id") or "clauses", "clauses": payload["clauses"]}]
            if not isinstance(gates, list):
                self.warn_shape(path, "no gates or clauses list")
                continue
            for gate in gates:
                if not isinstance(gate, dict) or not isinstance(gate.get("clauses"), list):
                    self.warn_shape(path, "gate without a clauses list")
                    continue
                for clause in gate["clauses"]:
                    self._collect_clause(path, str(family), gate, clause)

    def _collect_clause(self, path: Path, family: str, gate: dict, clause: Any) -> None:
        if not isinstance(clause, dict) or not clause.get("id"):
            self.warn_shape(path, f"clause without an id in gate {gate.get('id')!r}")
            return
        coverage = str(clause.get("coverage", ""))
        missing_raw = clause.get("missing") or []
        if not isinstance(missing_raw, list):
            self.warn_shape(path, f"clause {clause['id']} has a non-list missing field")
            missing_raw = []
        missing = [str(entry) for entry in missing_raw if str(entry).strip()]
        if coverage not in ("partial", "unmapped") and not missing:
            return
        clause_id = str(clause["id"])
        clause_text = str(clause.get("clause", "")).strip()
        missing_text = "; ".join(missing)
        kind = classify_gap_kind(missing_text)
        blocked_on = classify_blocked_on(f"{clause_text} {missing_text}")
        if kind == "evidence_gap" and blocked_on == "nothing":
            blocked_on = "unity_editor"
        if missing_text:
            verb = "Write the missing test coverage" if kind == "test_gap" else "Produce the missing evidence"
            next_action = f"{verb} for {clause_id}: {missing_text}."
        else:
            next_action = f"Extend coverage for {clause_id} until the map marks it covered."
        evidence_note = None
        if kind == "evidence_gap":
            evidence_note = "The coverage map records authored coverage, not execution; only the named evidence closes this clause."
        self.add(
            id=f"{self.rel(path)}#{clause_id}",
            kind=kind,
            family=family,
            title=f"{clause_id}: {clause_text}" if clause_text else clause_id,
            source_path=self.rel(path),
            blocked_on=blocked_on,
            next_action=next_action,
            evidence_note=evidence_note,
        )

    def collect_lessons(self) -> None:
        path = self.root / LESSONS_REGISTER
        if not path.is_file():
            return
        payload = self.load_json(path)
        if payload is None:
            return
        lessons = payload.get("lessons") if isinstance(payload, dict) else None
        if not isinstance(lessons, list):
            self.warn_shape(path, "no lessons list")
            return
        for lesson in lessons:
            if not isinstance(lesson, dict) or not lesson.get("id"):
                self.warn_shape(path, "lesson without an id")
                continue
            dispositions = lesson.get("dispositions")
            if not isinstance(dispositions, list):
                self.warn_shape(path, f"{lesson['id']} has no dispositions list")
                continue
            for disposition in dispositions:
                if not isinstance(disposition, dict):
                    self.warn_shape(path, f"{lesson['id']} has a non-object disposition")
                    continue
                status = str(disposition.get("status", ""))
                if status not in ("gap", "deferred"):
                    continue
                family = str(disposition.get("family") or REPOSITORY_FAMILY)
                follow_up = str(disposition.get("follow_up", "")).strip()
                rationale = str(disposition.get("rationale", "")).strip()
                lesson_id = str(lesson["id"])
                self.add(
                    id=f"{self.rel(path)}#{lesson_id}/{family}",
                    kind="lesson_gap",
                    source_status=status,
                    family=family,
                    title=f"{lesson_id} ({status}): {lesson.get('title', '')}".strip(),
                    source_path=self.rel(path),
                    blocked_on=classify_blocked_on(f"{follow_up} {rationale}"),
                    next_action=follow_up or f"Record a follow-up for the {status} disposition of {lesson_id}.",
                    evidence_note=rationale or None,
                )

    def collect_queue(self) -> None:
        path = self.root / QUEUE_FILE
        if not path.is_file():
            return
        payload = self.load_json(path)
        if payload is None:
            return
        candidates = payload.get("candidates") if isinstance(payload, dict) else None
        if not isinstance(candidates, list):
            self.warn_shape(path, "no candidates list")
            return
        for candidate in candidates:
            if not isinstance(candidate, dict) or not candidate.get("id"):
                self.warn_shape(path, "candidate without an id")
                continue
            candidate_id = str(candidate["id"])
            family = str(candidate.get("family") or re.sub(r"^next-", "", candidate_id.casefold()))
            action = str(candidate.get("exact_next_action", "")).strip()
            blocked_on = classify_blocked_on(action)
            if blocked_on == "nothing":
                blocked_on = "maintainer"
            self.add(
                id=f"{self.rel(path)}#{candidate_id}",
                kind="family_proposal",
                family=family,
                title=f"{candidate_id}: {candidate.get('title', '')}".strip(),
                source_path=self.rel(path),
                blocked_on=blocked_on,
                next_action=action or f"Run the positive-source gate for {candidate_id}.",
                evidence_note="A family proposal admits no package id or directory before the source gate and admission record.",
            )

    def collect_work_items(self) -> None:
        path = self.root / WORK_ITEMS_FILE
        if not path.is_file():
            return
        payload = self.load_json(path)
        if payload is None:
            return
        items = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            self.warn_shape(path, "no items list")
            return
        for item in items:
            if not isinstance(item, dict) or not item.get("id"):
                self.warn_shape(path, "item without an id")
                continue
            status = item.get("status")
            if status not in ("open", "in_progress", "done", "blocked"):
                self.warn_shape(path, f"{item['id']} declares an unknown status {status!r}")
                continue
            if status == "done":
                continue
            needs = str(item.get("needs", "none"))
            blocked_on = NEEDS_TO_BLOCKER.get(needs)
            if blocked_on is None:
                self.warn_shape(path, f"{item['id']} declares an unknown needs value {needs!r}")
                continue
            decision_class = item.get("decision_class")
            if decision_class not in LANES:
                self.warn_shape(path, f"{item['id']} declares an unknown decision_class {decision_class!r}")
                continue
            depends_on = item.get("depends_on")
            if not isinstance(depends_on, list) or not all(
                isinstance(value, str) and value.strip() for value in depends_on
            ):
                self.warn_shape(path, f"{item['id']} depends_on is not a list of non-empty ids")
                continue
            unfinished = []
            for dependency in depends_on:
                matches = [candidate for candidate in items
                           if isinstance(candidate, dict) and candidate.get("id") == dependency]
                if not matches:
                    self.warn_shape(path, f"{item['id']} names unknown dependency {dependency}")
                if len(matches) != 1 or matches[0].get("status") != "done":
                    unfinished.append(dependency)
            steps = [str(step) for step in item.get("steps", []) if isinstance(step, str)]
            next_action = steps[0] if steps else f"Read {self.rel(path)} for {item['id']}."
            if unfinished:
                next_action = f"Waits on {', '.join(unfinished)}. Then: {next_action}"
            self.add(
                id=f"{self.rel(path)}#{item['id']}",
                kind="work_item",
                source_status=status,
                lane=decision_class,
                pending_dependencies=unfinished,
                family=REPOSITORY_FAMILY,
                title=f"{item['id']}: {item.get('title', '')}".strip(),
                source_path=self.rel(path),
                blocked_on=blocked_on,
                next_action=next_action,
                evidence_note=str(item.get("evidence") or "") or None,
            )

    def collect_staging(self) -> None:
        base = self.root / STAGING_DIR
        if not base.is_dir():
            return
        for readme in sorted(base.glob("*/README.md")):
            text = self.read_text(readme)
            heading = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), None)
            family = readme.parent.name
            self.add(
                id=self.rel(readme),
                kind="staging_promotion",
                family=family,
                title=heading or f"{family} staging",
                source_path=self.rel(readme),
                blocked_on=classify_blocked_on(STAGING_SUMMARY),
                next_action=f"Move {family} out of staging: it {STAGING_SUMMARY}.",
                evidence_note="Staged code is authored and unexecuted; it is outside the catalog, every batch, and every profile.",
            )

    def collect_deliberations(self) -> None:
        base = self.root / DELIBERATIONS_DIR
        if not base.is_dir():
            return
        for path in sorted(base.glob("*.json")):
            payload = self.load_json(path)
            if payload is None:
                continue
            if not isinstance(payload, dict) or not payload.get("id"):
                self.warn_shape(path, "no id")
                continue
            if str(payload.get("status", "")) != "open":
                continue
            not_before = payload.get("review_not_before")
            closed: bool | None = None
            moment = parse_timestamp(not_before)
            if not_before is not None and moment is None:
                self.warn_shape(path, "review_not_before is not an RFC 3339 timestamp")
            if moment is not None:
                closed = self.now >= moment
            execution = payload.get("execution") if isinstance(payload.get("execution"), dict) else {}
            action = str(execution.get("exact_next_action", "")).strip()
            if closed:
                blocked_on = "maintainer"
                note = f"The review window closed at {not_before}; a person or the recorded process resolves the record."
            elif closed is False:
                blocked_on = "review_window"
                note = f"The review window stays open until {not_before}; add a delta or wait."
            else:
                blocked_on = "review_window"
                note = "The record names no review_not_before; treat the window as open."
            self.add(
                id=f"{self.rel(path)}#{payload['id']}",
                kind="deliberation_open",
                family=REPOSITORY_FAMILY,
                title=f"{payload['id']}: {payload.get('title', '')}".strip(),
                source_path=self.rel(path),
                blocked_on=blocked_on,
                next_action=action or "Read the record and add a delta or resolve it as its execution section says.",
                evidence_note=note,
                review_not_before=str(not_before) if not_before is not None else None,
                window_closed=closed,
            )

    def collect_roadmap(self) -> None:
        path = self.root / ROADMAP_FILE
        if not path.is_file():
            return
        text = self.read_text(path)
        steps = parse_roadmap_steps(text)
        if not steps:
            self.warnings.append(f"{self.rel(path)}: no numbered items under '{ROADMAP_HEADING}'")
            return
        for number, body in steps:
            title_match = re.match(r"\*\*(.+?)\*\*", body)
            title = title_match.group(1).rstrip(".") if title_match else first_sentence(body)
            rest = first_sentence(body[title_match.end():] if title_match else body)
            if rest and (rest[0].islower() or rest.startswith("(")):
                rest = f"{title} {rest}"  # the bold title is the sentence's subject
            self.add(
                id=f"{self.rel(path)}#execution-order/{number:02d}",
                kind="roadmap_step",
                family=REPOSITORY_FAMILY,
                title=f"Step {number}: {title}",
                source_path=self.rel(path),
                blocked_on=classify_blocked_on(body),
                next_action=rest or body,
                evidence_note=None,
            )


# -- pure helpers ----------------------------------------------------------


def classify_blocked_on(text: str) -> str:
    if HEADSET_PATTERN.search(text):
        return "headset"
    if UNITY_PATTERN.search(text):
        return "unity_editor"
    if RECEIPT_PATTERN.search(text):
        return "headset"
    if MAINTAINER_PATTERN.search(text):
        return "maintainer"
    if WINDOW_PATTERN.search(text):
        return "review_window"
    return "nothing"


def classify_gap_kind(missing_text: str) -> str:
    # Evidence words win: "a green unity-consumer-tests receipt" names a test run
    # but only evidence closes it. A partial clause with no missing text is a
    # test gap, because the map's own tests are what is incomplete.
    if EVIDENCE_PATTERN.search(missing_text):
        return "evidence_gap"
    return "test_gap"


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def first_sentence(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    match = re.match(r"(.+?\.)(?:\s|$)", cleaned)
    return match.group(1).strip() if match else cleaned


def parse_roadmap_steps(text: str) -> list[tuple[int, str]]:
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if re.match(rf"^##\s+{re.escape(ROADMAP_HEADING)}\s*$", line):
            start = index + 1
            break
    if start is None:
        return []
    steps: list[tuple[int, list[str]]] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        item = re.match(r"^(\d+)\.\s+(.*)$", line)
        if item:
            steps.append((int(item.group(1)), [item.group(2)]))
        elif steps and line.startswith(" ") and line.strip():
            steps[-1][1].append(line.strip())
        elif steps and line.strip():
            break  # unindented prose after the list ends the numbered items
    return [(number, " ".join(parts)) for number, parts in steps]


def git_head(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def sort_key(item: WorkItem) -> tuple[int, str, str]:
    return (LANES.index(item.lane), item.family, item.id)


def counts(items: list[WorkItem], field: str, order: tuple[str, ...]) -> dict[str, int]:
    result = {name: 0 for name in order}
    for item in items:
        value = getattr(item, field)
        result[value] = result.get(value, 0) + 1
    return {name: count for name, count in result.items() if count or name in order}


def build_board(root: Path, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    collector = Collector(root, now)
    sources: list[Callable[[], None]] = [
        collector.collect_work_items,
        collector.collect_coverage_maps,
        collector.collect_lessons,
        collector.collect_queue,
        collector.collect_staging,
        collector.collect_deliberations,
        collector.collect_roadmap,
    ]
    for source in sources:
        source()
    items = sorted(collector.items, key=sort_key)
    return {
        "schema": SCHEMA,
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "commit": git_head(root),
        "items": [asdict(item) for item in items],
        "summary": {
            "total": len(items),
            "by_kind": counts(items, "kind", KINDS),
            "by_blocked_on": counts(items, "blocked_on", BLOCKERS),
            "by_lane": counts(items, "lane", LANES),
        },
        "warnings": collector.warnings,
    }


def render_markdown(board: dict[str, Any]) -> str:
    lines = ["# Open work board", ""]
    lines.append(f"Generated {board['generated_at']} at commit `{board['commit'] or 'unknown'}`.")
    lines.append("This board is generated from the source files; it assigns and reserves nothing.")
    capability = board.get("capability")
    if capability:
        lines.append("")
        lines.append(
            "Narrowed to capability `{id}` ({title}), which reaches work blocked on {blockers}. "
            "{hidden} item(s) need a different declaration; "
            "{waiting} item(s) wait on dependencies; "
            "{status_waiting} item(s) are not actionable in their source status.".format(
                id=capability.get("id"),
                title=capability.get("title"),
                blockers=", ".join(capability.get("satisfies_blockers", [])),
                hidden=capability.get("items_needing_capability", capability.get("items_hidden", 0)),
                waiting=capability.get("items_waiting_on_dependencies", 0),
                status_waiting=capability.get("items_not_actionable_by_status", 0),
            )
        )
    lines.append("")
    items = board["items"]
    for lane, heading in (("routine", "Routine lane"), ("non_routine", "Non-routine lane")):
        lane_items = [item for item in items if item["lane"] == lane]
        lines.append(f"## {heading} ({len(lane_items)})")
        lines.append("")
        if not lane_items:
            lines.append("No items.")
            lines.append("")
        for blocker in BLOCKERS:
            group = [item for item in lane_items if item["blocked_on"] == blocker]
            if not group:
                continue
            lines.append(f"### Blocked on: {blocker} ({len(group)})")
            lines.append("")
            lines.append("| Kind | Source status | Family | Title | Next action | Source |")
            lines.append("| --- | --- | --- | --- | --- | --- |")
            for item in group:
                lines.append(
                    "| {kind} | {source_status} | {family} | {title} | {action} | `{source}` |".format(
                        kind=item["kind"],
                        source_status=cell(item.get("source_status") or "not specified"),
                        family=item["family"],
                        title=cell(item["title"]),
                        action=cell(item["next_action"]),
                        source=item["source_path"],
                    )
                )
            lines.append("")
    summary = board["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total: {summary['total']}")
    lines.append("- By kind: " + ", ".join(f"{k} {v}" for k, v in summary["by_kind"].items()))
    lines.append("- By blocked_on: " + ", ".join(f"{k} {v}" for k, v in summary["by_blocked_on"].items()))
    lines.append("- By lane: " + ", ".join(f"{k} {v}" for k, v in summary["by_lane"].items()))
    if board["warnings"]:
        lines.append("")
        lines.append("## Warnings")
        lines.append("")
        lines.extend(f"- {warning}" for warning in board["warnings"])
    lines.append("")
    return "\n".join(lines)


def cell(text: str) -> str:
    return re.sub(r"\s+", " ", text).replace("|", "\\|").strip()


def load_capability_profiles(root: Path) -> dict[str, dict[str, Any]]:
    """Return the declared capability profiles, keyed by id (empty when absent)."""

    path = root / CAPABILITY_PROFILES_FILE
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise UnreadableSource(f"{CAPABILITY_PROFILES_FILE}: {error}") from error
    profiles = payload.get("profiles") if isinstance(payload, dict) else None
    if not isinstance(profiles, list):
        return {}
    return {
        str(profile["id"]): profile
        for profile in profiles
        if isinstance(profile, dict) and isinstance(profile.get("id"), str)
    }


def filter_board_by_capability(board: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Keep only the items a declared capability can actually take.

    The board itself is unchanged on disk; this narrows one printed view. An item
    whose ``blocked_on`` the profile does not satisfy is not hidden work, it is
    work for a different declaration, and the printed header says which.
    """

    reachable = set(profile.get("satisfies_blockers", []))
    eligible = [item for item in board["items"] if item["blocked_on"] in reachable]
    dependency_ready = [item for item in eligible if not item.get("pending_dependencies")]
    items = [item for item in dependency_ready
             if not (item["kind"] == "work_item" and item.get("source_status") != "open")
             and not (item["kind"] == "lesson_gap" and item.get("source_status") == "deferred")]
    narrowed = dict(board)
    narrowed["capability"] = {
        "id": profile.get("id"),
        "title": profile.get("title"),
        "satisfies_blockers": sorted(reachable),
        "items_hidden": len(board["items"]) - len(items),
        "items_needing_capability": len(board["items"]) - len(eligible),
        "items_waiting_on_dependencies": len(eligible) - len(dependency_ready),
        "items_not_actionable_by_status": len(dependency_ready) - len(items),
    }
    narrowed["items"] = items
    narrowed["summary"] = {
        "total": len(items),
        "by_kind": counts([WorkItem(**item) for item in items], "kind", KINDS),
        "by_blocked_on": counts([WorkItem(**item) for item in items], "blocked_on", BLOCKERS),
        "by_lane": counts([WorkItem(**item) for item in items], "lane", LANES),
    }
    return narrowed


PACKET_SCHEMA = "xr-foundry.item_brief.v1"
PACKET_DISCLAIMER = (
    "This generated packet assigns and reserves nothing. Capability and readiness "
    "grant no write, review, merge, release, promotion, governance, or device authority. "
    "Source files remain authoritative. Read the cited files before acting; commands "
    "are data for review, never executed by this exporter."
)


def build_item_brief(root: Path, item_id: str, capability: str | None = None,
                      now: datetime | None = None) -> dict[str, Any]:
    """Export the canonical record, failing closed on invalid source contracts.

    Validation is deliberately stricter than the best-effort board. Validating
    the entire work registry also checks duplicate ids, dependency cycles, and
    done proofs, so malformed prerequisites cannot confer readiness.
    """
    try:
        import validate_repository as validator
    except ModuleNotFoundError as error:
        if error.name != "validate_repository":
            raise
        from scripts import validate_repository as validator

    source = root / WORK_ITEMS_FILE
    raw = source.read_bytes()
    errors = validator.validate_work_items(root)
    if source.read_bytes() != raw:
        raise ValueError("work-item source changed during validation; retry the export")
    if errors:
        raise ValueError("invalid work-item source: " + "; ".join(errors))
    payload = json.loads(raw)
    items = {item["id"]: item for item in payload["items"]}
    if item_id not in items:
        raise ValueError(f"unknown work item {item_id!r}")
    item = items[item_id]
    profile = None
    profile_digest = None
    if capability is not None:
        profile_raw = (root / CAPABILITY_PROFILES_FILE).read_bytes()
        errors = validator.validate_capability_profiles(root)
        if (root / CAPABILITY_PROFILES_FILE).read_bytes() != profile_raw or source.read_bytes() != raw:
            raise ValueError("source changed during capability validation; retry the export")
        if errors:
            raise ValueError("invalid capability source: " + "; ".join(errors))
        profiles = {entry["id"]: entry for entry in json.loads(profile_raw)["profiles"]}
        if capability not in profiles:
            raise ValueError(f"unknown capability profile {capability!r}")
        profile = profiles[capability]
        profile_digest = hashlib.sha256(profile_raw).hexdigest()
    prerequisites = [
        {"id": dep, "title": items[dep]["title"], "status": items[dep]["status"],
         "complete": items[dep]["status"] == "done", "done_proof": items[dep]["done_proof"]}
        for dep in item["depends_on"]
    ]
    reasons = []
    if item["status"] != "open":
        reasons.append(f"Item status is {item['status']}; only open items are available to start.")
    pending = [dep["id"] for dep in prerequisites if not dep["complete"]]
    if pending:
        reasons.append("Unfinished prerequisites: " + ", ".join(pending) + ".")
    matches = None if profile is None else item["needs"] in profile["satisfies_needs"]
    if profile is None:
        reasons.append("No capability declared; capability readiness is unconfirmed.")
    elif not matches:
        reasons.append(f"Capability {capability} does not satisfy needs {item['needs']}.")
    return {
        "schema": PACKET_SCHEMA,
        "generated_at": (now or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z"),
        "commit": git_head(root),
        "source_path": WORK_ITEMS_FILE.as_posix(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "item": item,
        "capability": profile,
        "capability_source_path": CAPABILITY_PROFILES_FILE.as_posix() if profile else None,
        "capability_source_sha256": profile_digest,
        "prerequisites": prerequisites,
        "readiness": {"ready": not reasons, "capability_satisfied": matches,
                      "pending_dependencies": pending, "reasons": reasons},
        "disclaimer": PACKET_DISCLAIMER,
    }


def render_item_brief(packet: dict[str, Any]) -> str:
    item = packet["item"]
    lines = [f"# Item brief: {item['id']} — {item['title']}", "",
             packet["disclaimer"], "",
             f"Generated {packet['generated_at']} at HEAD `{packet['commit'] or 'unknown'}`.",
             f"Source: `{packet['source_path']}` (SHA-256 `{packet['source_sha256']}`).",
             "HEAD identifies the checkout; the digest identifies the actual source snapshot, including local edits.", "",
             f"- Status: {item['status']}", f"- Decision class: {item['decision_class']}",
             f"- Milestone batch: {item['milestone_batch']}", f"- Size: {item['size']}",
             f"- Required capability (needs): {item['needs']}",
             f"- Ready to start: {'yes' if packet['readiness']['ready'] else 'no'}",
             "Readiness checks only open status, prerequisites, and declared capability. "
             "It does not satisfy claims, leases, review, or evidence gates. Follow "
             "docs/contributing/work-items.md and, for non-routine work, docs/contributing/task-hall.md."]
    lines.extend(f"- {reason}" for reason in packet["readiness"]["reasons"])
    profile = packet["capability"]
    if profile:
        lines += ["", f"## Declared capability: {profile['id']}", "", profile["brings"],
                  f"Source: `{packet['capability_source_path']}` (SHA-256 `{packet['capability_source_sha256']}`).",
                  "", "May never claim:"]
        lines.extend(f"- {claim}" for claim in profile["may_never_claim"])
    lines += ["", "## Prerequisites", ""]
    for dep in packet["prerequisites"]:
        lines.append(f"- {dep['id']}: {dep['title']} — {dep['status']}; "
                     f"complete: {str(dep['complete']).lower()}; proof: {dep['done_proof'] or 'none'}")
    if not packet["prerequisites"]:
        lines.append("None.")
    for heading, entries in (("Read first", item["read_first"]),
                             ("Allowed paths", item["allowed_paths"]),
                             ("Steps", item["steps"]),
                             ("Acceptance commands (review before running)", item["acceptance"]["commands"]),
                             ("Acceptance artifacts", item["acceptance"]["artifacts"])):
        lines += ["", f"## {heading}", ""]
        lines.extend(f"{index}. {entry}" for index, entry in enumerate(entries, 1))
        if not entries:
            lines.append("None declared.")
    lines += ["", "## Evidence", "", item["evidence"], "", "## Done proof", "",
              item["done_proof"] or "None recorded. Completion requires an existing proof path in the source item.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    parser.add_argument("--json", action="store_true", help="print the board as JSON")
    parser.add_argument("--markdown", action="store_true", help="print the board as a Markdown table")
    parser.add_argument("--output", help="write the JSON board to this path")
    parser.add_argument(
        "--capability",
        help="keep only the work a declared capability profile can take "
        "(an id from docs/contributing/capability-profiles.json)",
    )
    parser.add_argument(
        "--list-capabilities",
        action="store_true",
        help="print the declared capability profiles and the question each one answers",
    )
    parser.add_argument("--item", help="export a complete curated item brief by WI-nnn id")
    args = parser.parse_args(argv)
    if args.item is not None and (args.list_capabilities or (args.json and args.markdown)):
        parser.error("--item cannot combine with --list-capabilities or both --json and --markdown")

    root = Path(args.root).resolve()
    if args.item is not None:
        try:
            packet = build_item_brief(root, args.item, args.capability)
            payload = json.dumps(packet, indent=2) + "\n"
            if args.output:
                Path(args.output).write_text(payload, encoding="utf-8")
        except (OSError, ValueError, UnicodeError, UnreadableSource) as error:
            print(f"open_work: cannot export item brief: {error}", file=sys.stderr)
            return 1
        if args.markdown:
            print(render_item_brief(packet), end="")
        if args.json or not (args.markdown or args.output):
            print(payload, end="")
        return 0
    try:
        profiles = load_capability_profiles(root)
    except UnreadableSource as error:
        print(f"open_work: unreadable source file: {error}", file=sys.stderr)
        return 1

    if args.list_capabilities:
        if not profiles:
            print("open_work: no capability profiles are declared", file=sys.stderr)
            return 1
        for profile_id, profile in profiles.items():
            print(f"{profile_id}: {profile.get('title', '')}")
            print(f"  {profile.get('question', '')}")
            print(f"  reaches: {', '.join(sorted(profile.get('satisfies_blockers', [])))}")
        return 0

    if args.capability and args.capability not in profiles:
        known = ", ".join(sorted(profiles)) or "none declared"
        print(
            f"open_work: unknown capability profile {args.capability!r}; declared profiles: {known}",
            file=sys.stderr,
        )
        return 1

    try:
        board = build_board(root)
    except UnreadableSource as error:
        print(f"open_work: unreadable source file: {error}", file=sys.stderr)
        return 1

    if args.capability:
        board = filter_board_by_capability(board, profiles[args.capability])

    payload = json.dumps(board, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    if args.markdown:
        print(render_markdown(board), end="")
    if args.json or not (args.markdown or args.output):
        print(payload, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
