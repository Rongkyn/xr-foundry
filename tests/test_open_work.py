from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "open_work.py"
SPEC = importlib.util.spec_from_file_location("open_work", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE  # dataclasses resolve string annotations through sys.modules
SPEC.loader.exec_module(MODULE)

NOW = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)


def write(repo: Path, path: str, content: str) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def write_json(repo: Path, path: str, payload: dict) -> None:
    write(repo, path, json.dumps(payload, indent=2) + "\n")


def make_repo(directory: str) -> Path:
    repo = Path(directory)
    write_json(
        repo,
        "docs/standards/demo/coverage-map.json",
        {
            "schema": "xr-foundry.verification_coverage_map.v1",
            "family": "demo",
            "gates": [
                {
                    "id": "core",
                    "clauses": [
                        {"id": "D-00", "clause": "covered clause", "coverage": "covered", "tests": ["A"], "missing": []},
                        {
                            "id": "D-01",
                            "clause": "a real headset test records comfort",
                            "coverage": "partial",
                            "tests": [],
                            "missing": ["a Device Lab receipt on one named headset"],
                        },
                        {
                            "id": "D-02",
                            "clause": "empty identities are rejected",
                            "coverage": "partial",
                            "tests": ["RejectsDefault"],
                            "missing": ["a test that rejects an empty identity"],
                        },
                    ],
                }
            ],
        },
    )
    write_json(
        repo,
        "docs/standards/lessons/lessons-register.json",
        {
            "lessons": [
                {
                    "id": "LESSON-001",
                    "title": "Keep a closed classification",
                    "dispositions": [
                        {
                            "family": "demo",
                            "status": "gap",
                            "rationale": "The taxonomy question is open.",
                            "follow_up": "Maintainer records the decision in the proposal.",
                        },
                        {"family": "other", "status": "adopted", "rationale": "Done."},
                    ],
                }
            ]
        },
    )
    write_json(
        repo,
        "docs/foundry/queue/next-batch.json",
        {
            "candidates": [
                {
                    "id": "NEXT-DEMO",
                    "title": "Demo family",
                    "state": "proposal",
                    "exact_next_action": "Run the positive-source gate and decide whether to admit a Core blueprint.",
                }
            ]
        },
    )
    write(repo, "staging/demo/README.md", "# Demo staging\n\nStatus: staging material.\n")
    write_json(
        repo,
        "docs/governance/deliberations/DLB-0001-past.json",
        {
            "id": "DLB-0001-PAST",
            "title": "A closed window",
            "status": "open",
            "review_not_before": "2026-01-01T00:00:00Z",
            "execution": {"exact_next_action": "Record the outcome when the window closes."},
        },
    )
    write_json(
        repo,
        "docs/governance/deliberations/DLB-0002-future.json",
        {
            "id": "DLB-0002-FUTURE",
            "title": "An open window",
            "status": "open",
            "review_not_before": "2030-01-01T00:00:00Z",
            "execution": {"exact_next_action": "Add a delta before the window closes."},
        },
    )
    write_json(
        repo,
        "docs/governance/deliberations/DLB-0003-resolved.json",
        {"id": "DLB-0003-RESOLVED", "title": "Done", "status": "resolved", "review_not_before": "2026-01-01T00:00:00Z"},
    )
    write(
        repo,
        "ROADMAP.md",
        "# Roadmap\n\n## Execution order after Inventory\n\nIn this order:\n\n"
        "1. **Editor evidence for the authored tests.** Every test runs through\n"
        "   the gates. Needs a Unity Editor.\n"
        "2. **Documentation sweep.** Tidy the docs index so every page is linked.\n\n"
        "Families beyond these enter only through the queue.\n\n## Composition\n\n3. Not a step.\n",
    )
    return repo


class OpenWorkBoardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = make_repo(self.tmp.name)
        self.board = MODULE.build_board(self.repo, now=NOW)
        self.items = {item["id"]: item for item in self.board["items"]}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_kinds_and_blockers_are_derived_from_each_source(self) -> None:
        self.assertEqual(self.board["schema"], "xr-foundry.open_work.v1")
        self.assertEqual(self.board["warnings"], [])
        expected = {
            "docs/standards/demo/coverage-map.json#D-01": ("evidence_gap", "headset", "non_routine"),
            "docs/standards/demo/coverage-map.json#D-02": ("test_gap", "nothing", "routine"),
            "docs/standards/lessons/lessons-register.json#LESSON-001/demo": ("lesson_gap", "maintainer", "non_routine"),
            "docs/foundry/queue/next-batch.json#NEXT-DEMO": ("family_proposal", "maintainer", "non_routine"),
            "staging/demo/README.md": ("staging_promotion", "unity_editor", "non_routine"),
            "docs/governance/deliberations/DLB-0001-past.json#DLB-0001-PAST": ("deliberation_open", "maintainer", "non_routine"),
            "docs/governance/deliberations/DLB-0002-future.json#DLB-0002-FUTURE": ("deliberation_open", "review_window", "non_routine"),
            "ROADMAP.md#execution-order/01": ("roadmap_step", "unity_editor", "non_routine"),
            "ROADMAP.md#execution-order/02": ("roadmap_step", "nothing", "routine"),
        }
        self.assertEqual(set(self.items), set(expected))
        for item_id, (kind, blocked_on, lane) in expected.items():
            item = self.items[item_id]
            self.assertEqual((item["kind"], item["blocked_on"], item["lane"]), (kind, blocked_on, lane), item_id)
            self.assertTrue(item["next_action"], item_id)
            self.assertEqual(item["source_path"], item_id.split("#")[0])
        self.assertNotIn("docs/standards/demo/coverage-map.json#D-00", self.items)
        self.assertNotIn("DLB-0003", json.dumps(self.board["items"]))

    def test_item_details(self) -> None:
        lesson = self.items["docs/standards/lessons/lessons-register.json#LESSON-001/demo"]
        self.assertEqual(lesson["next_action"], "Maintainer records the decision in the proposal.")
        self.assertEqual(lesson["family"], "demo")
        self.assertIn("(gap)", lesson["title"])
        proposal = self.items["docs/foundry/queue/next-batch.json#NEXT-DEMO"]
        self.assertTrue(proposal["next_action"].startswith("Run the positive-source gate"))
        self.assertEqual(proposal["family"], "demo")
        staging = self.items["staging/demo/README.md"]
        self.assertIn("needs a Unity run and the maintainer's admission signature", staging["next_action"])
        self.assertEqual(staging["title"], "Demo staging")
        past = self.items["docs/governance/deliberations/DLB-0001-past.json#DLB-0001-PAST"]
        self.assertEqual(past["review_not_before"], "2026-01-01T00:00:00Z")
        self.assertIs(past["window_closed"], True)
        future = self.items["docs/governance/deliberations/DLB-0002-future.json#DLB-0002-FUTURE"]
        self.assertIs(future["window_closed"], False)
        self.assertEqual(future["next_action"], "Add a delta before the window closes.")
        step = self.items["ROADMAP.md#execution-order/01"]
        self.assertEqual(step["title"], "Step 1: Editor evidence for the authored tests")
        self.assertEqual(step["next_action"], "Every test runs through the gates.")
        self.assertEqual(step["family"], "repository")
        evidence = self.items["docs/standards/demo/coverage-map.json#D-01"]
        self.assertIsNotNone(evidence["evidence_note"])
        self.assertIn("a Device Lab receipt on one named headset", evidence["next_action"])

    def test_ordering_is_routine_first_then_family_then_id(self) -> None:
        ids = [item["id"] for item in self.board["items"]]
        self.assertEqual(
            ids[:2],
            ["docs/standards/demo/coverage-map.json#D-02", "ROADMAP.md#execution-order/02"],
        )
        rest = self.board["items"][2:]
        self.assertTrue(all(item["lane"] == "non_routine" for item in rest))
        self.assertEqual([(i["family"], i["id"]) for i in rest], sorted((i["family"], i["id"]) for i in rest))

    def test_summary_counts(self) -> None:
        summary = self.board["summary"]
        self.assertEqual(summary["total"], 9)
        self.assertEqual(
            summary["by_kind"],
            {
                "work_item": 0,
                "test_gap": 1,
                "evidence_gap": 1,
                "lesson_gap": 1,
                "family_proposal": 1,
                "staging_promotion": 1,
                "deliberation_open": 2,
                "roadmap_step": 2,
            },
        )
        self.assertEqual(
            summary["by_blocked_on"],
            {
                "nothing": 2,
                "unity_editor": 2,
                "headset": 1,
                "maintainer": 3,
                "review_window": 1,
                "outside_contributor": 0,
            },
        )
        self.assertEqual(summary["by_lane"], {"routine": 2, "non_routine": 7})

    def test_markdown_groups_by_lane_then_blocker(self) -> None:
        text = MODULE.render_markdown(self.board)
        self.assertIn("## Routine lane (2)", text)
        self.assertIn("## Non-routine lane (7)", text)
        self.assertLess(text.index("## Routine lane"), text.index("## Non-routine lane"))
        self.assertIn("### Blocked on: nothing (2)", text)
        self.assertIn("### Blocked on: review_window (1)", text)
        self.assertIn("| test_gap | not specified | demo |", text)
        self.assertIn("## Summary", text)

    def test_malformed_json_lands_in_warnings(self) -> None:
        write(self.repo, "docs/standards/broken/coverage-map.json", "{not json\n")
        write_json(self.repo, "docs/standards/odd/coverage-map.json", {"family": "odd", "gates": "nope"})
        board = MODULE.build_board(self.repo, now=NOW)
        self.assertEqual(len(board["warnings"]), 2)
        self.assertTrue(any(w.startswith("docs/standards/broken/coverage-map.json: invalid JSON") for w in board["warnings"]))
        self.assertTrue(any(w.startswith("docs/standards/odd/coverage-map.json: unexpected shape") for w in board["warnings"]))
        self.assertEqual(board["summary"]["total"], 9)

    def test_empty_root_yields_no_items_and_no_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            board = MODULE.build_board(Path(empty), now=NOW)
        self.assertEqual(board["items"], [])
        self.assertEqual(board["warnings"], [])
        self.assertIsNone(board["commit"])
        self.assertEqual(board["summary"]["by_lane"], {"routine": 0, "non_routine": 0})

    def test_cli_writes_json_and_prints_markdown(self) -> None:
        output = self.repo / "board.json"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = MODULE.main(["--root", str(self.repo), "--markdown", "--output", str(output)])
        self.assertEqual(code, 0)
        self.assertIn("## Routine lane", stdout.getvalue())
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "xr-foundry.open_work.v1")
        self.assertEqual(payload["summary"]["total"], 9)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = MODULE.main(["--root", str(self.repo), "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["summary"]["total"], 9)


class WorkItemRoutingTests(unittest.TestCase):
    def board(self, items):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            write_json(repo, "docs/contributing/work-items.json", {"items": items})
            return MODULE.build_board(repo, now=NOW)

    def item(self, identity="WI-001"):
        return dict(id=identity, title="A bounded task", needs="none",
                    decision_class="routine", status="open", depends_on=[],
                    steps=["Perform the bounded task."])

    def test_explicit_decision_class_is_not_inferred_from_capability(self):
        for needs in MODULE.NEEDS_TO_BLOCKER:
            for decision in MODULE.LANES:
                with self.subTest(needs=needs, decision=decision):
                    item = self.item()
                    item.update(needs=needs, decision_class=decision)
                    board = self.board([item])
                    self.assertEqual(board["items"][0]["lane"], decision)

    def test_pending_dependencies_stay_visible_but_are_not_dispatchable(self):
        prerequisite = self.item()
        dependent = self.item("WI-002")
        dependent["depends_on"] = ["WI-001"]
        for status in ("open", "in_progress", "blocked"):
            with self.subTest(status=status):
                prerequisite["status"] = status
                board = self.board([prerequisite, dependent])
                child = next(i for i in board["items"] if i["id"].endswith("#WI-002"))
                self.assertEqual(child["pending_dependencies"], ["WI-001"])
                self.assertIn("Waits on WI-001", child["next_action"])
                narrowed = MODULE.filter_board_by_capability(board, {
                    "id": "all", "title": "All capabilities",
                    "satisfies_blockers": list(MODULE.BLOCKERS)})
                self.assertNotIn(child, narrowed["items"])
                self.assertEqual(narrowed["capability"]["items_waiting_on_dependencies"], 1)
                self.assertIn("1 item(s) wait on dependencies", MODULE.render_markdown(narrowed))
        prerequisite["status"] = "done"
        board = self.board([prerequisite, dependent])
        narrowed = MODULE.filter_board_by_capability(board, {"satisfies_blockers": ["nothing"]})
        self.assertEqual(len(narrowed["items"]), 1)
        self.assertEqual(narrowed["items"][0]["pending_dependencies"], [])

    def test_mixed_dependencies_and_hidden_counts_do_not_double_count(self):
        done = self.item("WI-001")
        done["status"] = "done"
        pending = self.item("WI-002")
        child = self.item("WI-003")
        child.update(needs="headset", depends_on=["WI-001", "WI-002"])
        board = self.board([done, pending, child])
        original = json.dumps(board, sort_keys=True)
        self.assertEqual(board["items"][1]["pending_dependencies"], ["WI-002"])
        narrowed = MODULE.filter_board_by_capability(board, {"satisfies_blockers": ["nothing"]})
        self.assertEqual(narrowed["capability"]["items_hidden"], 1)
        self.assertEqual(narrowed["capability"]["items_needing_capability"], 1)
        self.assertEqual(narrowed["capability"]["items_waiting_on_dependencies"], 0)
        self.assertEqual(json.dumps(board, sort_keys=True), original)

    def test_in_progress_is_visible_but_not_offered_for_new_work(self):
        item = self.item()
        item["status"] = "in_progress"
        board = self.board([item])
        self.assertEqual(len(board["items"]), 1)
        narrowed = MODULE.filter_board_by_capability(board, {"satisfies_blockers": ["nothing"]})
        self.assertEqual(narrowed["items"], [])
        self.assertEqual(narrowed["capability"]["items_not_actionable_by_status"], 1)

    def test_deferred_lesson_is_visible_without_becoming_a_task(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root, "docs/standards/lessons/lessons-register.json", {"lessons": [{
                "id": "LESSON-001", "title": "Future adapter", "dispositions": [
                    {"family": "example", "status": "deferred", "follow_up": "When an adapter exists, add its seam."},
                    {"family": "current", "status": "gap", "follow_up": "Document the existing seam."}]}]})
            board = MODULE.build_board(root, now=NOW)
            narrowed = MODULE.filter_board_by_capability(board, {"satisfies_blockers": ["nothing"]})
            self.assertEqual(len(board["items"]), 2)
            self.assertEqual([i["family"] for i in narrowed["items"]], ["current"])
            self.assertEqual(narrowed["capability"]["items_not_actionable_by_status"], 1)

    def test_status_and_dependency_waits_are_counted_without_overlap(self):
        active = self.item("WI-001")
        active["status"] = "in_progress"
        waiting = self.item("WI-002")
        waiting.update(status="in_progress", depends_on=["WI-001"])
        unavailable = self.item("WI-003")
        unavailable.update(status="in_progress", needs="headset")
        board = self.board([active, waiting, unavailable, self.item("WI-004")])
        original = json.dumps(board, sort_keys=True)
        narrowed = MODULE.filter_board_by_capability(board, {"satisfies_blockers": ["nothing"]})
        self.assertEqual([i["id"].split("#")[-1] for i in narrowed["items"]], ["WI-004"])
        counters = narrowed["capability"]
        self.assertEqual(counters["items_hidden"], 3)
        self.assertEqual(counters["items_needing_capability"], 1)
        self.assertEqual(counters["items_waiting_on_dependencies"], 1)
        self.assertEqual(counters["items_not_actionable_by_status"], 1)
        self.assertEqual(json.dumps(board, sort_keys=True), original)

    def test_missing_dependency_is_not_treated_as_done(self):
        item = self.item()
        item["depends_on"] = ["WI-999"]
        board = self.board([item])
        self.assertEqual(board["items"][0]["pending_dependencies"], ["WI-999"])
        self.assertTrue(any("unknown dependency WI-999" in w for w in board["warnings"]))

    def test_malformed_dispatch_fields_are_warned_and_skipped(self):
        for field, value in (("status", None), ("status", []), ("status", "unknown"),
                             ("decision_class", "unknown"), ("decision_class", None),
                             ("depends_on", None), ("depends_on", "WI-001"),
                             ("depends_on", [None])):
            with self.subTest(field=field, value=value):
                item = self.item()
                item[field] = value
                board = self.board([item])
                self.assertEqual(board["items"], [])
                self.assertTrue(board["warnings"])


class RealRepositoryTests(unittest.TestCase):
    def test_real_repository_yields_every_present_kind_without_warnings(self) -> None:
        board = MODULE.build_board(ROOT)
        self.assertEqual(board["warnings"], [])
        self.assertGreater(board["summary"]["total"], 0)
        kinds = {item["kind"] for item in board["items"]}
        present = {"roadmap_step": (ROOT / "ROADMAP.md").is_file()}
        open_clauses = False
        for path in (ROOT / "docs" / "standards").glob("*/coverage-map*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            gates = payload.get("gates") or [{"clauses": payload.get("clauses", [])}]
            for gate in gates:
                for clause in gate.get("clauses", []):
                    if clause.get("coverage") == "partial" or clause.get("missing"):
                        open_clauses = True
        if open_clauses:
            self.assertTrue(kinds & {"test_gap", "evidence_gap"}, "coverage gaps")
        present["lesson_gap"] = (ROOT / "docs" / "standards" / "lessons" / "lessons-register.json").is_file()
        present["family_proposal"] = (ROOT / "docs" / "foundry" / "queue" / "next-batch.json").is_file()
        present["staging_promotion"] = bool(list((ROOT / "staging").glob("*/README.md")))
        present["deliberation_open"] = any(
            json.loads(p.read_text(encoding="utf-8")).get("status") == "open"
            for p in (ROOT / "docs" / "governance" / "deliberations").glob("*.json")
        )
        for kind, expected in present.items():
            if expected:
                self.assertIn(kind, kinds, kind)
        for item in board["items"]:
            self.assertIn(item["blocked_on"], MODULE.BLOCKERS)
            self.assertIn(item["lane"], MODULE.LANES)
            self.assertTrue((ROOT / item["source_path"]).is_file(), item["source_path"])


if __name__ == "__main__":
    unittest.main()
