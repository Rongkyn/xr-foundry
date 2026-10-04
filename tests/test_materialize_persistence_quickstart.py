from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("persistence_fixture", ROOT / "scripts/materialize_persistence_quickstart.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PersistenceQuickstartFixtureTests(unittest.TestCase):
    def setUp(self):
        self.guide = MODULE.GUIDE.read_text(encoding="utf-8")

    def test_clean_project_preserves_canonical_inputs_and_reports_no_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "consumer"
            receipt = MODULE.materialize(output)
            self.assertEqual((output / "Assets/PersistenceQuickstart.cs").read_text(), MODULE.block(self.guide, "csharp"))
            self.assertEqual((output / "Packages/manifest.json").read_text(), MODULE.block(self.guide, "json"))
            self.assertFalse((output / "Packages/packages-lock.json").exists())
            self.assertEqual(receipt["status"], "prepared_only")
            for field in ("unity_resolution", "unity_compilation", "runtime_smoke"):
                self.assertEqual(receipt[field], "not_run")
            for name, digest in receipt["files_sha256"].items():
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), digest)
            self.assertEqual(json.loads((output / "fixture-receipt.json").read_text()), receipt)

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            sentinel = output / "keep.txt"
            sentinel.write_text("keep")
            with self.assertRaisesRegex(ValueError, "already exists"):
                MODULE.materialize(output)
            self.assertEqual(list(output.iterdir()), [sentinel])
            self.assertEqual(sentinel.read_text(), "keep")

    def test_repository_and_symlink_into_repository_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            MODULE.materialize(ROOT / "disposable-consumer")
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / "repo"
            link.symlink_to(ROOT, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "outside"):
                MODULE.materialize(link / "disposable-consumer")

    def test_mismatched_revision_and_mutable_ref_are_rejected(self):
        pin = MODULE.prepare(self.guide)[2]
        for replacement, message in (("a" * 40, "differ"), ("main", "immutable")):
            with self.subTest(replacement=replacement):
                with self.assertRaisesRegex(ValueError, message):
                    MODULE.prepare(self.guide.replace(pin, replacement, 1))

    def test_ambiguous_or_missing_snippet_is_rejected(self):
        for guide in (self.guide + '\n```json\n{}\n```\n', self.guide.replace('```csharp', '```text')):
            with self.assertRaisesRegex(ValueError, "exactly one"):
                MODULE.prepare(guide)

    def test_invalid_source_creates_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            guide = Path(directory) / "guide.md"
            guide.write_text(self.guide.replace('"com.unity.modules.jsonserialize": "1.0.0"', '"unreviewed.package": "1.0.0"'))
            output = Path(directory) / "consumer"
            with patch.object(MODULE, "GUIDE", guide):
                with self.assertRaisesRegex(ValueError, "only the two"):
                    MODULE.materialize(output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
