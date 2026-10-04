from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_repository.py"
BOARD = ROOT / "scripts" / "open_work.py"
PROFILES = "docs/contributing/capability-profiles.json"
SCHEMA = "docs/contributing/capability-profiles.schema.json"
ITEMS = "docs/contributing/work-items.json"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses in the target module need this
    spec.loader.exec_module(module)
    return module


MODULE = load(VALIDATOR, "validate_repository_capability_profiles")
BOARD_MODULE = load(BOARD, "open_work_capability_profiles")


def base_profiles() -> dict:
    return {
        "schema": "xr-foundry.capability_profiles.v1",
        "version": "0.1.0",
        "policy": {
            "declaration_precedes_work": True,
            "profile_grants_no_permission": True,
            "undeclared_capability_is_never_assumed": True,
            "a_profile_cannot_produce_evidence_it_lacks": True,
        },
        "profiles": [
            {
                "id": "ai_tokens_only",
                "title": "AI budget and a clone",
                "question": "Do you bring an AI budget and nothing else?",
                "brings": "A clone and an AI budget.",
                "satisfies_needs": ["none", "outside_contributor"],
                "satisfies_blockers": ["nothing", "outside_contributor"],
                "may_never_claim": ["that any C# compiled or any test executed"],
                "start_at": "AGENTS.md",
                "first_command": "python scripts/open_work.py --capability ai_tokens_only --markdown",
            },
            {
                "id": "maintainer",
                "title": "Repository rights",
                "question": "Do you hold rights on this repository?",
                "brings": "Settings, secrets, tags, and signatures.",
                "satisfies_needs": ["none", "unity_editor", "headset", "maintainer"],
                "satisfies_blockers": ["nothing", "unity_editor", "headset", "maintainer", "review_window"],
                "may_never_claim": ["an Editor or device result without its receipt"],
                "start_at": "AGENTS.md",
                "first_command": "python scripts/open_work.py --capability maintainer --markdown",
            },
        ],
    }


def base_items() -> dict:
    return {
        "schema": "xr-foundry.work_items.v1",
        "version": "0.1.0",
        "policy": {
            "item_grants_no_permission": True,
            "acceptance_is_machine_checked_where_possible": True,
            "done_needs_proof_path": True,
            "disjoint_allowed_paths_run_in_parallel": True,
        },
        "items": [
            {
                "id": "WI-001",
                "title": "A routine item",
                "milestone_batch": "1a",
                "needs": "none",
                "decision_class": "routine",
                "size": "small",
                "status": "open",
                "depends_on": [],
                "read_first": ["AGENTS.md"],
                "allowed_paths": ["docs/"],
                "steps": ["Do the first thing."],
                "acceptance": {
                    "commands": ["python scripts/validate_repository.py --json"],
                    "artifacts": ["docs/thing.md"],
                },
                "evidence": "The artifact exists.",
                "done_proof": None,
            },
            {
                "id": "WI-002",
                "title": "A headset item",
                "milestone_batch": "1a",
                "needs": "headset",
                "decision_class": "non_routine",
                "size": "small",
                "status": "open",
                "depends_on": ["WI-001"],
                "read_first": ["AGENTS.md"],
                "allowed_paths": ["docs/"],
                "steps": ["Run the plan on a named device."],
                "acceptance": {
                    "commands": ["python scripts/validate_repository.py --json"],
                    "artifacts": ["docs/receipt.json"],
                },
                "evidence": "A receipt names the device.",
                "done_proof": None,
            },
        ],
    }


class CapabilityProfilesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="capability-profiles-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "docs" / "contributing").mkdir(parents=True)
        (self.tmp / "scripts").mkdir()
        shutil.copy(ROOT / SCHEMA, self.tmp / SCHEMA)
        shutil.copy(BOARD, self.tmp / "scripts" / "open_work.py")
        (self.tmp / "AGENTS.md").write_text("# guide\n", encoding="utf-8")
        (self.tmp / ITEMS).write_text(json.dumps(base_items()), encoding="utf-8")

    def write(self, payload: dict) -> list[str]:
        (self.tmp / PROFILES).write_text(json.dumps(payload), encoding="utf-8")
        return MODULE.validate_capability_profiles(self.tmp)

    def test_valid_profiles_pass(self) -> None:
        self.assertEqual(self.write(base_profiles()), [])

    def test_absent_file_is_not_an_error(self) -> None:
        self.assertEqual(MODULE.validate_capability_profiles(self.tmp), [])

    def test_schema_violation_is_reported(self) -> None:
        payload = base_profiles()
        payload["profiles"][0]["satisfies_blockers"] = ["teleportation"]
        self.assertTrue(any("capability profiles" in error for error in self.write(payload)))

    def test_every_profile_must_reach_the_nothing_blocker(self) -> None:
        payload = base_profiles()
        payload["profiles"][0]["satisfies_blockers"] = ["outside_contributor"]
        errors = self.write(payload)
        self.assertTrue(any("must include 'nothing'" in error for error in errors), errors)

    def test_duplicate_profile_id_is_reported(self) -> None:
        payload = base_profiles()
        payload["profiles"][1]["id"] = "ai_tokens_only"
        errors = self.write(payload)
        self.assertTrue(any("duplicate profile id" in error for error in errors), errors)

    def test_missing_start_at_page_is_reported(self) -> None:
        payload = base_profiles()
        payload["profiles"][0]["start_at"] = "docs/nowhere.md"
        errors = self.write(payload)
        self.assertTrue(any("start_at page does not exist" in error for error in errors), errors)

    def test_first_command_must_name_an_existing_script(self) -> None:
        payload = base_profiles()
        payload["profiles"][0]["first_command"] = "python scripts/not_here.py"
        errors = self.write(payload)
        self.assertTrue(any("first_command must run a script" in error for error in errors), errors)

    def test_unreachable_board_blocker_is_reported(self) -> None:
        payload = base_profiles()
        payload["profiles"][1]["satisfies_blockers"] = ["nothing", "unity_editor", "headset", "maintainer"]
        errors = self.write(payload)
        self.assertTrue(
            any("no profile can reach these open-work blockers" in error for error in errors), errors
        )

    def test_work_item_needing_an_undeclared_capability_is_reported(self) -> None:
        items = base_items()
        items["items"][1]["needs"] = "unity_editor"
        (self.tmp / ITEMS).write_text(json.dumps(items), encoding="utf-8")
        payload = base_profiles()
        payload["profiles"][1]["satisfies_needs"] = ["none", "maintainer"]
        errors = self.write(payload)
        self.assertTrue(
            any("need capabilities no profile declares" in error for error in errors), errors
        )

    def test_hints_exist_for_each_error_shape(self) -> None:
        samples = [
            "capability profiles ai_tokens_only: satisfies_blockers must include 'nothing'; every profile can do work that waits on nothing",
            "capability profiles ai_tokens_only: start_at page does not exist: x",
            "capability profiles ai_tokens_only: first_command must run a script that exists under scripts/: 'x'",
            "capability profiles: satisfies_blockers names blockers the open-work board does not use: ['x']",
            "capability profiles: no profile can reach these open-work blockers: ['review_window']",
            "capability profiles: work items need capabilities no profile declares: ['headset']",
            "capability profiles: duplicate profile id maintainer",
        ]
        for item in MODULE.explain_errors(samples):
            self.assertTrue(item.get("hint"), item)

    def test_real_repository_profiles_pass(self) -> None:
        self.assertEqual(MODULE.validate_capability_profiles(ROOT), [])


class CapabilityBoardTests(unittest.TestCase):
    def test_board_filters_to_the_declared_capability(self) -> None:
        board = {
            "schema": BOARD_MODULE.SCHEMA,
            "generated_at": "2026-01-01T00:00:00Z",
            "commit": None,
            "items": [
                {
                    "id": "a",
                    "kind": "work_item",
                    "source_status": "open",
                    "family": "repository",
                    "title": "A",
                    "source_path": "docs/contributing/work-items.json",
                    "blocked_on": "nothing",
                    "lane": "routine",
                    "next_action": "Do A.",
                },
                {
                    "id": "b",
                    "kind": "evidence_gap",
                    "family": "inventory",
                    "title": "B",
                    "source_path": "docs/standards/inventory/coverage-map.json",
                    "blocked_on": "headset",
                    "lane": "non_routine",
                    "next_action": "Run the device plan.",
                },
            ],
            "summary": {},
            "warnings": [],
        }
        profile = {"id": "ai_tokens_only", "title": "AI budget", "satisfies_blockers": ["nothing"]}
        narrowed = BOARD_MODULE.filter_board_by_capability(board, profile)
        self.assertEqual([item["id"] for item in narrowed["items"]], ["a"])
        self.assertEqual(narrowed["capability"]["items_hidden"], 1)
        self.assertEqual(narrowed["summary"]["total"], 1)
        text = BOARD_MODULE.render_markdown(narrowed)
        self.assertIn("Narrowed to capability `ai_tokens_only`", text)
        self.assertIn("1 item(s) need a different declaration", text)

    def test_every_needs_value_maps_to_a_board_blocker(self) -> None:
        for blocker in BOARD_MODULE.NEEDS_TO_BLOCKER.values():
            self.assertIn(blocker, BOARD_MODULE.BLOCKERS)

    def test_real_repository_board_lists_open_work_items(self) -> None:
        board = BOARD_MODULE.build_board(ROOT)
        work_items = [item for item in board["items"] if item["kind"] == "work_item"]
        self.assertTrue(work_items, "the board must surface the curated work items")
        self.assertEqual(board["warnings"], [])


if __name__ == "__main__":
    unittest.main()
