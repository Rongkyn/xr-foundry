from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_unity_gates.py"
SPEC = importlib.util.spec_from_file_location("run_unity_gates", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _passing_result_xml(mode: str, assembly: str, cases: int) -> str:
    test_cases = "".join(
        f'<test-case id="{index}" name="Case{index}" fullname="{assembly}.Case{index}" result="Passed" />'
        for index in range(cases)
    )
    counts = f'testcasecount="{cases}" total="{cases}" passed="{cases}" failed="0" inconclusive="0" skipped="0" result="Passed"'
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<test-run id="2" {counts}>'
        f'<test-suite type="TestSuite" id="1000" name="host" fullname="host" {counts}>'
        f'<properties><property name="platform" value="{mode}" /></properties>'
        f'<test-suite type="Assembly" id="1001" name="{assembly}.dll" fullname="{assembly}.dll" {counts}>'
        f'<properties><property name="platform" value="{mode}" /></properties>'
        f"{test_cases}</test-suite></test-suite></test-run>"
    )


def _args(**overrides):
    parser = MODULE.build_parser()
    defaults = ["--host", "com.lingkyn.inventory.core"]
    return parser.parse_args(defaults + overrides.pop("argv", []))


class RunUnityGatesTests(unittest.TestCase):
    def test_minimal_host_embeds_transitive_dependencies_and_xr_pins(self) -> None:
        catalog = MODULE.load_catalog_packages()
        profile, packages = MODULE.resolve_host_packages("com.lingkyn.inventory.xr.ugui", catalog)
        self.assertEqual("minimal:com.lingkyn.inventory.xr.ugui", profile)
        self.assertEqual(
            [
                "com.lingkyn.inventory.core",
                "com.lingkyn.inventory.presentation",
                "com.lingkyn.inventory.ugui",
                "com.lingkyn.inventory.xr.ugui",
            ],
            packages,
        )
        with tempfile.TemporaryDirectory() as directory:
            host = Path(directory) / "host"
            MODULE.generate_host(host, packages, catalog)
            manifest = json.loads((host / "Packages" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(packages, manifest["testables"])
        self.assertEqual("1.6.0", manifest["dependencies"]["com.unity.test-framework"])
        for pin, version in MODULE.XR_HOST_PINS.items():
            self.assertEqual(version, manifest["dependencies"][pin])

    def test_all_packages_host_covers_every_live_package(self) -> None:
        catalog = MODULE.load_catalog_packages()
        profile, packages = MODULE.resolve_host_packages("all", catalog)
        self.assertEqual("all-packages", profile)
        self.assertEqual(sorted(catalog), packages)
        self.assertEqual(15, len(packages))

    def test_dry_run_plans_every_assembly_without_unity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = _args(argv=["--dry-run", "--output", directory])
            receipt, exit_code = MODULE.run_gates(args)
            written = json.loads((Path(directory) / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(0, exit_code)
        self.assertEqual("planned", receipt["status"])
        self.assertEqual([], receipt["inventory_errors"])
        self.assertEqual(1, receipt["summary"]["planned"])
        self.assertEqual("Lingkyn.Inventory.Core.Editor.Tests", receipt["runs"][0]["assembly"])
        self.assertEqual(29, receipt["runs"][0]["expected_cases"])
        self.assertIn("-assemblyNames", receipt["runs"][0]["command"])
        self.assertEqual(receipt["schema"], written["schema"])
        self.assertIsNone(receipt["host"]["path"], "temporary host must be removed after the run")

    def test_fake_unity_run_verifies_each_assembly_and_writes_receipt(self) -> None:
        def fake_launch(command: list[str], timeout_seconds: int) -> int:
            mode = command[command.index("-testPlatform") + 1]
            assembly = command[command.index("-assemblyNames") + 1]
            result = Path(command[command.index("-testResults") + 1])
            cases = 29 if assembly == "Lingkyn.Inventory.Core.Editor.Tests" else 1
            result.write_text(_passing_result_xml(mode, assembly, cases), encoding="utf-8")
            Path(command[command.index("-logFile") + 1]).write_text("fake unity log\n", encoding="utf-8")
            return 0

        with tempfile.TemporaryDirectory() as directory, mock.patch.object(MODULE, "launch_unity", side_effect=fake_launch):
            args = _args(argv=["--unity", str(ROOT / "scripts" / "run_unity_gates.py"), "--output", directory])
            receipt, exit_code = MODULE.run_gates(args)

        self.assertEqual(0, exit_code, json.dumps(receipt["runs"], indent=2))
        self.assertEqual("pass", receipt["status"])
        self.assertEqual({"assemblies": 1, "passed": 1, "failed": 0, "planned": 0}, receipt["summary"])
        run = receipt["runs"][0]
        self.assertEqual("pass", run["verification"]["status"])
        self.assertEqual(29, run["verification"]["actual_test_cases"])
        self.assertIsNotNone(run["result_sha256"])

    def test_run_boundary_never_postdates_a_result_written_right_after_it(self) -> None:
        """A fresh result must never look stale to the gate.

        The boundary and the result mtime have to come from one clock: a
        filesystem that truncates timestamps used to place a result written
        microseconds after time.time() *before* the boundary, failing a run that
        was in fact fresh. Repeating the pair many times catches that race.
        """

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for attempt in range(200):
                boundary = MODULE.run_boundary(output)
                result = output / f"result-{attempt}.xml"
                result.write_text("<x/>", encoding="utf-8")
                self.assertGreaterEqual(
                    result.stat().st_mtime,
                    boundary,
                    f"attempt {attempt}: a result written after the boundary must not predate it",
                )
            self.assertEqual([], sorted(p.name for p in output.glob(".run-boundary")))

    def test_wrong_case_count_fails_closed(self) -> None:
        def fake_launch(command: list[str], timeout_seconds: int) -> int:
            mode = command[command.index("-testPlatform") + 1]
            assembly = command[command.index("-assemblyNames") + 1]
            result = Path(command[command.index("-testResults") + 1])
            result.write_text(_passing_result_xml(mode, assembly, 3), encoding="utf-8")
            return 0

        with tempfile.TemporaryDirectory() as directory, mock.patch.object(MODULE, "launch_unity", side_effect=fake_launch):
            args = _args(argv=["--unity", str(SCRIPT), "--output", directory])
            receipt, exit_code = MODULE.run_gates(args)

        self.assertEqual(1, exit_code)
        self.assertEqual("fail", receipt["status"])
        self.assertTrue(any("expected total" in error for error in receipt["runs"][0]["verification"]["errors"]))

    def test_missing_result_is_a_failure_not_a_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(MODULE, "launch_unity", return_value=0):
            args = _args(argv=["--unity", str(SCRIPT), "--output", directory])
            receipt, exit_code = MODULE.run_gates(args)

        self.assertEqual(1, exit_code)
        self.assertEqual("fail", receipt["runs"][0]["status"])
        self.assertTrue(any("missing" in error for error in receipt["runs"][0]["verification"]["errors"]))


class PreparedConsumerTests(unittest.TestCase):
    SHA = "a" * 40

    def fixture(self, root: Path, *, assembly=True, cases=True, lock=True):
        (root / "Packages").mkdir(parents=True)
        (root / "ProjectSettings").mkdir()
        tests = root / "Assets/Tests"
        tests.mkdir(parents=True)
        dependencies = {"com.unity.test-framework": "1.6.0"}
        catalog = MODULE.load_catalog_packages()
        for package in ("com.lingkyn.persistence.core", "com.lingkyn.persistence.unity"):
            dependencies[package] = (
                "https://github.com/Lingkyn/xr-foundry.git?path=/"
                + catalog[package]["path"] + "#" + self.SHA
            )
        (root / "Packages/manifest.json").write_text(json.dumps({"dependencies": dependencies}))
        if lock:
            entries = {key: {"source": "git", "version": value, "hash": self.SHA}
                       for key, value in dependencies.items() if key.startswith("com.lingkyn.")}
            (root / "Packages/packages-lock.json").write_text(json.dumps({"dependencies": entries}))
        (root / "ProjectSettings/ProjectVersion.txt").write_text("m_EditorVersion: 6000.3.19f1\n")
        if assembly:
            (tests / "Consumer.Tests.asmdef").write_text(json.dumps({
                "name": "Consumer.Tests", "optionalUnityReferences": ["TestAssemblies"],
                "includePlatforms": ["Editor"],
            }))
        if cases:
            (tests / "SaveTests.cs").write_text("public class SaveTests {\n[Test] public void Saves() {}\n}")

    def args(self, root, *extra):
        return MODULE.build_parser().parse_args(["--prepared-consumer", str(root), "--dry-run", *extra])

    def snapshot(self, root):
        return {p.relative_to(root).as_posix(): p.read_bytes() if p.is_file() else None
                for p in root.rglob("*")}

    def test_prepared_consumer_is_byte_preserved_and_never_launches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            before = self.snapshot(root)
            with mock.patch.object(MODULE, "launch_unity") as launch, \
                 mock.patch.object(MODULE, "locate_unity") as locate, \
                 mock.patch.object(MODULE, "generate_host") as generate, \
                 mock.patch.object(MODULE, "materialize_reference_system") as materialize, \
                 mock.patch.object(MODULE.subprocess, "run") as process:
                report, code = MODULE.run_gates(self.args(root))
                for operation in (launch, locate, generate, materialize, process):
                    operation.assert_not_called()
            self.assertEqual(before, self.snapshot(root))
            self.assertEqual(0, code, report["errors"])
            self.assertEqual("prepared", report["status"])
            self.assertEqual("6000.3.19f1", report["editor_version"])
            self.assertEqual(1, report["assemblies"][0]["cases"])
            self.assertFalse(report["unity_executed"])
            self.assertNotIn("runs", report)

    def test_conflicting_arguments_fail_before_side_effects(self):
        for option in (["--host", "all"], ["--host", "reference-system"],
                       ["--host-dir", "somewhere"], ["--keep-host"],
                       ["--unity", "Unity"], ["--output", "report"], ["--timeout-minutes", "60"]):
            with self.subTest(option=option), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    self.args("consumer", *option)

    def test_cannot_enable_execution_by_omitting_dry_run_or_mutating_args(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            MODULE.build_parser().parse_args(["--prepared-consumer", "consumer"])
        args = self.args("consumer")
        args.dry_run = False
        with mock.patch.object(MODULE, "launch_unity") as launch:
            with self.assertRaisesRegex(ValueError, "requires --dry-run"):
                MODULE.run_gates(args)
            launch.assert_not_called()

    def test_unpinned_and_mismatched_git_selectors_fail(self):
        for pin in ("main", "v1.0.0", "abc1234", "b" * 40):
            with self.subTest(pin=pin), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root)
                path = root / "Packages/manifest.json"
                payload = json.loads(path.read_text())
                package = "com.lingkyn.persistence.unity"
                payload["dependencies"][package] = payload["dependencies"][package].replace(self.SHA, pin)
                path.write_text(json.dumps(payload))
                report, code = MODULE.run_gates(self.args(root))
                self.assertEqual(1, code)
                self.assertTrue(any("immutable SHA" in error for error in report["errors"]))

    def test_missing_or_wrong_lock_is_reported_without_creating_one(self):
        for value in (None, {}, {"dependencies": {"com.lingkyn.persistence.core": {"hash": None}}}):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root, lock=False)
                lock = root / "Packages/packages-lock.json"
                if value is not None:
                    lock.write_text(json.dumps(value))
                before = self.snapshot(root)
                report, code = MODULE.run_gates(self.args(root))
                self.assertEqual(1, code)
                self.assertTrue(any("lock" in error for error in report["errors"]))
                self.assertEqual(before, self.snapshot(root))

    def test_missing_assembly_and_zero_cases_fail(self):
        for assembly, cases, message in ((False, True, "no consumer-owned"),
                                         (True, False, "no statically countable")):
            with self.subTest(assembly=assembly), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root, assembly=assembly, cases=cases)
                report, code = MODULE.run_gates(self.args(root))
                self.assertEqual(1, code)
                self.assertTrue(any(message in error for error in report["errors"]))

    def test_package_tests_do_not_substitute_for_consumer_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "Assets/Tests").rename(root / "Packages/PackageTests")
            report, code = MODULE.run_gates(self.args(root))
            self.assertEqual(1, code)
            self.assertEqual([], report["assemblies"])

    def test_missing_config_and_requested_assembly_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "ProjectSettings/ProjectVersion.txt").unlink()
            report, code = MODULE.run_gates(self.args(root, "--assembly", "Missing.Tests"))
            self.assertEqual(1, code)
            self.assertIsNone(report["editor_version"])
            self.assertTrue(any("ProjectVersion.txt" in error for error in report["errors"]))
            self.assertTrue(any("Missing.Tests" in error for error in report["errors"]))

    def test_nonexistent_or_invalid_project_reports_blockers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "absent"
            report, code = MODULE.run_gates(self.args(root))
            self.assertEqual(1, code)
            self.assertFalse(root.exists())
            self.assertTrue(report["errors"])

    def test_empty_project_cannot_enter_generated_host_mode(self):
        for extra in ([], ["--dry-run"]):
            with self.subTest(extra=extra), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    MODULE.build_parser().parse_args(["--prepared-consumer", "", *extra])

    def test_symlinked_project_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "consumer"
            self.fixture(root)
            alias = Path(directory) / "alias"
            alias.symlink_to(root, target_is_directory=True)
            report, code = MODULE.run_gates(self.args(alias))
            self.assertEqual(1, code)
            self.assertTrue(any("symlinked" in error for error in report["errors"]))

    def test_runtime_and_qualified_unity_range_are_not_nunit_expansion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "Assets/Volume.cs").write_text(
                "public class Volume { [Range(0f, 1f)] public float value; }"
            )
            (root / "Assets/Tests/Volume.cs").write_text(
                "public class Volume { [UnityEngine.Range(0f, 1f)] public float value; }"
            )
            report, code = MODULE.run_gates(self.args(root))
            self.assertEqual(0, code, report["errors"])

    def test_parameter_expansion_is_rejected(self):
        for attribute in ("Values(1, 2, 3)", "Range(1, 5)", "Random(1, 9, 2)"):
            with self.subTest(attribute=attribute), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root)
                (root / "Assets/Tests/SaveTests.cs").write_text(
                    "public class SaveTests {\n[Test] public void Saves([" + attribute + "] int x) {}\n}"
                )
                report, code = MODULE.run_gates(self.args(root))
                self.assertEqual(1, code)
                self.assertTrue(any("unsupported dynamic" in error for error in report["errors"]))

    def test_qualified_dynamic_test_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "Assets/Tests/SaveTests.cs").write_text(
                'public class SaveTests {\n[Test] public void Saves() {}\n'
                '[NUnit.Framework.TestCaseSource("Cases")] public void Dynamic() {}\n}'
            )
            report, code = MODULE.run_gates(self.args(root))
            self.assertEqual(1, code)
            self.assertTrue(any("unsupported dynamic" in error for error in report["errors"]))

    def test_malformed_selector_credentials_are_not_echoed(self):
        for selector in (
            "https://user:TOP_SECRET@github.com/" + "Lingkyn/xr-foundry.git?path=/packages/unity/systems/persistence/com.lingkyn.persistence.core#main",
            "https://github.com/" + "Lingkyn/xr-foundry.git?path=/packages/unity/systems/persistence/com.lingkyn.persistence.core&token=TOP_SECRET#main",
        ):
            with self.subTest(selector=selector), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root)
                path = root / "Packages/manifest.json"
                value = json.loads(path.read_text())
                value["dependencies"]["com.lingkyn.persistence.core"] = selector
                path.write_text(json.dumps(value))
                report, code = MODULE.run_gates(self.args(root))
                self.assertEqual(1, code)
                self.assertNotIn("TOP_SECRET", json.dumps(report))

    def test_symlinked_manifest_is_not_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "consumer"
            self.fixture(root)
            manifest = root / "Packages/manifest.json"
            target = Path(directory) / "outside.json"
            manifest.rename(target)
            manifest.symlink_to(target)
            report, code = MODULE.run_gates(self.args(root))
            self.assertEqual(1, code)
            self.assertIsNone(report["manifest_sha256"])
            self.assertTrue(any("symlinked" in error for error in report["errors"]))

    def test_symlinked_assets_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "consumer"
            self.fixture(root)
            (root / "Assets/linked").symlink_to(root / "Packages", target_is_directory=True)
            report, code = MODULE.run_gates(self.args(root))
            self.assertEqual(1, code)
            self.assertTrue(any("symlinked" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
