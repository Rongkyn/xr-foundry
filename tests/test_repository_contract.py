from __future__ import annotations

import atexit
import copy
import contextlib
import hashlib
import io
import importlib.util
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_repository.py"
SPEC = importlib.util.spec_from_file_location("validate_repository", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SCAFFOLD_SCRIPT = ROOT / "scripts" / "scaffold_unity_package.py"
SCAFFOLD_SPEC = importlib.util.spec_from_file_location(
    "scaffold_unity_package", SCAFFOLD_SCRIPT
)
assert SCAFFOLD_SPEC and SCAFFOLD_SPEC.loader
SCAFFOLD_MODULE = importlib.util.module_from_spec(SCAFFOLD_SPEC)
SCAFFOLD_SPEC.loader.exec_module(SCAFFOLD_MODULE)
COMPOSE_SCRIPT = ROOT / "scripts" / "compose_system.py"
COMPOSE_SPEC = importlib.util.spec_from_file_location("compose_system", COMPOSE_SCRIPT)
assert COMPOSE_SPEC and COMPOSE_SPEC.loader
COMPOSE_MODULE = importlib.util.module_from_spec(COMPOSE_SPEC)
COMPOSE_SPEC.loader.exec_module(COMPOSE_MODULE)
MATERIALIZER_SCRIPT = ROOT / "scripts" / "materialize_reference_consumer.py"
MATERIALIZER_SPEC = importlib.util.spec_from_file_location(
    "materialize_reference_consumer", MATERIALIZER_SCRIPT
)
assert MATERIALIZER_SPEC and MATERIALIZER_SPEC.loader
MATERIALIZER_MODULE = importlib.util.module_from_spec(MATERIALIZER_SPEC)
MATERIALIZER_SPEC.loader.exec_module(MATERIALIZER_MODULE)


def current_device_profiles() -> dict[str, dict]:
    return {
        payload["profile_id"]: payload
        for path in (ROOT / "docs" / "device-lab" / "profiles").glob("*.json")
        if isinstance(payload := json.loads(path.read_text(encoding="utf-8")), dict)
    }


def current_device_plans() -> dict[str, dict]:
    return {
        payload["test_plan_id"]: payload
        for path in (ROOT / "docs" / "device-lab" / "test-plans").glob("*.json")
        if isinstance(payload := json.loads(path.read_text(encoding="utf-8")), dict)
    }


def current_compatibility_profiles() -> dict:
    return json.loads((ROOT / "compatibility-profiles.json").read_text(encoding="utf-8"))


def compatibility_evidence_test_root() -> Path:
    path = ROOT / "docs" / "validation" / "evidence"
    path.mkdir(parents=True, exist_ok=True)
    return path


def public_fixture_commit() -> str:
    catalog = MODULE.load_json(ROOT / "package-catalog.json")
    refs = subprocess.check_output(
        [
            "git",
            "for-each-ref",
            "--sort=-committerdate",
            "--format=%(refname)",
            "refs/remotes/origin/codex",
            "refs/remotes/origin/main",
        ],
        cwd=ROOT,
        text=True,
    ).splitlines()
    for ref in refs:
        commit_sha = subprocess.check_output(
            ["git", "rev-parse", ref], cwd=ROOT, text=True
        ).strip()
        if not MODULE.commit_is_public_origin_reachable(ROOT, commit_sha):
            continue
        if all(
            subprocess.run(
                ["git", "cat-file", "-e", f"{commit_sha}:{item['path']}/package.json"],
                cwd=ROOT,
                capture_output=True,
                check=False,
            ).returncode
            == 0
            for item in catalog["packages"]
        ):
            return commit_sha
    raise AssertionError("No public origin revision contains the current canonical package tree")


DEVICE_EVIDENCE_TEST_PREFIX = "device-receipt-test-"
STALE_DEVICE_EVIDENCE_AGE_SECONDS = 60 * 60

# Fallback holders for callers that run outside a TestCase. Test methods register
# per-test cleanup through ``self.addCleanup`` instead, so this list is normally empty.
_DEVICE_EVIDENCE_DIRECTORIES: list[tempfile.TemporaryDirectory] = []


def _release_unregistered_device_evidence_directories() -> None:
    while _DEVICE_EVIDENCE_DIRECTORIES:
        holder = _DEVICE_EVIDENCE_DIRECTORIES.pop()
        with contextlib.suppress(Exception):
            holder.cleanup()


atexit.register(_release_unregistered_device_evidence_directories)


def remove_stale_device_evidence_directories(
    max_age_seconds: float = STALE_DEVICE_EVIDENCE_AGE_SECONDS,
) -> list[Path]:
    """Remove ``device-receipt-test-*`` leftovers older than ``max_age_seconds``.

    A crashed or interrupted earlier run can leave fixture directories under the
    repository evidence tree. Younger directories are never touched because a
    concurrent validator run may still be writing into them.
    """
    removed: list[Path] = []
    cutoff = time.time() - max_age_seconds
    for candidate in sorted(
        compatibility_evidence_test_root().glob(f"{DEVICE_EVIDENCE_TEST_PREFIX}*")
    ):
        try:
            if not candidate.is_dir() or candidate.stat().st_mtime > cutoff:
                continue
        except FileNotFoundError:
            continue
        shutil.rmtree(candidate, ignore_errors=True)
        removed.append(candidate)
    return removed


def setUpModule() -> None:
    remove_stale_device_evidence_directories()


def device_evidence_test_root(test_case: unittest.TestCase | None = None) -> Path:
    """Create a repository-relative device-evidence fixture directory.

    The directory must live under ``docs/validation/evidence`` because the
    validator resolves receipt evidence, manifest, lock, and artifact refs as
    repository-relative paths. When ``test_case`` is given the directory is
    removed as soon as that test finishes, whether it passes or fails; otherwise
    it is held until interpreter exit.
    """
    holder = tempfile.TemporaryDirectory(
        prefix=DEVICE_EVIDENCE_TEST_PREFIX,
        dir=compatibility_evidence_test_root(),
    )
    if test_case is not None:
        test_case.addCleanup(holder.cleanup)
    else:
        _DEVICE_EVIDENCE_DIRECTORIES.append(holder)
    return Path(holder.name)


def binary_android_manifest(application_id: str) -> bytes:
    strings = [
        "manifest",
        "package",
        application_id,
        "http://schemas.android.com/apk/res/android",
        "versionCode",
    ]
    string_offsets: list[int] = []
    string_data = bytearray()
    for value in strings:
        encoded = value.encode("utf-8")
        if len(value) >= 128 or len(encoded) >= 128:
            raise ValueError("test fixture strings must use one-byte AXML lengths")
        string_offsets.append(len(string_data))
        string_data.extend((len(value), len(encoded)))
        string_data.extend(encoded)
        string_data.append(0)
    while len(string_data) % 4:
        string_data.append(0)
    strings_start = 28 + len(strings) * 4
    string_pool_size = strings_start + len(string_data)
    string_pool = (
        struct.pack("<HHI", 0x0001, 28, string_pool_size)
        + struct.pack("<IIIII", len(strings), 0, 0x00000100, strings_start, 0)
        + b"".join(struct.pack("<I", offset) for offset in string_offsets)
        + bytes(string_data)
    )
    start_element = (
        struct.pack("<HHI", 0x0102, 16, 76)
        + struct.pack("<II", 1, 0xFFFFFFFF)
        + struct.pack("<IIHHHHHH", 0xFFFFFFFF, 0, 20, 20, 2, 0, 0, 0)
        + struct.pack("<IIIHBBI", 0xFFFFFFFF, 1, 2, 8, 0, 0x03, 2)
        + struct.pack("<IIIHBBI", 3, 4, 0xFFFFFFFF, 8, 0, 0x10, 1)
    )
    end_element = (
        struct.pack("<HHI", 0x0103, 16, 24)
        + struct.pack("<II", 1, 0xFFFFFFFF)
        + struct.pack("<II", 0xFFFFFFFF, 0)
    )
    body = string_pool + start_element + end_element
    return struct.pack("<HHI", 0x0003, 8, 8 + len(body)) + body


def write_minimal_unity_apk(path: Path, application_id: str) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("AndroidManifest.xml", binary_android_manifest(application_id))
        archive.writestr("classes.dex", b"dex\n035\x00" + b"\x00" * 112)
        archive.writestr("lib/arm64-v8a/libunity.so", b"\x7fELF" + b"unity")
        archive.writestr("lib/arm64-v8a/libil2cpp.so", b"\x7fELF" + b"il2cpp")
        archive.writestr("assets/bin/Data/globalgamemanagers", b"unity-player-data")


def attach_compatibility_receipt(
    payload: dict,
    directory: str | Path,
    *,
    profile_id: str = "unity-6000.3-inventory-ugui-non-xr-windows-editor",
) -> tuple[dict, dict, Path]:
    profile = next(item for item in payload["profiles"] if item["id"] == profile_id)
    commit_sha = public_fixture_commit()
    catalog = MODULE.load_json(ROOT / "package-catalog.json")
    catalog_paths = {
        item["id"]: item["path"] for item in catalog["packages"]
    }
    if profile_id in payload["current_profile_ids"]:
        profile = json.loads(json.dumps(profile))
        profile["id"] = f"{profile_id}-verified-fixture"
        for package_id in profile["package_versions"]:
            manifest_at_commit = json.loads(
                subprocess.check_output(
                    [
                        "git",
                        "show",
                        f"{commit_sha}:{catalog_paths[package_id]}/package.json",
                    ],
                    cwd=ROOT,
                    text=True,
                )
            )
            profile["package_versions"][package_id] = manifest_at_commit["version"]
        payload["profiles"].append(profile)
    profile["state"] = "verified"
    profile["verified_claims"] = ["editor_compile", "editmode_tests", "playmode_tests"]
    evidence_directory = Path(directory)
    receipt_path = evidence_directory / "compatibility-receipt.json"
    manifest_path = evidence_directory / "consumer-manifest.json"
    lock_path = evidence_directory / "consumer-packages-lock.json"
    selector = lambda package_id: (
        "https://github.com/Lingkyn/xr-foundry.git?path=/"
        f"{catalog_paths[package_id]}#{commit_sha}"
    )
    manifest_dependencies = dict(profile["target"]["requested_dependencies"])
    manifest_dependencies.update(
        {package_id: selector(package_id) for package_id in profile["package_versions"]}
    )
    lock_dependencies: dict[str, dict] = {}
    for package_id in profile["package_versions"]:
        package_manifest = json.loads(
            subprocess.check_output(
                ["git", "show", f"{commit_sha}:{catalog_paths[package_id]}/package.json"],
                cwd=ROOT,
                text=True,
            )
        )
        lock_dependencies[package_id] = {
            "version": selector(package_id),
            "depth": 0,
            "source": "git",
            "dependencies": package_manifest.get("dependencies", {}),
            "hash": commit_sha,
        }
    for dependency_id, version in profile["target"]["resolved_dependencies"].items():
        lock_dependencies[dependency_id] = {
            "version": version,
            "depth": 0 if dependency_id in manifest_dependencies else 1,
            "source": (
                "builtin"
                if dependency_id.startswith("com.unity.modules.")
                or dependency_id == "com.unity.ugui"
                else "registry"
            ),
            "dependencies": {},
        }
    known_unity_edges = {
        "com.unity.test-framework": {
            "com.unity.ext.nunit": "2.0.3",
            "com.unity.modules.imgui": "1.0.0",
            "com.unity.modules.jsonserialize": "1.0.0",
        },
        "com.unity.ugui": {
            "com.unity.modules.ui": "1.0.0",
            "com.unity.modules.imgui": "1.0.0",
        },
    }
    for dependency_id, edges in known_unity_edges.items():
        if dependency_id in lock_dependencies:
            lock_dependencies[dependency_id]["dependencies"] = {
                child_id: requested_version
                for child_id, requested_version in edges.items()
                if child_id in lock_dependencies
            }
    shortest_depths: dict[str, int] = {}
    pending_depths = [(dependency_id, 0) for dependency_id in manifest_dependencies]
    while pending_depths:
        dependency_id, depth = pending_depths.pop(0)
        if dependency_id in shortest_depths and shortest_depths[dependency_id] <= depth:
            continue
        shortest_depths[dependency_id] = depth
        entry = lock_dependencies.get(dependency_id, {})
        pending_depths.extend(
            (child_id, depth + 1)
            for child_id in entry.get("dependencies", {})
        )
    for dependency_id, depth in shortest_depths.items():
        if dependency_id in lock_dependencies:
            lock_dependencies[dependency_id]["depth"] = depth
    manifest_path.write_text(
        json.dumps(
            {
                "dependencies": manifest_dependencies,
                "testables": sorted(profile["package_versions"]),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    lock_path.write_text(
        json.dumps({"dependencies": lock_dependencies}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    lock_digest = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    check_payloads = []
    for check_id in ("editor_compile", "editmode_tests", "playmode_tests"):
        if check_id == "editor_compile":
            result_path = evidence_directory / "unity-compile-result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "$schema": "docs/validation/unity-compile-result.schema.json",
                        "schema": "xr-foundry.unity_compile_result.v1",
                        "profile_id": profile["id"],
                        "commit_sha": commit_sha,
                        "unity_version": profile["target"]["editor"]["version"],
                        "build_target": profile["target"]["build_target"],
                        "graphics_api": profile["target"]["graphics_api"],
                        "scripting_backend": profile["target"]["scripting_backend"],
                        "architecture": profile["target"]["architecture"],
                        "manifest_sha256": manifest_digest,
                        "lock_sha256": lock_digest,
                        "batchmode": True,
                        "result": "pass",
                        "error_count": 0,
                        "warning_count": 0,
                        "started_at": "2026-07-15T10:00:00Z",
                        "completed_at": "2026-07-15T10:00:05Z",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            kind = "compile_result"
        else:
            result_path = evidence_directory / f"{check_id}-results.xml"
            mode = "EditMode" if check_id == "editmode_tests" else "PlayMode"
            expected_assemblies, derivation_errors = MODULE.derive_expected_test_assemblies(
                ROOT,
                commit_sha,
                catalog_paths,
                set(profile["package_versions"]),
                mode,
            )
            if derivation_errors or not expected_assemblies:
                raise AssertionError((derivation_errors, expected_assemblies))
            assembly_xml = "".join(
                (
                    f'<test-suite type="Assembly" name="{assembly}" result="Passed" '
                    'total="1" passed="1" failed="0" inconclusive="0" skipped="0">'
                    '<properties>'
                    f'<property name="platform" value="{mode}" />'
                    f'<property name="EditorOnly" value="'
                    f'{"True" if mode == "EditMode" else "False"}" />'
                    '</properties>'
                    f'<test-suite type="TestSuite" name="{assembly}.Tests" result="Passed" '
                    'total="1" passed="1" failed="0" inconclusive="0" skipped="0">'
                    f'<test-suite type="TestFixture" name="{assembly}.RequiredFixture" '
                    'result="Passed" total="1" passed="1" failed="0" '
                    'inconclusive="0" skipped="0">'
                    f'<test-case name="{assembly}.RequiredFixture.Passes" result="Passed" />'
                    '</test-suite></test-suite>'
                    '</test-suite>'
                )
                for assembly in sorted(expected_assemblies)
            )
            total = len(expected_assemblies)
            result_path.write_text(
                '<?xml version="1.0" encoding="utf-8"?>\n'
                f'<test-run testcasecount="{total}" result="Passed" total="{total}" '
                f'passed="{total}" failed="0" inconclusive="0" skipped="0" asserts="{total}">'
                f'<test-suite type="TestSuite" name="xr-foundry-consumer" result="Passed" '
                f'total="{total}" passed="{total}" failed="0" inconclusive="0" '
                f'skipped="0"><properties><property name="platform" value="{mode}" />'
                f'</properties>{assembly_xml}</test-suite></test-run>\n',
                encoding="utf-8",
            )
            kind = "nunit_result"
        result_digest = hashlib.sha256(result_path.read_bytes()).hexdigest()
        check_payloads.append(
            {
                "id": check_id,
                "status": "pass",
                "evidence_refs": [
                    {
                        "kind": kind,
                        "ref": result_path.relative_to(ROOT).as_posix(),
                        "sha256": result_digest,
                    }
                ],
            }
        )
    receipt = {
        "$schema": "docs/validation/compatibility-evidence.schema.json",
        "schema": "xr-foundry.compatibility_evidence.v1",
        "kind": "editor_automated",
        "profile_id": profile["id"],
        "commit_sha": commit_sha,
        "target": json.loads(json.dumps(profile["target"])),
        "package_versions": json.loads(json.dumps(profile["package_versions"])),
        "resolved_dependencies": json.loads(
            json.dumps(profile["target"]["resolved_dependencies"])
        ),
        "manifest": {
            "path": manifest_path.relative_to(ROOT).as_posix(),
            "sha256": manifest_digest,
        },
        "lock": {
            "path": lock_path.relative_to(ROOT).as_posix(),
            "sha256": lock_digest,
        },
        "checks": check_payloads,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    profile["evidence"] = [
        {
            "kind": "editor_automated",
            "profile_id": profile["id"],
            "commit_sha": commit_sha,
            "receipt_path": receipt_path.relative_to(ROOT).as_posix(),
            "manifest_sha256": manifest_digest,
            "lock_sha256": lock_digest,
            "checks": ["editor_compile", "editmode_tests", "playmode_tests"],
        }
    ]
    return profile, receipt, receipt_path


def completed_device_lab_receipt(test_case: unittest.TestCase | None = None) -> dict:
    payload = json.loads(
        (ROOT / "docs" / "device-lab" / "device-receipt.template.json").read_text(
            encoding="utf-8"
        )
    )
    payload["receipt_id"] = "inventory-world-ui-pico-pass"
    payload["compatibility_profile_id"] = (
        "unity-6000.3-inventory-xr-ugui-openxr-pico-4"
    )
    payload["task_url"] = "https://github.com/Lingkyn/xr-foundry/issues/1"
    commit_sha = public_fixture_commit()
    payload["revision"]["commit_sha"] = commit_sha
    catalog_at_commit = json.loads(
        subprocess.check_output(
            ["git", "show", f"{commit_sha}:package-catalog.json"],
            cwd=ROOT,
            text=True,
        )
    )
    catalog_paths = {
        item["id"]: item["path"] for item in catalog_at_commit["packages"]
    }
    custom_manifests: dict[str, dict] = {}
    for role in ("domain", "presentation", "renderer_adapter", "xr_adapter"):
        package_id = payload["package_tuple"][role]["id"]
        package_path = catalog_paths[package_id]
        manifest = json.loads(
            subprocess.check_output(
                ["git", "show", f"{commit_sha}:{package_path}/package.json"],
                cwd=ROOT,
                text=True,
            )
        )
        custom_manifests[package_id] = manifest
        payload["package_tuple"][role]["version"] = manifest["version"]

    selector = lambda package_id: (
        "https://github.com/Lingkyn/xr-foundry.git?path=/"
        f"{catalog_paths[package_id]}#{commit_sha}"
    )
    lock_dependencies: dict[str, dict] = {
        package_id: {
            "version": selector(package_id),
            "depth": 0,
            "source": "git",
            "dependencies": manifest.get("dependencies", {}),
            "hash": commit_sha,
        }
        for package_id, manifest in custom_manifests.items()
    }
    external_versions = {
        "com.unity.xr.interaction.toolkit": "3.5.1",
        "com.unity.xr.openxr": "1.16.0",
        "com.unity.xr.management": "4.5.3",
        "com.unity.inputsystem": "1.19.0",
    }
    for manifest in custom_manifests.values():
        for dependency_id, version in manifest.get("dependencies", {}).items():
            if dependency_id not in catalog_paths:
                external_versions[dependency_id] = version
    manifest_dependencies = {
        package_id: selector(package_id) for package_id in custom_manifests
    }
    for package_id in (
        "com.unity.inputsystem",
        "com.unity.xr.management",
        "com.unity.xr.openxr",
    ):
        manifest_dependencies[package_id] = external_versions[package_id]
    for package_id, version in external_versions.items():
        lock_dependencies[package_id] = {
            "version": version,
            "depth": 0 if package_id in manifest_dependencies else 1,
            "source": "builtin" if package_id == "com.unity.ugui" else "registry",
            "dependencies": {},
        }

    evidence_directory = device_evidence_test_root(test_case)
    artifact_path = evidence_directory / "inventory-world-ui.apk"
    write_minimal_unity_apk(artifact_path, "com.example.inventoryworldui")
    payload["artifact"] = {
        "kind": "android-apk",
        "file_name": artifact_path.name,
        "sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        "repository_path": artifact_path.relative_to(ROOT).as_posix(),
        "application_id": "com.example.inventoryworldui",
    }
    manifest_path = evidence_directory / "manifest.json"
    manifest_path.write_text(
        json.dumps({"dependencies": manifest_dependencies}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lock_path = evidence_directory / "packages-lock.json"
    lock_path.write_text(
        json.dumps({"dependencies": lock_dependencies}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lock_digest = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    payload["dependency_resolution"] = {
        "manifest": {
            "format": "unity-manifest-v1",
            "kind": "repository_file",
            "ref": manifest_path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        },
        "lock": {
            "format": "unity-packages-lock-v1",
            "kind": "repository_file",
            "ref": lock_path.relative_to(ROOT).as_posix(),
            "sha256": lock_digest,
        },
        "resolved_packages": [
            {"id": package_id, "version": version}
            for package_id, version in sorted(external_versions.items())
        ],
    }
    payload["software"].update(
        {
            "engine_version": "6000.3.19f1",
            "editor_version": "6000.3.19f1",
            "runtime_version": "1.0.31",
        }
    )
    payload["device"].update(
        {
            "model": "PICO 4",
            "os_version": "5.11.2",
        }
    )
    payload["build"] = {
        "target": "Android",
        "graphics_api": "OpenGLES3",
        "scripting_backend": "IL2CPP",
        "architecture": "ARM64",
    }
    for source in payload["input"]["sources"]:
        source["description"] = f"Recorded {source['id']} tracked controller"
    payload["input"]["device_description"] = "Recorded left and right tracked controllers"
    payload["execution_context"] = {"posture": "seated", "duration_seconds": 120}
    observation_path = evidence_directory / "headset-observation.json"
    observation_path.write_text(
        json.dumps(
            {
                "receipt_id": payload["receipt_id"],
                "commit_sha": commit_sha,
                "device": "PICO 4",
                "result": "recorded test fixture",
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    observation_digest = hashlib.sha256(observation_path.read_bytes()).hexdigest()
    evidence_ref = observation_path.relative_to(ROOT).as_posix()
    required_ids = {
        item["id"]
        for item in current_device_plans()["inventory-world-space-ui-v1"]["required_checks"]
    }
    for check in payload["checks"]:
        if check["id"] in required_ids:
            check.update(
                {
                    "status": "pass",
                    "observation": f"Observed {check['id']} on the recorded composition",
                    "evidence_refs": [
                        {
                            "kind": "repository_file",
                            "ref": evidence_ref,
                            "sha256": observation_digest,
                        }
                    ],
                }
            )
    payload["overall_result"] = "pass"
    payload["claims_supported"] = ["inventory-ugui-xr-required-suite"]
    payload["claims_not_supported"] = [
        "inventory-ui-toolkit-xr-required-suite",
        "direct-poke",
        "hand-ray",
        "gaze-and-pinch",
    ]
    payload["tester"]["github_identity"] = "example-tester"
    payload["timestamps"] = {
        "started_at": "2026-07-15T12:00:00Z",
        "completed_at": "2026-07-15T12:05:00Z",
    }
    return payload


def activate_checkpoint_fixture(checkpoint: dict) -> None:
    """Make lifecycle-sensitive negative fixtures independent of live task state."""
    checkpoint["status"] = "in_progress"
    checkpoint["waiting"] = None
    checkpoint["claim"].update(
        {
            "status": "active",
            "adoptable": False,
            "ended_at": None,
            "transition_reason": None,
        }
    )
    checkpoint["exact_next_action"] = "Continue the bounded test fixture."
    checkpoint["completed_at"] = None


def attach_device_runtime_receipt(
    payload: dict,
    directory: str | Path,
    test_case: unittest.TestCase | None = None,
) -> tuple[dict, dict, Path, Path]:
    device_receipt = completed_device_lab_receipt(test_case)
    profile_id = device_receipt["compatibility_profile_id"]
    base = next(
        item
        for item in payload["profiles"]
        if item["install_artifact"] == "com.lingkyn.inventory.xr.ugui"
    )
    profile = json.loads(json.dumps(base))
    profile["id"] = profile_id
    package_versions = {
        package["id"]: package["version"]
        for role in ("domain", "presentation", "renderer_adapter", "xr_adapter")
        if isinstance(package := device_receipt["package_tuple"].get(role), dict)
    }
    resolved_dependencies = {
        package["id"]: package["version"]
        for package in device_receipt["dependency_resolution"]["resolved_packages"]
    }
    manifest_path = ROOT / device_receipt["dependency_resolution"]["manifest"]["ref"]
    manifest_dependencies = json.loads(manifest_path.read_text(encoding="utf-8"))[
        "dependencies"
    ]
    profile["target"] = {
        "engine": {"id": "unity", "version": device_receipt["software"]["engine_version"]},
        "editor": {
            "id": "unity-editor",
            "version": device_receipt["software"]["editor_version"],
        },
        "renderer": {"id": "com.unity.ugui", "version": resolved_dependencies["com.unity.ugui"]},
        "requested_dependencies": {
            package_id: version
            for package_id, version in manifest_dependencies.items()
            if package_id not in package_versions
        },
        "resolved_dependencies": resolved_dependencies,
        "build_target": device_receipt["build"]["target"],
        "graphics_api": device_receipt["build"]["graphics_api"],
        "scripting_backend": device_receipt["build"]["scripting_backend"],
        "architecture": device_receipt["build"]["architecture"],
        "xr_provider": {
            "id": "com.unity.xr.openxr",
            "version": resolved_dependencies["com.unity.xr.openxr"],
        },
        "runtime": {
            "id": device_receipt["software"]["runtime_id"],
            "version": device_receipt["software"]["runtime_version"],
        },
        "input_routes": sorted(device_receipt["input"]["routes"]),
        "device": {
            "id": device_receipt["device"]["family_id"],
            "version": device_receipt["device"]["os_version"],
        },
    }
    profile["package_versions"] = package_versions
    profile["state"] = "verified"
    profile["verified_claims"] = ["device_runtime"]
    payload["profiles"].append(profile)

    receipts_root = ROOT / "docs" / "device-lab" / "receipts"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        prefix="device-runtime-fixture-",
        dir=receipts_root,
        delete=False,
    ) as handle:
        json.dump(device_receipt, handle, indent=2)
        device_path = Path(handle.name)
    device_digest = hashlib.sha256(device_path.read_bytes()).hexdigest()
    evidence_directory = Path(directory)
    receipt_path = evidence_directory / "device-compatibility-receipt.json"
    manifest = device_receipt["dependency_resolution"]["manifest"]
    lock = device_receipt["dependency_resolution"]["lock"]
    compatibility_receipt = {
        "$schema": "docs/validation/compatibility-evidence.schema.json",
        "schema": "xr-foundry.compatibility_evidence.v1",
        "kind": "device_runtime",
        "profile_id": profile_id,
        "commit_sha": device_receipt["revision"]["commit_sha"],
        "target": json.loads(json.dumps(profile["target"])),
        "package_versions": json.loads(json.dumps(package_versions)),
        "resolved_dependencies": json.loads(json.dumps(resolved_dependencies)),
        "manifest": {"path": manifest["ref"], "sha256": manifest["sha256"]},
        "lock": {"path": lock["ref"], "sha256": lock["sha256"]},
        "device_lab_receipt": {
            "path": device_path.relative_to(ROOT).as_posix(),
            "sha256": device_digest,
        },
        "checks": [
            {
                "id": "device_runtime",
                "status": "pass",
                "evidence_refs": [
                    {
                        "kind": "device_lab_receipt",
                        "ref": device_path.relative_to(ROOT).as_posix(),
                        "sha256": device_digest,
                    }
                ],
            }
        ],
    }
    receipt_path.write_text(json.dumps(compatibility_receipt, indent=2), encoding="utf-8")
    profile["evidence"] = [
        {
            "kind": "device_runtime",
            "profile_id": profile_id,
            "commit_sha": device_receipt["revision"]["commit_sha"],
            "receipt_path": receipt_path.relative_to(ROOT).as_posix(),
            "manifest_sha256": manifest["sha256"],
            "lock_sha256": lock["sha256"],
            "checks": ["device_runtime"],
        }
    ]
    return profile, compatibility_receipt, receipt_path, device_path


class RepositoryContractTests(unittest.TestCase):
    def test_authoritative_json_loader_rejects_nested_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document_path = Path(directory) / "nested-duplicate.json"
            document_path.write_text(
                '{"outer":{"safe":1,"deeper":{"duplicate":2,"duplicate":3}}}',
                encoding="utf-8",
            )

            with self.assertRaises(json.JSONDecodeError) as raised:
                MODULE.load_json(document_path)

            message = str(raised.exception)
            self.assertIn(str(document_path), message)
            self.assertIn("duplicate key 'duplicate'", message)

    def test_compose_cli_reports_duplicate_json_key_without_last_wins(self) -> None:
        composition_path = ROOT / MODULE.REFERENCE_COMPOSITION_PATH
        failure = json.JSONDecodeError(
            f"{composition_path}: duplicate key 'key'", "{}", 0
        )
        output = io.StringIO()
        with (
            mock.patch.object(COMPOSE_MODULE.VALIDATOR, "load_json", side_effect=failure),
            mock.patch.object(
                sys,
                "argv",
                [str(COMPOSE_SCRIPT), str(composition_path), "--json"],
            ),
            contextlib.redirect_stdout(output),
        ):
            status = COMPOSE_MODULE.main()

        self.assertEqual(1, status)
        report = json.loads(output.getvalue())
        self.assertEqual("fail", report["status"])
        self.assertTrue(
            any(
                str(composition_path) in error and "duplicate key 'key'" in error
                for error in report["errors"]
            )
        )

    def test_compose_check_reports_invalid_existing_lock_without_traceback(self) -> None:
        lock_path = ROOT / "compositions/unity/reference-system/foundry.lock.json"
        failure = json.JSONDecodeError(
            f"{lock_path}: duplicate key 'claims'", "{}", 0
        )
        original_load_json = COMPOSE_MODULE.VALIDATOR.load_json

        def fail_only_existing_lock(path: Path) -> object:
            if Path(path) == lock_path:
                raise failure
            return original_load_json(Path(path))

        output = io.StringIO()
        with (
            mock.patch.object(
                COMPOSE_MODULE.VALIDATOR,
                "load_json",
                side_effect=fail_only_existing_lock,
            ),
            mock.patch.object(
                sys,
                "argv",
                [str(COMPOSE_SCRIPT), "--check", "--json"],
            ),
            contextlib.redirect_stdout(output),
        ):
            status = COMPOSE_MODULE.main()

        self.assertEqual(1, status)
        report = json.loads(output.getvalue())
        self.assertEqual("fail", report["status"])
        self.assertEqual(
            "compositions/unity/reference-system/foundry.lock.json",
            report["lock_path"],
        )
        self.assertTrue(
            any(
                str(lock_path) in error and "duplicate key 'claims'" in error
                for error in report["errors"]
            )
        )

    def test_repository_cli_reports_json_decode_failure_without_traceback(self) -> None:
        failure = json.JSONDecodeError(
            "/tmp/authority.json: duplicate key 'authority'", "{}", 0
        )
        output = io.StringIO()
        with (
            mock.patch.object(MODULE, "validate_repository", side_effect=failure),
            mock.patch.object(sys, "argv", [str(SCRIPT)]),
            contextlib.redirect_stdout(output),
        ):
            status = MODULE.main()

        self.assertEqual(1, status)
        report = json.loads(output.getvalue())
        self.assertEqual("fail", report["status"])
        self.assertEqual(
            ["repository JSON is invalid: " + str(failure)], report["errors"]
        )

    def test_device_lab_cli_reports_invalid_profile_or_plan_without_traceback(
        self,
    ) -> None:
        receipt_path = ROOT / "docs/device-lab/device-receipt.template.json"
        original_load_json = MODULE.load_json
        cases = (
            (
                "profiles",
                "profile_id",
                "Device Lab profile is invalid JSON",
            ),
            (
                "test-plans",
                "test_plan_id",
                "Device Lab test plan is invalid JSON",
            ),
        )
        for directory_name, duplicate_key, expected_prefix in cases:
            with self.subTest(directory=directory_name):
                failed_path: Path | None = None

                def fail_selected_authority(path: Path) -> object:
                    nonlocal failed_path
                    candidate = Path(path)
                    if candidate == receipt_path:
                        return {}
                    if candidate.parent.name == directory_name:
                        failed_path = candidate
                        raise json.JSONDecodeError(
                            f"{candidate}: duplicate key {duplicate_key!r}", "{}", 0
                        )
                    return original_load_json(candidate)

                output = io.StringIO()
                with (
                    mock.patch.object(MODULE, "validate_repository", return_value=[]),
                    mock.patch.object(
                        MODULE, "load_json", side_effect=fail_selected_authority
                    ),
                    mock.patch.object(
                        MODULE, "validate_device_lab_execution_receipt"
                    ) as receipt_validator,
                    mock.patch.object(
                        sys,
                        "argv",
                        [
                            str(SCRIPT),
                            "--device-lab-receipt",
                            str(receipt_path),
                            "--json",
                        ],
                    ),
                    contextlib.redirect_stdout(output),
                ):
                    status = MODULE.main()

                self.assertEqual(1, status)
                self.assertIsNotNone(failed_path)
                receipt_validator.assert_not_called()
                report = json.loads(output.getvalue())
                self.assertEqual("fail", report["status"])
                self.assertTrue(
                    any(
                        error.startswith(expected_prefix)
                        and str(failed_path) in error
                        and f"duplicate key '{duplicate_key}'" in error
                        for error in report["errors"]
                    )
                )


    def test_inventory_isolation_rules_pass_and_fail_closed(self) -> None:
        self.assertEqual([], MODULE.validate_inventory_isolation_rules(ROOT))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asmdef = root / MODULE.INVENTORY_PRESENTATION_ASMDEF
            asmdef.parent.mkdir(parents=True)
            asmdef.write_text(
                json.dumps({"name": "Lingkyn.Inventory.Presentation", "references": ["Lingkyn.Inventory.Core", "Unity.ugui"], "noEngineReferences": False}),
                encoding="utf-8",
            )
            runtime = root / MODULE.INVENTORY_AUTHORING_RUNTIME
            runtime.mkdir(parents=True)
            (runtime / "Lookup.cs").write_text(
                "namespace Lingkyn.Inventory.Unity { static class L { static void F() { var x = UnityEngine.Resources.Load(\"a\"); } } }\n",
                encoding="utf-8",
            )
            errors = MODULE.validate_inventory_isolation_rules(root)
        self.assertTrue(any("reference only Lingkyn.Inventory.Core" in error for error in errors), errors)
        self.assertTrue(any("noEngineReferences" in error for error in errors), errors)
        self.assertTrue(any("Resources.Load" in error for error in errors), errors)

    def test_foundation_assembly_references_pass_and_fail_closed(self) -> None:
        self.assertEqual([], MODULE.validate_foundation_assembly_references(ROOT))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asmdef = root / MODULE.FOUNDATIONS_PACKAGES_ROOT / "com.example.foundation" / "Editor" / "Example.Editor.asmdef"
            asmdef.parent.mkdir(parents=True)
            asmdef.write_text(
                json.dumps({"name": "Lingkyn.Example.Editor", "references": ["Lingkyn.Example.Runtime", "Unity.InputSystem", "ConsumerProduct.Runtime", "GUID:0123456789abcdef0123456789abcdef"]}),
                encoding="utf-8",
            )
            errors = MODULE.validate_foundation_assembly_references(root)
        self.assertEqual(2, len(errors), errors)
        self.assertTrue(any("'ConsumerProduct.Runtime'" in error for error in errors), errors)
        self.assertTrue(any("GUID:" in error for error in errors), errors)

    def test_every_error_gets_a_fix_hint(self) -> None:
        explained = MODULE.explain_errors(
            [
                "packages/unity/x/Runtime/A.cs: missing .meta",
                "com.lingkyn.demo: component/package.json version mismatch",
                "Contract test suite failed; no commit or push may proceed",
                "something nobody anticipated",
            ]
        )
        self.assertEqual(4, len(explained))
        self.assertIn(".meta", explained[0]["hint"])
        self.assertIn("LESSON-008", explained[1]["hint"])
        self.assertIn("unittest", explained[2]["hint"])
        self.assertIn("start-here.md", explained[3]["hint"])
        for pattern, hint in MODULE.FIX_HINTS:
            self.assertTrue(hint.strip(), pattern.pattern)

    def test_operating_mandates_validate_and_fail_closed(self) -> None:
        self.assertEqual([], MODULE.validate_operating_mandates(ROOT))
        mandate_path = ROOT / "docs" / "governance" / "mandates" / "weekly-steward.mandate.json"
        original_loader = MODULE.load_json

        def mutate(change):
            payload = json.loads(mandate_path.read_text(encoding="utf-8"))
            change(payload)

            def loader(path: Path):
                return payload if Path(path) == mandate_path else original_loader(Path(path))

            with mock.patch.object(MODULE, "load_json", side_effect=loader):
                return MODULE.validate_operating_mandates(ROOT)

        def expire_before_start(payload: dict) -> None:
            payload["expires_at"] = payload["not_before"]

        self.assertTrue(any("expires_at must follow" in error for error in mutate(expire_before_start)))

        def allow_merge(payload: dict) -> None:
            payload["forbidden_actions"] = ["nothing is forbidden"]

        self.assertTrue(any("must cover 'merge'" in error for error in mutate(allow_merge)))

        def drop_decision(payload: dict) -> None:
            payload.pop("decision")

        self.assertTrue(any("JSON Schema violation" in error for error in mutate(drop_decision)))

    def test_consumer_lessons_register_positive_contract_passes(self) -> None:
        self.assertEqual([], MODULE.validate_consumer_lessons_register(ROOT))
        register = MODULE.load_json(ROOT / MODULE.LESSONS_REGISTER_PATH)
        families = MODULE.live_package_families(ROOT)
        self.assertEqual(
            {"foundations", "inventory", "persistence", "settings", "interaction"},
            families,
        )
        for lesson in register["lessons"]:
            self.assertEqual(
                families,
                {item["family"] for item in lesson["dispositions"]},
                lesson["id"],
            )

    def _lessons_register_with(self, mutate) -> list[str]:
        register_path = ROOT / MODULE.LESSONS_REGISTER_PATH
        original_loader = MODULE.load_json
        mutated = json.loads(register_path.read_text(encoding="utf-8"))
        mutate(mutated)

        def load_with_mutation(path: Path) -> dict:
            return mutated if Path(path) == register_path else original_loader(Path(path))

        with mock.patch.object(MODULE, "load_json", side_effect=load_with_mutation):
            return MODULE.validate_consumer_lessons_register(ROOT)

    def test_consumer_lessons_register_rejects_a_family_that_did_not_respond(self) -> None:
        def drop_settings(register: dict) -> None:
            register["lessons"][0]["dispositions"] = [
                item
                for item in register["lessons"][0]["dispositions"]
                if item["family"] != "settings"
            ]

        errors = self._lessons_register_with(drop_settings)
        self.assertTrue(
            any("must respond for every live family; missing settings" in error for error in errors),
            errors,
        )

    def test_consumer_lessons_register_rejects_gap_without_follow_up(self) -> None:
        def strip_follow_up(register: dict) -> None:
            for item in register["lessons"][0]["dispositions"]:
                if item["status"] == "gap":
                    item.pop("follow_up", None)
                    break

        errors = self._lessons_register_with(strip_follow_up)
        self.assertTrue(any("must name a follow_up" in error for error in errors), errors)

    def test_consumer_lessons_register_rejects_unknown_family_and_missing_evidence(self) -> None:
        def corrupt(register: dict) -> None:
            lesson = register["lessons"][0]
            lesson["dispositions"][0]["family"] = "localization"
            lesson["evidence"].append("docs/standards/lessons/does-not-exist.md")

        errors = self._lessons_register_with(corrupt)
        self.assertTrue(any("unknown family: localization" in error for error in errors), errors)
        self.assertTrue(any("evidence path does not exist" in error for error in errors), errors)

    def test_consumer_lessons_register_rejects_schema_and_policy_drift(self) -> None:
        def drift(register: dict) -> None:
            register["policy"]["gap_requires_follow_up"] = False

        errors = self._lessons_register_with(drift)
        self.assertTrue(any("JSON Schema violation" in error for error in errors), errors)

        def duplicate(register: dict) -> None:
            register["lessons"].append(copy.deepcopy(register["lessons"][0]))

        errors = self._lessons_register_with(duplicate)
        self.assertTrue(any("duplicate lesson id" in error for error in errors), errors)

    def test_foundry_v1_positive_contract_and_fast_structure_pass(self) -> None:
        self.assertEqual([], MODULE.validate_foundry_contract(ROOT))
        self.assertEqual([], MODULE.validate_fast_structure(ROOT))
        registry = json.loads(
            (ROOT / "docs" / "foundry" / "batches" / "batch-registry.v1.json").read_text(
                encoding="utf-8"
            )
        )
        batches = [
            json.loads((ROOT / item["path"]).read_text(encoding="utf-8"))
            for item in registry["batches"]
        ]
        batch_packages = [item for batch in batches for item in batch["packages"]]
        catalog = current_compatibility_profiles()
        package_catalog = json.loads((ROOT / "package-catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(
            {item["id"] for item in package_catalog["packages"]},
            {item["id"] for item in batch_packages},
        )
        self.assertEqual(len(batch_packages), len({item["id"] for item in batch_packages}))
        self.assertEqual(
            {item["id"] for item in catalog["profiles"]},
            {item["compatibility_profile"] for item in batch_packages},
        )

    def test_foundry_first_batch_rejects_membership_and_version_drift(self) -> None:
        batch_path = (
            ROOT
            / "docs"
            / "foundry"
            / "batches"
            / "unity-first-batch.v1.json"
        )
        original_loader = MODULE.load_json
        drifted = json.loads(batch_path.read_text(encoding="utf-8"))
        drifted["packages"][0]["version"] = "9.9.9"
        drifted["packages"].pop()

        def load_with_drift(path: Path) -> dict:
            return drifted if Path(path) == batch_path else original_loader(Path(path))

        with mock.patch.object(MODULE, "load_json", side_effect=load_with_drift):
            errors = MODULE.validate_foundry_contract(ROOT)

        self.assertTrue(any("cover every live catalog package" in error for error in errors))
        self.assertTrue(any("version must match package catalog" in error for error in errors))

    def test_foundry_first_batch_rejects_compatibility_profile_swap(self) -> None:
        batch_path = (
            ROOT
            / "docs"
            / "foundry"
            / "batches"
            / "unity-first-batch.v1.json"
        )
        original_loader = MODULE.load_json
        swapped = json.loads(batch_path.read_text(encoding="utf-8"))
        first_profile = swapped["packages"][0]["compatibility_profile"]
        swapped["packages"][0]["compatibility_profile"] = swapped["packages"][1][
            "compatibility_profile"
        ]
        swapped["packages"][1]["compatibility_profile"] = first_profile

        def load_with_swap(path: Path) -> dict:
            return swapped if Path(path) == batch_path else original_loader(Path(path))

        with mock.patch.object(MODULE, "load_json", side_effect=load_with_swap):
            errors = MODULE.validate_foundry_contract(ROOT)

        self.assertTrue(
            any("compatibility profile identity/version mismatch" in error for error in errors)
        )

    def test_foundry_batch_registry_rejects_cross_batch_package_duplication(self) -> None:
        first_batch_path = (
            ROOT
            / "docs"
            / "foundry"
            / "batches"
            / "unity-first-batch.v1.json"
        )
        next_batch_path = (
            ROOT
            / "docs"
            / "foundry"
            / "batches"
            / "unity-next-systems.v1.json"
        )
        original_loader = MODULE.load_json
        first_batch = json.loads(first_batch_path.read_text(encoding="utf-8"))
        duplicated = json.loads(next_batch_path.read_text(encoding="utf-8"))
        duplicated["packages"].append(copy.deepcopy(first_batch["packages"][0]))

        def load_with_duplicate(path: Path) -> dict:
            return duplicated if Path(path) == next_batch_path else original_loader(Path(path))

        with mock.patch.object(MODULE, "load_json", side_effect=load_with_duplicate):
            errors = MODULE.validate_foundry_contract(ROOT)

        self.assertTrue(
            any("assigns a package to more than one batch" in error for error in errors)
        )

    def test_foundry_scaffolder_is_deterministic_dry_run_first_and_collision_safe(self) -> None:
        example_path = (
            ROOT / "docs" / "foundry" / "unity-package-blueprint.example.json"
        )
        example = json.loads(example_path.read_text(encoding="utf-8"))
        self.assertEqual([], SCAFFOLD_MODULE.validate_blueprint(example))
        first_plan = SCAFFOLD_MODULE.build_scaffold_plan(
            example, (ROOT / "LICENSE").read_text(encoding="utf-8")
        )
        second_plan = SCAFFOLD_MODULE.build_scaffold_plan(
            example, (ROOT / "LICENSE").read_text(encoding="utf-8")
        )
        self.assertEqual(first_plan, second_plan)
        self.assertIn("Assert.Fail", first_plan["Tests/Editor/FoundryScaffoldContractTests.cs"])
        self.assertFalse(json.loads(first_plan[".foundry-scaffold.json"])["catalog_admission"])

        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCAFFOLD_SCRIPT),
                    str(example_path),
                    "--output-root",
                    directory,
                    "--write",
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            report = json.loads(result.stdout)
            self.assertNotEqual(0, result.returncode)
            self.assertEqual("fail", report["status"])
            self.assertTrue(any("Only an admitted blueprint" in error for error in report["errors"]))
            self.assertFalse((Path(directory) / example["package"]["target_path"]).exists())

            admitted = json.loads(json.dumps(example))
            admitted["record_status"] = "admitted"
            admitted["admission"]["implementation_issue"] = (
                "https://github.com/Lingkyn/xr-foundry/issues/52"
            )
            admitted["package"]["family"] = "interaction"
            admitted["package"]["target_path"] = (
                "packages/unity/systems/interaction/com.lingkyn.example-system"
            )
            admitted["admission"]["system_admission_record"] = (
                "docs/foundry/admissions/interaction.v1.json"
            )
            admitted["admission"]["source_manifest"] = (
                "docs/standards/interaction/source-manifest.json"
            )
            admitted["admission"]["positive_sources"] = [
                "https://registry.khronos.org/OpenXR/specs/1.1/html/xrspec.html#input"
            ]
            self.assertEqual([], SCAFFOLD_MODULE.validate_blueprint(admitted))
            admitted_plan = SCAFFOLD_MODULE.build_scaffold_plan(
                admitted, (ROOT / "LICENSE").read_text(encoding="utf-8")
            )
            target = SCAFFOLD_MODULE.resolve_target(
                Path(directory), admitted["package"]["target_path"]
            )
            SCAFFOLD_MODULE.write_scaffold(target, admitted_plan)
            self.assertTrue((target / ".foundry-scaffold.json").exists())
            with self.assertRaises(FileExistsError):
                SCAFFOLD_MODULE.write_scaffold(target, admitted_plan)

            failed_target = target.parent / "com.lingkyn.atomic-failure"
            with mock.patch.object(
                SCAFFOLD_MODULE,
                "write_plan_to_directory",
                side_effect=OSError("simulated write failure"),
            ):
                with self.assertRaises(OSError):
                    SCAFFOLD_MODULE.write_scaffold(failed_target, admitted_plan)
            self.assertFalse(failed_target.exists())
            self.assertEqual(
                [],
                list(failed_target.parent.glob(f".{failed_target.name}.foundry-*")),
            )

    def test_foundry_admitted_blueprint_rejects_unadmitted_positive_source(self) -> None:
        blueprint = json.loads(
            (
                ROOT / "docs" / "foundry" / "unity-package-blueprint.example.json"
            ).read_text(encoding="utf-8")
        )
        blueprint["record_status"] = "admitted"
        blueprint["admission"]["implementation_issue"] = (
            "https://github.com/Lingkyn/xr-foundry/issues/52"
        )
        blueprint["package"]["family"] = "interaction"
        blueprint["package"]["target_path"] = (
            "packages/unity/systems/interaction/com.lingkyn.example-system"
        )
        blueprint["admission"]["system_admission_record"] = (
            "docs/foundry/admissions/interaction.v1.json"
        )
        blueprint["admission"]["source_manifest"] = (
            "docs/standards/interaction/source-manifest.json"
        )
        blueprint["admission"]["positive_sources"] = [
            "https://example.invalid/unadmitted-source"
        ]

        errors = SCAFFOLD_MODULE.validate_blueprint(blueprint)

        self.assertTrue(
            any("positive_sources must be admitted by source_manifest" in error for error in errors)
        )

    def test_foundry_admitted_blueprint_requires_matching_system_admission(self) -> None:
        blueprint = json.loads(
            (
                ROOT / "docs" / "foundry" / "blueprints" / "interaction-core.v1.json"
            ).read_text(encoding="utf-8")
        )
        blueprint["admission"]["system_admission_record"] = (
            "docs/foundry/admissions/settings.v1.json"
        )

        errors = SCAFFOLD_MODULE.validate_blueprint(blueprint)

        self.assertTrue(
            any("family must match" in error for error in errors)
        )

    def test_foundry_next_batch_rejects_placeholder_actions(self) -> None:
        queue_path = ROOT / "docs" / "foundry" / "queue" / "next-batch.json"
        original_loader = MODULE.load_json
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["candidates"][0]["exact_next_action"] = "<placeholder>"

        def load_with_placeholder(path: Path) -> dict:
            return queue if Path(path) == queue_path else original_loader(Path(path))

        with mock.patch.object(MODULE, "load_json", side_effect=load_with_placeholder):
            errors = MODULE.validate_foundry_contract(ROOT)

        self.assertTrue(any("placeholder text is prohibited" in error for error in errors))

    def test_foundry_blueprint_rejects_unsafe_or_mismatched_target(self) -> None:
        blueprint = json.loads(
            (
                ROOT / "docs" / "foundry" / "unity-package-blueprint.example.json"
            ).read_text(encoding="utf-8")
        )
        blueprint["package"]["target_path"] = (
            "packages/unity/systems/example-system/com.lingkyn.different"
        )
        errors = SCAFFOLD_MODULE.validate_blueprint(blueprint)
        self.assertTrue(any("target_path leaf must equal package.id" in error for error in errors))

    def test_component_model_resolves_deterministically_and_lock_is_current(self) -> None:
        self.assertEqual([], MODULE.validate_component_model(ROOT))
        first_lock, first_errors = MODULE.build_composition_lock(ROOT)
        second_lock, second_errors = MODULE.build_composition_lock(ROOT)

        self.assertEqual([], first_errors)
        self.assertEqual([], second_errors)
        self.assertEqual(first_lock, second_lock)
        self.assertIsNotNone(first_lock)
        assert first_lock is not None
        self.assertEqual("xr-foundry.composition_lock.v2", first_lock["schema"])
        self.assertEqual("0.2.0", first_lock["model_version"])
        self.assertEqual(13, len(first_lock["resolution"]["components"]))
        self.assertTrue(first_lock["claims"]["bindings_implemented"])
        self.assertFalse(first_lock["claims"]["runtime_ready"])
        self.assertEqual(
            "not_claimed_for_this_composition",
            first_lock["claims"]["unity_compile"],
        )
        self.assertEqual("not_claimed", first_lock["claims"]["device_runtime"])
        self.assertEqual(7, len(first_lock["resolution"]["bindings"]))
        expected_binding_sources = {
            "interaction-to-inventory-intent": "InteractionToInventoryIntentAdapter.cs",
            "inventory-to-persistence": "InventoryToPersistenceAdapter.cs",
            "settings-to-interaction-policy": "SettingsToInteractionPolicyAdapter.cs",
            "unity-input-to-semantic-interaction": "UnityInputSemanticInteractionAdapter.cs",
            "inventory-presentation-to-ugui-renderer": "InventoryUguiXrSurfaceAdapter.cs",
            "inventory-ugui-renderer-to-xr-surface": "InventoryUguiXrSurfaceAdapter.cs",
            "settings-to-persistence-rehydration": "SettingsPersistenceRehydrationAdapter.cs",
        }
        self.assertEqual(
            set(expected_binding_sources),
            {binding["id"] for binding in first_lock["resolution"]["bindings"]},
        )
        for binding in first_lock["resolution"]["bindings"]:
            implementation = binding["implementation"]
            self.assertEqual("implemented", implementation["status"])
            source = ROOT / implementation["source_path"]
            self.assertTrue(source.is_file())
            self.assertEqual(expected_binding_sources[binding["id"]], source.name)
            self.assertEqual(
                hashlib.sha256(source.read_bytes()).hexdigest(),
                implementation["source_sha256"],
            )
        self.assertEqual(
            15,
            len(list(ROOT.glob("packages/unity/**/foundry.component.json"))),
        )

        result = subprocess.run(
            [sys.executable, str(COMPOSE_SCRIPT), "--check", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual("pass", report["status"])
        self.assertEqual(13, report["component_count"])
        self.assertTrue(report["bindings_implemented"])
        self.assertFalse(report["runtime_ready"])

    def test_reference_consumer_materializes_every_typed_endpoint_package(self) -> None:
        consumer = ROOT / "compositions" / "unity" / "reference-system" / "consumer"
        manifest = MODULE.load_json(consumer / "Packages" / "manifest.json")
        runtime_asmdef = MODULE.load_json(
            consumer
            / "Assets"
            / "XRFoundry.ReferenceSystem"
            / "Runtime"
            / "XRFoundry.ReferenceSystem.asmdef"
        )
        editmode_asmdef = MODULE.load_json(
            consumer
            / "Assets"
            / "XRFoundry.ReferenceSystem"
            / "Tests"
            / "EditMode"
            / "XRFoundry.ReferenceSystem.EditMode.Tests.asmdef"
        )
        playmode_asmdef = MODULE.load_json(
            consumer
            / "Assets"
            / "XRFoundry.ReferenceSystem"
            / "Tests"
            / "PlayMode"
            / "XRFoundry.ReferenceSystem.PlayMode.Tests.asmdef"
        )

        embedded_package_ids = {
            Path(path).name for path in MATERIALIZER_MODULE.EMBEDDED_PACKAGES
        }
        expected_endpoint_packages = {
            "com.lingkyn.interaction.unity",
            "com.lingkyn.inventory.ugui",
            "com.lingkyn.inventory.xr.ugui",
            "com.lingkyn.persistence.unity",
            "com.lingkyn.settings.unity",
        }
        self.assertEqual(embedded_package_ids, set(manifest["testables"]))
        self.assertTrue(expected_endpoint_packages.issubset(embedded_package_ids))

        expected_runtime_assemblies = {
            "Lingkyn.Interaction.Unity",
            "Lingkyn.Inventory.UGUI",
            "Lingkyn.Inventory.XR.UGUI",
            "Lingkyn.Persistence.Unity",
            "Lingkyn.Settings.Unity",
            "Unity.InputSystem",
        }
        self.assertTrue(
            expected_runtime_assemblies.issubset(set(runtime_asmdef["references"]))
        )
        self.assertFalse(runtime_asmdef["noEngineReferences"])
        for test_asmdef in (editmode_asmdef, playmode_asmdef):
            self.assertTrue(
                expected_runtime_assemblies.issubset(set(test_asmdef["references"]))
            )
            self.assertIn("UnityEngine.UI", test_asmdef["references"])

    def test_v2_composition_lock_tracks_adapter_source_bytes(self) -> None:
        lock_path = ROOT / "compositions/unity/reference-system/foundry.lock.json"
        current_lock = MODULE.load_json(lock_path)
        implementation = current_lock["resolution"]["bindings"][0]["implementation"]
        source_path = ROOT / implementation["source_path"]
        path_type = type(source_path)
        original_read_bytes = path_type.read_bytes

        def read_with_adapter_mutation(path: Path) -> bytes:
            content = original_read_bytes(path)
            if Path(path) == source_path:
                return content + b"\n// source-byte mutation\n"
            return content

        with mock.patch.object(path_type, "read_bytes", new=read_with_adapter_mutation):
            rebuilt_lock, build_errors = MODULE.build_composition_lock(ROOT)
            validation_errors = MODULE.validate_component_model(ROOT)

        self.assertEqual([], build_errors)
        self.assertIsNotNone(rebuilt_lock)
        assert rebuilt_lock is not None
        rebuilt_implementation = rebuilt_lock["resolution"]["bindings"][0][
            "implementation"
        ]
        self.assertNotEqual(
            implementation["source_sha256"],
            rebuilt_implementation["source_sha256"],
        )
        self.assertNotEqual(current_lock, rebuilt_lock)
        self.assertTrue(
            any("composition lock is stale" in error for error in validation_errors)
        )

    def test_v2_composition_rejects_unsafe_adapter_sources(self) -> None:
        composition_path = ROOT / MODULE.REFERENCE_COMPOSITION_PATH
        original = MODULE.load_json(composition_path)

        missing = copy.deepcopy(original)
        missing["bindings"][0]["implementation"]["source_path"] = (
            "consumer/Assets/XRFoundry.ReferenceSystem/Runtime/Bindings/MissingAdapter.cs"
        )
        _, missing_errors = MODULE.build_composition_lock(
            ROOT, composition_path, missing
        )
        self.assertTrue(any("source_path is missing" in error for error in missing_errors))

        escaping = copy.deepcopy(original)
        escaping["bindings"][0]["implementation"]["source_path"] = (
            "../foundry.project.json"
        )
        _, escaping_errors = MODULE.build_composition_lock(
            ROOT, composition_path, escaping
        )
        self.assertTrue(
            any("canonical and start with consumer/" in error for error in escaping_errors)
        )

        control_character = copy.deepcopy(original)
        control_character["bindings"][0]["implementation"]["source_path"] = (
            "consumer/Adapter\x00.cs"
        )
        _, control_errors = MODULE.build_composition_lock(
            ROOT, composition_path, control_character
        )
        self.assertTrue(
            any("non-empty POSIX path" in error for error in control_errors)
        )

        invalid_assembly = copy.deepcopy(original)
        invalid_assembly["bindings"][0]["implementation"]["assembly"] = (
            "XRFoundry.ReferenceSystem\n"
        )
        manifest_schema_path, dispatch_errors = (
            MODULE.composition_manifest_schema_path(invalid_assembly)
        )
        self.assertEqual([], dispatch_errors)
        assert manifest_schema_path is not None
        self.assertTrue(
            MODULE.validate_json_schema_instance(
                invalid_assembly,
                ROOT / manifest_schema_path,
                "v2 composition manifest",
            )
        )
        _, assembly_errors = MODULE.build_composition_lock(
            ROOT, composition_path, invalid_assembly
        )
        self.assertTrue(
            any("exact ASCII assembly name" in error for error in assembly_errors)
        )

        symlinked = copy.deepcopy(original)
        source_path = (
            composition_path.parent
            / symlinked["bindings"][0]["implementation"]["source_path"]
        )
        path_type = type(source_path)
        original_is_symlink = path_type.is_symlink

        def mark_adapter_as_symlink(path: Path) -> bool:
            if Path(path) == source_path:
                return True
            return original_is_symlink(path)

        with mock.patch.object(path_type, "is_symlink", new=mark_adapter_as_symlink):
            _, symlink_errors = MODULE.build_composition_lock(
                ROOT, composition_path, symlinked
            )
        self.assertTrue(
            any("must not be a symbolic link" in error for error in symlink_errors)
        )

        consumer_path = composition_path.parent / "consumer"

        def mark_consumer_as_symlink(path: Path) -> bool:
            if Path(path) == consumer_path:
                return True
            return original_is_symlink(path)

        with mock.patch.object(
            path_type, "is_symlink", new=mark_consumer_as_symlink
        ):
            _, consumer_symlink_errors = MODULE.build_composition_lock(
                ROOT, composition_path, original
            )
        self.assertTrue(
            any(
                "consumer directory must not be a symbolic link" in error
                for error in consumer_symlink_errors
            )
        )

    def test_v2_adapter_source_must_match_nearest_unity_assembly(self) -> None:
        composition_path = ROOT / MODULE.REFERENCE_COMPOSITION_PATH
        composition = MODULE.load_json(composition_path)
        implementation = composition["bindings"][0]["implementation"]
        implementation["source_path"] = (
            "consumer/Assets/XRFoundry.ReferenceSystem/Tests/PlayMode/"
            "ReferenceSystemIntegrationPlayModeTests.cs"
        )
        implementation["assembly"] = "Made.Up.Assembly"

        lock, errors = MODULE.build_composition_lock(
            ROOT, composition_path, composition
        )

        self.assertIsNone(lock)
        self.assertTrue(
            any(
                "XRFoundry.ReferenceSystem.PlayMode.Tests" in error
                and "Made.Up.Assembly" in error
                for error in errors
            )
        )

        implementation["assembly"] = "XRFoundry.ReferenceSystem.PlayMode.Tests"
        lock, errors = MODULE.build_composition_lock(
            ROOT, composition_path, composition
        )
        self.assertEqual([], errors)
        self.assertIsNotNone(lock)

    def test_adapter_assembly_scope_fails_closed_on_ambiguous_or_unsafe_metadata(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composition_path = (
                root / "compositions" / "unity" / "sample" / "foundry.project.json"
            )
            source_path = (
                composition_path.parent
                / "consumer/Assets/Sample/Runtime/Bindings/Adapter.cs"
            )
            source_path.parent.mkdir(parents=True)
            source_path.write_text("internal sealed class Adapter {}\n", encoding="utf-8")
            source, source_error = MODULE.resolve_composition_adapter_source(
                root,
                composition_path,
                "consumer/Assets/Sample/Runtime/Bindings/Adapter.cs",
            )
            self.assertIsNone(source_error)
            assert source is not None

            missing_error = MODULE.validate_composition_adapter_assembly(
                root, composition_path, source, "Sample.Runtime"
            )
            self.assertIn("no Unity assembly definition", missing_error)

            runtime_directory = source_path.parent.parent
            asmdef_path = runtime_directory / "Sample.Runtime.asmdef"
            asmdef_path.write_text('{"name":"Wrong.Runtime"}', encoding="utf-8")
            wrong_name_error = MODULE.validate_composition_adapter_assembly(
                root, composition_path, source, "Sample.Runtime"
            )
            self.assertIn("Wrong.Runtime", wrong_name_error)
            self.assertIn("Sample.Runtime", wrong_name_error)

            asmdef_path.write_text('{"name":"Sample.Runtime"}', encoding="utf-8")
            shadow_path = source_path.parent / "Shadow.asmdef"
            shadow_path.write_text('{"name":"Shadow.Runtime"}', encoding="utf-8")
            shadow_error = MODULE.validate_composition_adapter_assembly(
                root, composition_path, source, "Sample.Runtime"
            )
            self.assertIn("Shadow.Runtime", shadow_error)
            shadow_path.unlink()

            duplicate_asmdef = runtime_directory / "Second.asmdef"
            duplicate_asmdef.write_text('{"name":"Sample.Runtime"}', encoding="utf-8")
            duplicate_scope_error = MODULE.validate_composition_adapter_assembly(
                root, composition_path, source, "Sample.Runtime"
            )
            self.assertIn("exactly one .asmdef", duplicate_scope_error)
            duplicate_asmdef.unlink()

            asmdef_path.write_text('{"name":', encoding="utf-8")
            malformed_error = MODULE.validate_composition_adapter_assembly(
                root, composition_path, source, "Sample.Runtime"
            )
            self.assertIn("invalid JSON", malformed_error)

            asmdef_path.write_text(
                '{"name":"Sample.Runtime","nested":{"key":1,"key":2}}',
                encoding="utf-8",
            )
            duplicate_key_error = MODULE.validate_composition_adapter_assembly(
                root, composition_path, source, "Sample.Runtime"
            )
            self.assertIn("duplicate key 'key'", duplicate_key_error)

            asmdef_path.unlink()
            asmdef_path.mkdir()
            nonregular_error = MODULE.validate_composition_adapter_assembly(
                root, composition_path, source, "Sample.Runtime"
            )
            self.assertIn("regular file", nonregular_error)
            asmdef_path.rmdir()

            outside_asmdef = root / "outside.asmdef"
            outside_asmdef.write_text('{"name":"Sample.Runtime"}', encoding="utf-8")
            asmdef_path.symlink_to(outside_asmdef)
            symlink_error = MODULE.validate_composition_adapter_assembly(
                root, composition_path, source, "Sample.Runtime"
            )
            self.assertIn("symbolic link", symlink_error)
            asmdef_path.unlink()

            asmdef_path.write_text('{"name":"Sample.Runtime"}', encoding="utf-8")
            asmref_path = source_path.parent / "Redirect.asmref"
            asmref_path.write_text('{"reference":"Sample.Runtime"}', encoding="utf-8")
            asmref_error = MODULE.validate_composition_adapter_assembly(
                root, composition_path, source, "Sample.Runtime"
            )
            self.assertIn("asmref is unsupported", asmref_error)

    def test_v2_composition_rejects_duplicate_binding_and_unsafe_lock_path(self) -> None:
        composition_path = ROOT / MODULE.REFERENCE_COMPOSITION_PATH
        duplicate = MODULE.load_json(composition_path)
        duplicate["bindings"].append(copy.deepcopy(duplicate["bindings"][0]))
        _, duplicate_errors = MODULE.build_composition_lock(
            ROOT, composition_path, duplicate
        )
        self.assertTrue(any("duplicate binding id" in error for error in duplicate_errors))

        unsafe_lock = MODULE.load_json(composition_path)
        unsafe_lock["lock_path"] = "foundry.lock.json"
        _, lock_errors = MODULE.build_composition_lock(
            ROOT, composition_path, unsafe_lock
        )
        self.assertTrue(any("sibling foundry.lock.json" in error for error in lock_errors))

        lock_target = composition_path.parent / "foundry.lock.json"
        path_type = type(lock_target)
        original_is_symlink = path_type.is_symlink

        def mark_lock_as_symlink(path: Path) -> bool:
            if Path(path) == lock_target:
                return True
            return original_is_symlink(path)

        with mock.patch.object(path_type, "is_symlink", new=mark_lock_as_symlink):
            _, symlink_lock_errors = MODULE.build_composition_lock(
                ROOT, composition_path, MODULE.load_json(composition_path)
            )
        self.assertTrue(
            any("lock must not be a symbolic link" in error for error in symlink_lock_errors)
        )

    def test_v2_lock_schema_rejects_noncanonical_source_path(self) -> None:
        original_lock = MODULE.load_json(
            ROOT / "compositions/unity/reference-system/foundry.lock.json"
        )
        lock = copy.deepcopy(original_lock)
        lock["resolution"]["bindings"][0]["implementation"]["source_path"] = (
            "compositions/example/consumer/../../secret.cs"
        )
        lock_schema_path, dispatch_errors = MODULE.composition_lock_schema_path(lock)
        self.assertEqual([], dispatch_errors)
        assert lock_schema_path is not None
        schema_errors = MODULE.validate_json_schema_instance(
            lock,
            ROOT / lock_schema_path,
            "v2 composition lock",
        )
        self.assertTrue(schema_errors)

        invalid_assembly_lock = copy.deepcopy(original_lock)
        invalid_assembly_lock["resolution"]["bindings"][0]["implementation"][
            "assembly"
        ] = "XRFoundry.ReferenceSystem\n"
        assembly_schema_errors = MODULE.validate_json_schema_instance(
            invalid_assembly_lock,
            ROOT / lock_schema_path,
            "v2 composition lock",
        )
        self.assertTrue(assembly_schema_errors)

    def test_v2_semver_matches_semver_2_numeric_prerelease_rules(self) -> None:
        composition_path = ROOT / MODULE.REFERENCE_COMPOSITION_PATH
        original_composition = MODULE.load_json(composition_path)
        manifest_schema_path, dispatch_errors = (
            MODULE.composition_manifest_schema_path(original_composition)
        )
        self.assertEqual([], dispatch_errors)
        assert manifest_schema_path is not None

        original_lock = MODULE.load_json(
            ROOT / "compositions/unity/reference-system/foundry.lock.json"
        )
        lock_schema_path, lock_dispatch_errors = MODULE.composition_lock_schema_path(
            original_lock
        )
        self.assertEqual([], lock_dispatch_errors)
        assert lock_schema_path is not None

        valid_versions = (
            "0.2.0-0",
            "0.2.0-alpha.1",
            "0.2.0-0A",
            "0.2.0+001",
            "1.2.3-alpha.1+001",
        )
        for version in valid_versions:
            with self.subTest(valid=version):
                self.assertIsNotNone(MODULE.SEMVER_V2_PATTERN.fullmatch(version))
                composition = copy.deepcopy(original_composition)
                composition["version"] = version
                self.assertEqual(
                    [],
                    MODULE.validate_json_schema_instance(
                        composition,
                        ROOT / manifest_schema_path,
                        "v2 composition manifest",
                    ),
                )
                lock, build_errors = MODULE.build_composition_lock(
                    ROOT, composition_path, composition
                )
                self.assertEqual([], build_errors)
                self.assertIsNotNone(lock)
                schema_lock = copy.deepcopy(original_lock)
                schema_lock["composition"]["version"] = version
                self.assertEqual(
                    [],
                    MODULE.validate_json_schema_instance(
                        schema_lock,
                        ROOT / lock_schema_path,
                        "v2 composition lock",
                    ),
                )

        invalid_versions = (
            "0.2.0-01",
            "0.2.0-alpha.01",
            "01.2.3",
        )
        for version in invalid_versions:
            with self.subTest(invalid=version):
                self.assertIsNone(MODULE.SEMVER_V2_PATTERN.fullmatch(version))
                composition = copy.deepcopy(original_composition)
                composition["version"] = version
                self.assertTrue(
                    MODULE.validate_json_schema_instance(
                        composition,
                        ROOT / manifest_schema_path,
                        "v2 composition manifest",
                    )
                )
                lock, build_errors = MODULE.build_composition_lock(
                    ROOT, composition_path, composition
                )
                self.assertIsNone(lock)
                self.assertTrue(
                    any("version must be exact SemVer" in error for error in build_errors)
                )
                schema_lock = copy.deepcopy(original_lock)
                schema_lock["composition"]["version"] = version
                self.assertTrue(
                    MODULE.validate_json_schema_instance(
                        schema_lock,
                        ROOT / lock_schema_path,
                        "v2 composition lock",
                    )
                )

    def test_v1_semver_contract_remains_byte_compatible(self) -> None:
        composition_path = ROOT / MODULE.REFERENCE_COMPOSITION_PATH
        v1_composition = MODULE.load_json(composition_path)
        v1_composition["schema"] = "xr-foundry.composition_manifest.v1"
        v1_composition["model_version"] = "0.1.0"
        v1_composition["version"] = "0.2.0-01"
        for binding in v1_composition["bindings"]:
            binding["implementation"] = "consumer_owned_adapter_pending"

        schema_path, dispatch_errors = MODULE.composition_manifest_schema_path(
            v1_composition
        )
        self.assertEqual([], dispatch_errors)
        self.assertEqual(MODULE.COMPOSITION_MANIFEST_SCHEMA_PATH, schema_path)
        assert schema_path is not None
        self.assertEqual(
            [],
            MODULE.validate_json_schema_instance(
                v1_composition,
                ROOT / schema_path,
                "v1 composition manifest",
            ),
        )
        lock, build_errors = MODULE.build_composition_lock(
            ROOT, composition_path, v1_composition
        )
        self.assertEqual([], build_errors)
        self.assertIsNotNone(lock)
        assert lock is not None
        self.assertEqual("0.2.0-01", lock["composition"]["version"])

    def test_composition_schema_dispatch_fails_closed(self) -> None:
        composition = MODULE.load_json(ROOT / MODULE.REFERENCE_COMPOSITION_PATH)
        mismatched = copy.deepcopy(composition)
        mismatched["model_version"] = "0.1.0"
        _, mismatch_errors = MODULE.build_composition_lock(
            ROOT, MODULE.REFERENCE_COMPOSITION_PATH, mismatched
        )
        self.assertTrue(any("schema/model mismatch" in error for error in mismatch_errors))

        unknown = copy.deepcopy(composition)
        unknown["schema"] = "xr-foundry.composition_manifest.v99"
        _, unknown_errors = MODULE.build_composition_lock(
            ROOT, MODULE.REFERENCE_COMPOSITION_PATH, unknown
        )
        self.assertTrue(any("unsupported composition manifest schema" in error for error in unknown_errors))

    def test_v2_canonical_metadata_rejects_terminal_control_characters(self) -> None:
        composition_path = ROOT / MODULE.REFERENCE_COMPOSITION_PATH
        original_composition = MODULE.load_json(composition_path)
        manifest_paths = {
            "composition.id": ("id",),
            "composition.version": ("version",),
            "binding.id": ("bindings", 0, "id"),
            "binding.assembly": ("bindings", 0, "implementation", "assembly"),
        }

        def append_lf(payload: dict, path: tuple[object, ...]) -> None:
            cursor: object = payload
            for part in path[:-1]:
                if isinstance(part, int):
                    assert isinstance(cursor, list)
                    cursor = cursor[part]
                else:
                    assert isinstance(cursor, dict)
                    cursor = cursor[part]
            key = path[-1]
            assert isinstance(cursor, dict)
            assert isinstance(key, str)
            cursor[key] += "\n"

        manifest_schema_path, dispatch_errors = (
            MODULE.composition_manifest_schema_path(original_composition)
        )
        self.assertEqual([], dispatch_errors)
        assert manifest_schema_path is not None
        for label, field_path in manifest_paths.items():
            with self.subTest(contract="manifest-and-builder", field=label):
                mutated = copy.deepcopy(original_composition)
                append_lf(mutated, field_path)
                self.assertTrue(
                    MODULE.validate_json_schema_instance(
                        mutated,
                        ROOT / manifest_schema_path,
                        "v2 composition manifest",
                    )
                )
                lock, build_errors = MODULE.build_composition_lock(
                    ROOT, composition_path, mutated
                )
                self.assertIsNone(lock)
                self.assertTrue(build_errors)

        non_string_binding_id = copy.deepcopy(original_composition)
        non_string_binding_id["bindings"][0]["id"] = 123
        self.assertTrue(
            MODULE.validate_json_schema_instance(
                non_string_binding_id,
                ROOT / manifest_schema_path,
                "v2 composition manifest",
            )
        )
        lock, build_errors = MODULE.build_composition_lock(
            ROOT, composition_path, non_string_binding_id
        )
        self.assertIsNone(lock)
        self.assertTrue(
            any("binding id must be" in error for error in build_errors)
        )

        original_lock = MODULE.load_json(
            ROOT / "compositions/unity/reference-system/foundry.lock.json"
        )
        lock_paths = {
            "composition.id": ("composition", "id"),
            "composition.version": ("composition", "version"),
            "binding.id": ("resolution", "bindings", 0, "id"),
            "binding.assembly": (
                "resolution",
                "bindings",
                0,
                "implementation",
                "assembly",
            ),
        }
        lock_schema_path, lock_dispatch_errors = MODULE.composition_lock_schema_path(
            original_lock
        )
        self.assertEqual([], lock_dispatch_errors)
        assert lock_schema_path is not None
        for label, field_path in lock_paths.items():
            with self.subTest(contract="lock", field=label):
                mutated = copy.deepcopy(original_lock)
                append_lf(mutated, field_path)
                self.assertTrue(
                    MODULE.validate_json_schema_instance(
                        mutated,
                        ROOT / lock_schema_path,
                        "v2 composition lock",
                    )
                )

    def test_v1_pending_composition_remains_supported(self) -> None:
        composition_path = ROOT / MODULE.REFERENCE_COMPOSITION_PATH
        v1_composition = MODULE.load_json(composition_path)
        v1_composition["schema"] = "xr-foundry.composition_manifest.v1"
        v1_composition["model_version"] = "0.1.0"
        for binding in v1_composition["bindings"]:
            binding["implementation"] = "consumer_owned_adapter_pending"
        duplicate_binding_id = v1_composition["bindings"][0]["id"]
        v1_composition["bindings"].append(
            copy.deepcopy(v1_composition["bindings"][0])
        )

        manifest_schema_path, dispatch_errors = (
            MODULE.composition_manifest_schema_path(v1_composition)
        )
        self.assertEqual([], dispatch_errors)
        self.assertEqual(MODULE.COMPOSITION_MANIFEST_SCHEMA_PATH, manifest_schema_path)
        self.assertEqual(
            [],
            MODULE.validate_json_schema_instance(
                v1_composition,
                ROOT / manifest_schema_path,
                "v1 composition manifest",
            ),
        )

        v1_lock, build_errors = MODULE.build_composition_lock(
            ROOT, composition_path, v1_composition
        )
        self.assertEqual([], build_errors)
        self.assertIsNotNone(v1_lock)
        assert v1_lock is not None
        self.assertEqual("xr-foundry.composition_lock.v1", v1_lock["schema"])
        self.assertEqual("0.1.0", v1_lock["model_version"])
        self.assertEqual(
            {
                "structural_resolution": "resolved",
                "runtime_ready": False,
                "unity_compile": "not_claimed_for_this_composition",
                "device_runtime": "not_claimed",
            },
            v1_lock["claims"],
        )
        self.assertTrue(
            all(
                binding["implementation"] == "consumer_owned_adapter_pending"
                for binding in v1_lock["resolution"]["bindings"]
            )
        )
        self.assertEqual(
            2,
            sum(
                binding["id"] == duplicate_binding_id
                for binding in v1_lock["resolution"]["bindings"]
            ),
        )
        lock_schema_path, lock_dispatch_errors = MODULE.composition_lock_schema_path(
            v1_lock
        )
        self.assertEqual([], lock_dispatch_errors)
        self.assertEqual(MODULE.COMPOSITION_LOCK_SCHEMA_PATH, lock_schema_path)
        self.assertEqual(
            [],
            MODULE.validate_json_schema_instance(
                v1_lock,
                ROOT / lock_schema_path,
                "v1 composition lock",
            ),
        )

    def test_composition_rejects_missing_and_incompatible_capability(self) -> None:
        composition_path = ROOT / MODULE.REFERENCE_COMPOSITION_PATH
        composition = MODULE.load_json(composition_path)
        composition["required_capabilities"].append(
            {
                "id": "xr-foundry.inventory.renderer.uitoolkit",
                "version": "1.0.0",
            }
        )

        _, missing_errors = MODULE.build_composition_lock(
            ROOT, composition_path, composition
        )

        self.assertTrue(
            any(
                "missing capability provider for "
                "xr-foundry.inventory.renderer.uitoolkit@1.0.0" in error
                for error in missing_errors
            )
        )

        incompatible = MODULE.load_json(composition_path)
        domain_requirement = next(
            item
            for item in incompatible["required_capabilities"]
            if item["id"] == "xr-foundry.inventory.domain"
        )
        domain_requirement["version"] = "2.0.0"

        _, incompatible_errors = MODULE.build_composition_lock(
            ROOT, composition_path, incompatible
        )

        self.assertTrue(
            any(
                "missing capability provider for xr-foundry.inventory.domain@2.0.0"
                in error
                for error in incompatible_errors
            )
        )

    def test_composition_rejects_ambiguous_variant_provider(self) -> None:
        composition_path = ROOT / MODULE.REFERENCE_COMPOSITION_PATH
        composition = MODULE.load_json(composition_path)
        composition["components"].append(
            {"id": "com.lingkyn.inventory.uitoolkit", "version": "0.1.0"}
        )

        _, errors = MODULE.build_composition_lock(ROOT, composition_path, composition)

        self.assertTrue(
            any(
                "xr-foundry.inventory.renderer@1.0.0 requires exactly one provider"
                in error
                for error in errors
            )
        )

    def test_composition_rejects_dependency_cycle(self) -> None:
        manifest_path = (
            ROOT
            / "packages/unity/systems/interaction/com.lingkyn.interaction.core"
            / "foundry.component.json"
        )
        original_loader = MODULE.load_json
        cyclic_manifest = original_loader(manifest_path)
        cyclic_manifest["requires"].append(
            {"id": "xr-foundry.interaction.unity-input", "version": "1.0.0"}
        )

        def load_with_cycle(path: Path) -> dict:
            return (
                copy.deepcopy(cyclic_manifest)
                if Path(path) == manifest_path
                else original_loader(Path(path))
            )

        with mock.patch.object(MODULE, "load_json", side_effect=load_with_cycle):
            _, errors = MODULE.build_composition_lock(ROOT)

        self.assertTrue(any("dependency cycle detected" in error for error in errors))

    def test_component_model_rejects_package_dependency_and_lock_drift(self) -> None:
        manifest_path = (
            ROOT
            / "packages/unity/systems/interaction/com.lingkyn.interaction.unity"
            / "foundry.component.json"
        )
        lock_path = (
            ROOT / "compositions/unity/reference-system/foundry.lock.json"
        )
        original_loader = MODULE.load_json
        drifted_manifest = original_loader(manifest_path)
        drifted_manifest["requires"] = []
        drifted_lock = original_loader(lock_path)
        drifted_lock["resolution"]["dependency_order"] = list(
            reversed(drifted_lock["resolution"]["dependency_order"])
        )

        def load_with_drift(path: Path) -> dict:
            if Path(path) == manifest_path:
                return copy.deepcopy(drifted_manifest)
            if Path(path) == lock_path:
                return copy.deepcopy(drifted_lock)
            return original_loader(Path(path))

        with mock.patch.object(MODULE, "load_json", side_effect=load_with_drift):
            errors = MODULE.validate_component_model(ROOT)

        self.assertTrue(
            any("requirements must match internal package dependencies" in error for error in errors)
        )
        self.assertTrue(any("composition lock is stale" in error for error in errors))

    def test_component_model_rejects_runtime_promotion_without_new_contract(self) -> None:
        composition = MODULE.load_json(ROOT / MODULE.REFERENCE_COMPOSITION_PATH)
        composition["bindings"][0]["implementation"] = {
            "kind": "component_provided",
            "status": "implemented",
        }
        manifest_schema_path, dispatch_errors = (
            MODULE.composition_manifest_schema_path(composition)
        )
        self.assertEqual([], dispatch_errors)
        assert manifest_schema_path is not None
        composition_errors = MODULE.validate_json_schema_instance(
            composition,
            ROOT / manifest_schema_path,
            "composition manifest",
        )

        lock = MODULE.load_json(
            ROOT / "compositions/unity/reference-system/foundry.lock.json"
        )
        lock["claims"]["runtime_ready"] = True
        lock_schema_path, lock_dispatch_errors = MODULE.composition_lock_schema_path(
            lock
        )
        self.assertEqual([], lock_dispatch_errors)
        assert lock_schema_path is not None
        lock_errors = MODULE.validate_json_schema_instance(
            lock,
            ROOT / lock_schema_path,
            "composition lock",
        )

        self.assertTrue(composition_errors)
        self.assertTrue(any("False was expected" in error for error in lock_errors))

    def test_component_model_rejects_internal_dependency_version_drift(self) -> None:
        package_manifest_path = (
            ROOT
            / "packages/unity/systems/interaction/com.lingkyn.interaction.unity"
            / "package.json"
        )
        original_loader = MODULE.load_json
        drifted_package_manifest = original_loader(package_manifest_path)
        drifted_package_manifest["dependencies"]["com.lingkyn.interaction.core"] = "9.9.9"

        def load_with_dependency_drift(path: Path) -> dict:
            return (
                copy.deepcopy(drifted_package_manifest)
                if Path(path) == package_manifest_path
                else original_loader(Path(path))
            )

        with mock.patch.object(
            MODULE, "load_json", side_effect=load_with_dependency_drift
        ):
            errors = MODULE.validate_component_model(ROOT)

        self.assertTrue(
            any("internal package dependency version" in error for error in errors)
        )

    def test_current_repository_passes(self) -> None:
        self.assertEqual([], MODULE.validate_repository(ROOT))

    def test_agent_guide_rejects_existing_project_raw_material(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text(
                "admitted positive public sources\nexisting project raw material\n",
                encoding="utf-8",
            )

            errors = MODULE.validate_agent_guide_source_boundary(root)

            self.assertTrue(any("must not admit existing project raw material" in error for error in errors))

    def test_agent_guide_rejects_mojibake(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text(
                "admitted positive public sources\n"
                "Consumer implementations are not reference material unless independently reviewed "
                "and admitted as a positive public source.\n"
                "documentation\u9225\u650f",
                encoding="utf-8",
            )

            errors = MODULE.validate_agent_guide_source_boundary(root)

            self.assertTrue(any("contains mojibake" in error for error in errors))

    def test_current_inventory_projections_are_coherent(self) -> None:
        self.assertEqual([], MODULE.validate_inventory_projection_coherence(ROOT))

    def test_current_compatibility_profiles_are_adaptive_and_exact_verified(self) -> None:
        payload = current_compatibility_profiles()

        self.assertEqual(
            "version_adaptive",
            payload["capability"]["reference_and_generation"],
        )
        self.assertEqual(
            "exact_verified_profile_only",
            payload["capability"]["support_claim_source"],
        )
        self.assertEqual("exact_profile", payload["capability"]["engine_version_binding"])
        self.assertEqual(
            {
                "route": "raw_material_regeneration",
                "result_state": "candidate",
                "support_claim_allowed": False,
            },
            payload["evidence_policy"]["unmatched_target"],
        )
        non_xr = next(
            profile
            for profile in payload["profiles"]
            if profile["id"] == "unity-6000.3-inventory-ugui-non-xr-windows-editor"
        )
        not_applicable = {"id": "not_applicable", "version": "not_applicable"}
        self.assertEqual(not_applicable, non_xr["target"]["xr_provider"])
        self.assertEqual(not_applicable, non_xr["target"]["runtime"])
        self.assertNotIn("com.lingkyn.inventory.xr.ugui", non_xr["package_versions"])
        self.assertEqual(
            {item["id"] for item in MODULE.load_json(ROOT / "package-catalog.json")["packages"]},
            {profile["install_artifact"] for profile in payload["profiles"]},
        )
        self.assertEqual(
            len(payload["profiles"]),
            len({profile["install_artifact"] for profile in payload["profiles"]}),
        )
        for profile in payload["profiles"]:
            self.assertEqual("verified", profile["state"])
            self.assertEqual("6000.3.19f1", profile["target"]["engine"]["version"])
            self.assertEqual("6000.3.19f1", profile["target"]["editor"]["version"])
            self.assertEqual(1, len(profile["evidence"]))
            evidence = profile["evidence"][0]
            self.assertEqual(profile["id"], evidence["profile_id"])
            self.assertRegex(evidence["commit_sha"], r"^[0-9a-f]{40}$")
            self.assertNotEqual("0" * 40, evidence["commit_sha"])
            self.assertEqual(set(profile["verified_claims"]), set(evidence["checks"]))
            self.assertTrue(profile["verified_claims"])
        self.assertEqual(
            [],
            MODULE.validate_compatibility_profile_payload(
                payload,
                ROOT,
                MODULE.load_json(ROOT / "package-catalog.json"),
            ),
        )

    def test_unity_external_lock_edge_accepts_resolver_upgrade_and_rejects_incompatible(self) -> None:
        self.assertTrue(MODULE.unity_external_dependency_is_satisfied("1.2.0", "1.3.4"))
        self.assertTrue(MODULE.unity_external_dependency_is_satisfied("1.2.0-pre.1", "1.2.0"))
        self.assertFalse(MODULE.unity_external_dependency_is_satisfied("1.2.0", "1.2.0-pre.1"))
        self.assertFalse(MODULE.unity_external_dependency_is_satisfied("2.0.0", "1.9.9"))
        self.assertFalse(MODULE.unity_external_dependency_is_satisfied("not-semver", "1.0.0"))

    def test_contribution_credit_never_grants_authority_or_accepts_empty_evidence(self) -> None:
        schema = ROOT / "docs" / "contributing" / "contribution-credit.schema.json"
        example = MODULE.load_json(
            ROOT / "docs" / "contributing" / "contribution-credit.example.json"
        )
        self.assertEqual(
            [],
            MODULE.validate_json_schema_instance(example, schema, "credit example"),
        )

        escalated = json.loads(json.dumps(example))
        escalated["authority"]["grants_merge_authority"] = True
        self.assertTrue(
            MODULE.validate_json_schema_instance(escalated, schema, "credit escalation")
        )

        unsupported = json.loads(json.dumps(example))
        unsupported["record_status"] = "accepted"
        unsupported["credited_at"] = "2026-07-16T12:00:00Z"
        unsupported["recorded_by"] = "@maintainer"
        self.assertTrue(
            MODULE.validate_json_schema_instance(unsupported, schema, "credit without evidence")
        )

    def test_pending_compatibility_profile_rejects_verified_overclaim(self) -> None:
        payload = current_compatibility_profiles()
        profile = payload["profiles"][0]
        profile["state"] = "pending_automated_validation"
        profile["verified_claims"] = ["editor_compile"]
        profile["evidence"] = []

        errors = MODULE.validate_compatibility_profile_payload(
            payload,
            ROOT,
            MODULE.load_json(ROOT / "package-catalog.json"),
        )

        self.assertTrue(any("unverified profile must not publish" in error for error in errors))

    def test_verified_compatibility_profile_accepts_only_exact_bound_evidence(self) -> None:
        payload = current_compatibility_profiles()
        self.assertEqual(
            [],
            MODULE.validate_compatibility_profile_payload(
                payload,
                ROOT,
                MODULE.load_json(ROOT / "package-catalog.json"),
            ),
        )

    def test_device_runtime_compatibility_requires_exact_device_lab_pass(self) -> None:
        payload = current_compatibility_profiles()
        with tempfile.TemporaryDirectory(dir=compatibility_evidence_test_root()) as directory:
            _, _, _, device_path = attach_device_runtime_receipt(payload, directory, self)
            try:
                self.assertEqual(
                    [],
                    MODULE.validate_compatibility_profile_payload(
                        payload,
                        ROOT,
                        MODULE.load_json(ROOT / "package-catalog.json"),
                    ),
                )
            finally:
                device_path.unlink(missing_ok=True)

    def test_device_runtime_rejects_host_profile_or_cross_tuple_receipt(self) -> None:
        payload = current_compatibility_profiles()
        with tempfile.TemporaryDirectory(dir=compatibility_evidence_test_root()) as directory:
            profile, receipt, receipt_path, device_path = attach_device_runtime_receipt(
                payload, directory, self
            )
            try:
                host_target = next(
                    item["target"]
                    for item in payload["profiles"]
                    if item["id"] == "unity-6000.3-inventory-xr-ugui-openxr-windows-editor"
                )
                profile["target"] = json.loads(json.dumps(host_target))
                receipt["target"] = json.loads(json.dumps(host_target))
                receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                errors = MODULE.validate_compatibility_profile_payload(
                    payload, ROOT, MODULE.load_json(ROOT / "package-catalog.json")
                )
            finally:
                device_path.unlink(missing_ok=True)
        self.assertTrue(any("Device Lab runtime tuple must match" in error for error in errors))
        self.assertTrue(any("Device Lab device tuple must match" in error for error in errors))

    def test_device_runtime_rejects_device_receipt_that_does_not_pass_full_validator(self) -> None:
        payload = current_compatibility_profiles()
        with tempfile.TemporaryDirectory(dir=compatibility_evidence_test_root()) as directory:
            profile, receipt, receipt_path, device_path = attach_device_runtime_receipt(
                payload, directory, self
            )
            try:
                device_receipt = json.loads(device_path.read_text(encoding="utf-8"))
                required = next(
                    check
                    for check in device_receipt["checks"]
                    if check["id"] == "artifact-install"
                )
                required.update(
                    {"status": "not_tested", "observation": "", "evidence_refs": []}
                )
                device_path.write_text(json.dumps(device_receipt), encoding="utf-8")
                digest = hashlib.sha256(device_path.read_bytes()).hexdigest()
                receipt["device_lab_receipt"]["sha256"] = digest
                receipt["checks"][0]["evidence_refs"][0]["sha256"] = digest
                receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                profile["evidence"][0]["checks"] = ["device_runtime"]
                errors = MODULE.validate_compatibility_profile_payload(
                    payload, ROOT, MODULE.load_json(ROOT / "package-catalog.json")
                )
            finally:
                device_path.unlink(missing_ok=True)
        self.assertTrue(any("required check cannot remain not_tested" in error for error in errors))

    def test_device_runtime_rejects_receipt_outside_canonical_device_lab_route(self) -> None:
        payload = current_compatibility_profiles()
        with tempfile.TemporaryDirectory(dir=compatibility_evidence_test_root()) as directory:
            profile, receipt, receipt_path, device_path = attach_device_runtime_receipt(
                payload, directory, self
            )
            copied_path = Path(directory) / "copied-device-receipt.json"
            copied_path.write_bytes(device_path.read_bytes())
            try:
                digest = hashlib.sha256(copied_path.read_bytes()).hexdigest()
                receipt["device_lab_receipt"] = {
                    "path": copied_path.relative_to(ROOT).as_posix(),
                    "sha256": digest,
                }
                receipt["checks"][0]["evidence_refs"][0].update(
                    {"ref": copied_path.relative_to(ROOT).as_posix(), "sha256": digest}
                )
                receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                errors = MODULE.validate_compatibility_profile_payload(
                    payload, ROOT, MODULE.load_json(ROOT / "package-catalog.json")
                )
            finally:
                device_path.unlink(missing_ok=True)
        self.assertTrue(any("docs/device-lab/receipts/*.json" in error for error in errors))

    def test_historical_verified_profile_keeps_its_exact_manifest_versions(self) -> None:
        payload = current_compatibility_profiles()
        current = next(
            item
            for item in payload["profiles"]
            if item["id"] == "unity-6000.3-inventory-ugui-non-xr-windows-editor"
        )
        historical = json.loads(json.dumps(current))
        historical["id"] = "unity-6000.3-inventory-ugui-0.1.0-historical"
        fixture_commit = public_fixture_commit()
        catalog_paths = {
            item["id"]: item["path"]
            for item in MODULE.load_json(ROOT / "package-catalog.json")["packages"]
        }
        for package_id in historical["package_versions"]:
            manifest = json.loads(
                subprocess.check_output(
                    [
                        "git",
                        "show",
                        f"{fixture_commit}:{catalog_paths[package_id]}/package.json",
                    ],
                    cwd=ROOT,
                    text=True,
                )
            )
            historical["package_versions"][package_id] = manifest["version"]
        payload["profiles"].append(historical)
        with tempfile.TemporaryDirectory(dir=compatibility_evidence_test_root()) as directory:
            attach_compatibility_receipt(payload, directory, profile_id=historical["id"])
            self.assertEqual(
                [],
                MODULE.validate_compatibility_profile_payload(
                    payload,
                    ROOT,
                    MODULE.load_json(ROOT / "package-catalog.json"),
                ),
            )

    def test_compatibility_receipt_rejects_pseudo_revision_and_hashes(self) -> None:
        payload = current_compatibility_profiles()
        with tempfile.TemporaryDirectory(dir=compatibility_evidence_test_root()) as directory:
            profile, receipt, receipt_path = attach_compatibility_receipt(payload, directory)
            profile["evidence"][0]["commit_sha"] = "0" * 40
            profile["evidence"][0]["lock_sha256"] = "0" * 64
            receipt["commit_sha"] = "0" * 40
            receipt["lock"]["sha256"] = "0" * 64
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            errors = MODULE.validate_compatibility_profile_payload(
                payload, ROOT, MODULE.load_json(ROOT / "package-catalog.json")
            )
        self.assertTrue(any("non-zero full commit SHA" in error for error in errors))
        self.assertTrue(any("non-zero lock_sha256" in error for error in errors))

    def test_compatibility_receipt_rejects_nonexistent_commit(self) -> None:
        payload = current_compatibility_profiles()
        with tempfile.TemporaryDirectory(dir=compatibility_evidence_test_root()) as directory:
            profile, receipt, receipt_path = attach_compatibility_receipt(payload, directory)
            profile["evidence"][0]["commit_sha"] = "f" * 40
            receipt["commit_sha"] = "f" * 40
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            errors = MODULE.validate_compatibility_profile_payload(
                payload, ROOT, MODULE.load_json(ROOT / "package-catalog.json")
            )
        self.assertTrue(any("must resolve and be reachable" in error for error in errors))

    def test_compatibility_receipt_rejects_local_only_commit_with_public_tree(self) -> None:
        public_commit = public_fixture_commit()
        tree = subprocess.check_output(
            ["git", "rev-parse", f"{public_commit}^{{tree}}"], cwd=ROOT, text=True
        ).strip()
        local_only = subprocess.check_output(
            [
                "git",
                "-c",
                "user.name=XR Foundry Contract Test",
                "-c",
                "user.email=xr-foundry-contract-test@example.invalid",
                "commit-tree",
                tree,
            ],
            cwd=ROOT,
            input="local-only evidence object\n",
            text=True,
        ).strip()
        self.assertFalse(MODULE.commit_is_public_origin_reachable(ROOT, local_only))
        payload = current_compatibility_profiles()
        with tempfile.TemporaryDirectory(dir=compatibility_evidence_test_root()) as directory:
            profile, receipt, receipt_path = attach_compatibility_receipt(payload, directory)
            profile["evidence"][0]["commit_sha"] = local_only
            receipt["commit_sha"] = local_only
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            errors = MODULE.validate_compatibility_profile_payload(
                payload, ROOT, MODULE.load_json(ROOT / "package-catalog.json")
            )
        self.assertTrue(any("fetched public origin ref" in error for error in errors))

    def test_compatibility_receipt_rejects_missing_files_and_wrong_real_hash(self) -> None:
        payload = current_compatibility_profiles()
        with tempfile.TemporaryDirectory(dir=compatibility_evidence_test_root()) as directory:
            _, receipt, receipt_path = attach_compatibility_receipt(payload, directory)
            receipt["manifest"]["path"] = (
                "docs/validation/evidence/nonexistent-consumer-manifest.json"
            )
            receipt["checks"][0]["evidence_refs"][0]["sha256"] = "e" * 64
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            errors = MODULE.validate_compatibility_profile_payload(
                payload, ROOT, MODULE.load_json(ROOT / "package-catalog.json")
            )
        self.assertTrue(any("repository evidence file does not exist" in error for error in errors))
        self.assertTrue(any("SHA-256 does not match repository file" in error for error in errors))

    def test_compatibility_receipt_rejects_simplified_or_drifted_unity_lock(self) -> None:
        mutations = {
            "simplified": lambda lock, root: lock["dependencies"].__setitem__(root, "0.1.0"),
            "wrong_source": lambda lock, root: lock["dependencies"][root].__setitem__(
                "source", "registry"
            ),
            "wrong_hash": lambda lock, root: lock["dependencies"][root].__setitem__(
                "hash", "f" * 40
            ),
            "wrong_depth": lambda lock, root: lock["dependencies"][root].__setitem__(
                "depth", 7
            ),
            "wrong_path": lambda lock, root: lock["dependencies"][root].__setitem__(
                "version", lock["dependencies"][root]["version"].replace(
                    "com.lingkyn.inventory.ugui", "com.lingkyn.inventory.core"
                )
            ),
            "wrong_transitive": lambda lock, root: lock["dependencies"][root][
                "dependencies"
            ].__setitem__("com.unity.fake-transitive", "9.9.9"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                payload = current_compatibility_profiles()
                with tempfile.TemporaryDirectory(
                    dir=compatibility_evidence_test_root()
                ) as directory:
                    profile, receipt, receipt_path = attach_compatibility_receipt(
                        payload, directory
                    )
                    lock_path = ROOT / receipt["lock"]["path"]
                    lock = json.loads(lock_path.read_text(encoding="utf-8"))
                    mutate(lock, profile["install_artifact"])
                    lock_path.write_text(json.dumps(lock), encoding="utf-8")
                    digest = hashlib.sha256(lock_path.read_bytes()).hexdigest()
                    receipt["lock"]["sha256"] = digest
                    profile["evidence"][0]["lock_sha256"] = digest
                    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                    errors = MODULE.validate_compatibility_profile_payload(
                        payload, ROOT, MODULE.load_json(ROOT / "package-catalog.json")
                    )
                self.assertTrue(
                    any(
                        marker in error
                        for error in errors
                        for marker in (
                            "lock dependency entry must be an object",
                            "custom lock package source must be git",
                            "custom lock package hash must equal",
                            "custom lock selector must bind canonical path",
                            "custom lock dependency edges drift",
                            "direct manifest dependency must have depth=0",
                            "depth must equal the shortest manifest path",
                        )
                    )
                )

    def test_compatibility_receipt_rejects_exact_tuple_mismatches(self) -> None:
        mutations = {
            "build_target": lambda receipt: receipt["target"].__setitem__(
                "build_target", "Android"
            ),
            "provider": lambda receipt: receipt["target"]["xr_provider"].update(
                {"id": "com.unity.xr.openxr", "version": "1.16.0"}
            ),
            "input": lambda receipt: receipt["target"].__setitem__(
                "input_routes", ["xri-ray"]
            ),
            "renderer": lambda receipt: receipt["target"]["renderer"].update(
                {"id": "com.unity.modules.uielements", "version": "1.0.0"}
            ),
            "scripting_backend": lambda receipt: receipt["target"].__setitem__(
                "scripting_backend", "IL2CPP"
            ),
            "architecture": lambda receipt: receipt["target"].__setitem__(
                "architecture", "ARM64"
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                payload = current_compatibility_profiles()
                with tempfile.TemporaryDirectory(
                    dir=compatibility_evidence_test_root()
                ) as directory:
                    _, receipt, receipt_path = attach_compatibility_receipt(payload, directory)
                    mutate(receipt)
                    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                    errors = MODULE.validate_compatibility_profile_payload(
                        payload, ROOT, MODULE.load_json(ROOT / "package-catalog.json")
                    )
                self.assertTrue(any("receipt target must exactly match" in error for error in errors))

    def test_compatibility_receipt_rejects_package_dependency_and_lock_mismatch(self) -> None:
        payload = current_compatibility_profiles()
        with tempfile.TemporaryDirectory(dir=compatibility_evidence_test_root()) as directory:
            profile, receipt, receipt_path = attach_compatibility_receipt(payload, directory)
            receipt["package_versions"]["com.lingkyn.inventory.core"] = "9.9.9"
            receipt["resolved_dependencies"]["com.unity.ugui"] = "9.9.9"
            receipt["lock"]["sha256"] = "e" * 64
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            errors = MODULE.validate_compatibility_profile_payload(
                payload, ROOT, MODULE.load_json(ROOT / "package-catalog.json")
            )
        self.assertTrue(any("receipt package_versions must exactly match" in error for error in errors))
        self.assertTrue(any("receipt resolved_dependencies must exactly match" in error for error in errors))
        self.assertTrue(any("receipt lock hash must match" in error for error in errors))

    def test_compatibility_receipt_rejects_check_mismatch(self) -> None:
        payload = current_compatibility_profiles()
        with tempfile.TemporaryDirectory(dir=compatibility_evidence_test_root()) as directory:
            profile, receipt, receipt_path = attach_compatibility_receipt(payload, directory)
            receipt["checks"][0]["status"] = "fail"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            errors = MODULE.validate_compatibility_profile_payload(
                payload, ROOT, MODULE.load_json(ROOT / "package-catalog.json")
            )
        self.assertTrue(any("checks must exactly equal passed receipt checks" in error for error in errors))
        self.assertTrue(any("lacks a passed receipt check" in error for error in errors))

    def test_automated_compatibility_rejects_text_compile_and_fake_nunit(self) -> None:
        payload = current_compatibility_profiles()
        with tempfile.TemporaryDirectory(dir=compatibility_evidence_test_root()) as directory:
            _, receipt, receipt_path = attach_compatibility_receipt(payload, directory)
            compile_ref = receipt["checks"][0]["evidence_refs"][0]
            compile_path = ROOT / compile_ref["ref"]
            compile_path.write_text("compile passed", encoding="utf-8")
            compile_ref["sha256"] = hashlib.sha256(compile_path.read_bytes()).hexdigest()
            nunit_ref = receipt["checks"][1]["evidence_refs"][0]
            nunit_path = ROOT / nunit_ref["ref"]
            nunit_path.write_text("all tests passed", encoding="utf-8")
            nunit_ref["sha256"] = hashlib.sha256(nunit_path.read_bytes()).hexdigest()
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            errors = MODULE.validate_compatibility_profile_payload(
                payload, ROOT, MODULE.load_json(ROOT / "package-catalog.json")
            )
        self.assertTrue(any("compile result must be structured JSON" in error for error in errors))
        self.assertTrue(any("parseable NUnit XML" in error for error in errors))

    def test_nunit_result_rejects_wrong_mode_missing_and_unrelated_assemblies(self) -> None:
        cases = {
            "wrong-mode": "platform property must equal EditMode",
            "missing-required": "omits commit-required EditMode assemblies",
            "unrelated-assembly": "manifest-testables-derived EditMode assemblies",
        }
        for mutation, expected_error in cases.items():
            with self.subTest(mutation=mutation):
                payload = current_compatibility_profiles()
                with tempfile.TemporaryDirectory(
                    dir=compatibility_evidence_test_root()
                ) as directory:
                    _, receipt, receipt_path = attach_compatibility_receipt(
                        payload, directory
                    )
                    nunit_ref = receipt["checks"][1]["evidence_refs"][0]
                    nunit_path = ROOT / nunit_ref["ref"]
                    tree = ET.parse(nunit_path)
                    test_run = tree.getroot()
                    project_suite = next(
                        item
                        for item in test_run
                        if item.tag == "test-suite"
                        and item.attrib.get("type") == "TestSuite"
                    )
                    assembly_suites = [
                        item
                        for item in project_suite
                        if item.tag == "test-suite"
                        and item.attrib.get("type") == "Assembly"
                    ]
                    if mutation == "wrong-mode":
                        platform = next(
                            item
                            for properties in project_suite
                            if properties.tag == "properties"
                            for item in properties
                            if item.attrib.get("name") == "platform"
                        )
                        platform.attrib["value"] = "PlayMode"
                    elif mutation == "missing-required":
                        project_suite.remove(assembly_suites[0])
                    else:
                        assembly_suites[0].attrib["name"] = "Unrelated.Tests.dll"
                    tree.write(nunit_path, encoding="utf-8", xml_declaration=True)
                    nunit_ref["sha256"] = hashlib.sha256(
                        nunit_path.read_bytes()
                    ).hexdigest()
                    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                    errors = MODULE.validate_compatibility_profile_payload(
                        payload, ROOT, MODULE.load_json(ROOT / "package-catalog.json")
                    )
                self.assertTrue(
                    any(expected_error in error for error in errors), errors
                )

    def test_structured_compile_result_must_cross_bind_and_pass(self) -> None:
        payload = current_compatibility_profiles()
        with tempfile.TemporaryDirectory(dir=compatibility_evidence_test_root()) as directory:
            _, receipt, receipt_path = attach_compatibility_receipt(payload, directory)
            compile_ref = receipt["checks"][0]["evidence_refs"][0]
            compile_path = ROOT / compile_ref["ref"]
            compile_result = json.loads(compile_path.read_text(encoding="utf-8"))
            compile_result["profile_id"] = "another-profile"
            compile_result["result"] = "fail"
            compile_result["error_count"] = 1
            compile_path.write_text(json.dumps(compile_result), encoding="utf-8")
            compile_ref["sha256"] = hashlib.sha256(compile_path.read_bytes()).hexdigest()
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            errors = MODULE.validate_compatibility_profile_payload(
                payload, ROOT, MODULE.load_json(ROOT / "package-catalog.json")
            )
        self.assertTrue(any("profile_id must match the evidence tuple" in error for error in errors))
        self.assertTrue(any("pass with error_count=0" in error for error in errors))

    def test_compatibility_profiles_reject_vague_target_and_unsupported_match(self) -> None:
        payload = current_compatibility_profiles()
        payload["profiles"][0]["target"]["engine"]["version"] = "latest"
        payload["evidence_policy"]["unmatched_target"]["support_claim_allowed"] = True

        errors = MODULE.validate_compatibility_profile_payload(
            payload,
            ROOT,
            MODULE.load_json(ROOT / "package-catalog.json"),
        )

        self.assertTrue(any("concrete profile value" in error for error in errors))
        self.assertTrue(any("unsupported candidates" in error for error in errors))

    def test_compatibility_profile_rejects_package_version_drift(self) -> None:
        payload = current_compatibility_profiles()
        profile = next(
            item
            for item in payload["profiles"]
            if item["install_artifact"] == "com.lingkyn.inventory.core"
        )
        profile["package_versions"]["com.lingkyn.inventory.core"] = "9.9.9"

        errors = MODULE.validate_compatibility_profile_payload(
            payload,
            ROOT,
            MODULE.load_json(ROOT / "package-catalog.json"),
        )

        self.assertTrue(any("match catalog and installable manifest" in error for error in errors))

    def test_installable_manifest_rejects_dependency_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package_root = root / "packages" / "unity" / "com.lingkyn.example"
            package_root.mkdir(parents=True)
            (package_root / "package.json").write_text(
                json.dumps(
                    {
                        "name": "com.lingkyn.example",
                        "version": "0.1.0",
                        "unity": "6000.3",
                        "dependencies": {"com.unity.example": ">=1.0.0"},
                    }
                ),
                encoding="utf-8",
            )
            catalog = {
                "packages": [
                    {
                        "id": "com.lingkyn.example",
                        "path": "packages/unity/com.lingkyn.example",
                        "version": "0.1.0",
                    }
                ]
            }

            errors = MODULE.validate_concrete_package_manifests(root, catalog)

            self.assertTrue(any("dependency com.unity.example" in error for error in errors))

    def test_asmdef_filename_stem_must_equal_declared_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package_root = Path(directory)
            asmdef = package_root / "LegacyName.asmdef"
            asmdef.write_text(
                json.dumps({"name": "Lingkyn.Inventory.Runtime"}), encoding="utf-8"
            )
            asmdef.with_name(asmdef.name + ".meta").write_text(
                "fileFormatVersion: 2\n", encoding="utf-8"
            )

            errors = MODULE.validate_asmdef_identity(package_root)

        self.assertTrue(any("filename stem must equal declared name" in error for error in errors))

    def test_installable_reference_requires_raw_material_use_mode(self) -> None:
        catalog = MODULE.load_json(ROOT / "reference-catalog.json")
        package_artifact = next(
            item for item in catalog["artifacts"] if item.get("package_id")
        )
        package_artifact["use_modes"].remove("raw_material")

        errors = MODULE.validate_reference_package_use_modes(catalog)

        self.assertTrue(any("must include raw_material" in error for error in errors))

    def test_reference_package_coherence_accepts_live_catalogs(self) -> None:
        catalog = MODULE.load_json(ROOT / "package-catalog.json")
        reference = MODULE.load_json(ROOT / "reference-catalog.json")
        self.assertEqual([], MODULE.validate_reference_package_coherence(catalog, reference))

    def test_reference_package_coherence_rejects_maturity_drift_for_every_package(self) -> None:
        catalog = MODULE.load_json(ROOT / "package-catalog.json")
        reference = MODULE.load_json(ROOT / "reference-catalog.json")
        for index, artifact in enumerate(reference["artifacts"]):
            if not artifact.get("package_id"):
                continue
            different_maturity = next(
                state for state in catalog["maturity_states"] if state != artifact["maturity"]
            )
            for maturity in (different_maturity, None):
                with self.subTest(package_id=artifact["package_id"], maturity=maturity):
                    mutated = copy.deepcopy(reference)
                    if maturity is None:
                        mutated["artifacts"][index].pop("maturity")
                    else:
                        mutated["artifacts"][index]["maturity"] = maturity
                    errors = MODULE.validate_reference_package_coherence(catalog, mutated)
                    self.assertEqual(1, len(errors), errors)
                    self.assertIn("maturity must agree", errors[0])
                    self.assertIn(artifact["package_id"], errors[0])

    def test_repository_rejects_non_inventory_reference_maturity_drift(self) -> None:
        load_json = MODULE.load_json
        reference_path = ROOT / "reference-catalog.json"
        reference = load_json(reference_path)
        artifact = next(
            item for item in reference["artifacts"]
            if item.get("package_id") == "com.lingkyn.settings.core"
        )
        catalog = load_json(ROOT / "package-catalog.json")
        artifact["maturity"] = next(
            state for state in catalog["maturity_states"] if state != artifact["maturity"]
        )

        def mutated_load_json(path):
            return reference if path == reference_path else load_json(path)

        with mock.patch.object(MODULE, "load_json", side_effect=mutated_load_json):
            errors = MODULE.validate_repository(ROOT)
        self.assertTrue(any(
            "maturity must agree" in error and "com.lingkyn.settings.core" in error
            for error in errors
        ), errors)

    def test_reference_package_coherence_rejects_unknown_package_id(self) -> None:
        catalog = MODULE.load_json(ROOT / "package-catalog.json")
        reference = MODULE.load_json(ROOT / "reference-catalog.json")
        artifact = next(item for item in reference["artifacts"] if item.get("package_id"))
        artifact["package_id"] = "com.lingkyn.unknown"
        errors = MODULE.validate_reference_package_coherence(catalog, reference)
        self.assertEqual(1, len(errors), errors)
        self.assertIn("reference package_id is not in package catalog", errors[0])

    def test_reference_package_coherence_binds_each_path_to_its_package_id(self) -> None:
        catalog = MODULE.load_json(ROOT / "package-catalog.json")
        reference = MODULE.load_json(ROOT / "reference-catalog.json")
        artifacts = [item for item in reference["artifacts"] if item.get("package_id")]
        artifacts[0]["path"], artifacts[1]["path"] = artifacts[1]["path"], artifacts[0]["path"]
        errors = MODULE.validate_reference_package_coherence(catalog, reference)
        self.assertEqual(2, len(errors), errors)
        self.assertTrue(all("reference path must match package catalog" in error for error in errors))

    def test_reference_package_coherence_errors_have_specific_hints(self) -> None:
        catalog = {"packages": [{"id": "com.lingkyn.example", "path": "example", "maturity": "incubating"}]}
        reference = {"artifacts": [
            {"package_id": "com.lingkyn.unknown"},
            {"package_id": "com.lingkyn.example", "path": "wrong", "maturity": "candidate"},
        ]}
        errors = MODULE.validate_reference_package_coherence(catalog, reference)
        self.assertEqual(3, len(errors), errors)
        for entry in MODULE.explain_errors(errors):
            self.assertNotIn("No specific hint", entry["hint"], entry)
            self.assertIn("catalog.json", entry["hint"], entry)

    def test_reference_package_coherence_ignores_non_package_artifacts(self) -> None:
        reference = {"artifacts": [{"id": "standard", "maturity": "candidate"}]}
        self.assertEqual([], MODULE.validate_reference_package_coherence({"packages": []}, reference))

    def test_reference_catalog_rejects_nonexistent_evidence_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            errors = MODULE.validate_reference_evidence_paths(
                root,
                {
                    "artifacts": [
                        {"id": "example", "evidence": ["missing/evidence.md"]}
                    ]
                },
            )
            self.assertTrue(any("does not exist" in error for error in errors))

    def test_repository_layout_rejects_catalog_path_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layout_root = root / "docs" / "architecture"
            package_root = (
                root / "packages" / "unity" / "systems" / "inventory"
                / "com.lingkyn.inventory.core"
            )
            layout_root.mkdir(parents=True)
            package_root.mkdir(parents=True)
            (package_root / "package.json").write_text(
                json.dumps({"name": "com.lingkyn.inventory.core"}), encoding="utf-8"
            )
            (layout_root / "repository-layout.v1.json").write_text(
                json.dumps(
                    {
                        "schema": "xr-foundry.repository_layout.v1",
                        "status": "accepted_initialization_architecture",
                        "package_root": "packages",
                        "engine_roots": {"unity": "packages/unity"},
                        "collections": [
                            {
                                "id": "unity-system-inventory",
                                "path": "packages/unity/systems/inventory",
                                "packages": ["com.lingkyn.inventory.core"],
                            }
                        ],
                        "invariants": {
                            "leaf_directory_equals_package_id": True,
                            "landing_page_groups_package_families": True,
                            "machine_catalog_keeps_package_entries": True,
                            "consumer_asset_path_uses_package_id": True,
                            "git_url_path_precedes_revision": True,
                            "full_commit_sha_required": True,
                            "old_path_compatibility_layers_allowed": False,
                            "empty_future_engine_roots_allowed": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            catalog = {
                "packages": [
                    {
                        "id": "com.lingkyn.inventory.core",
                        "path": "packages/unity/foundations/com.lingkyn.inventory.core",
                    }
                ]
            }
            errors = MODULE.validate_repository_layout(root, catalog)
            self.assertTrue(any("layout path mismatch" in error for error in errors))

    def test_repository_layout_rejects_old_root_compatibility_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layout_root = root / "docs" / "architecture"
            package_root = (
                root / "packages" / "unity" / "systems" / "inventory"
                / "com.lingkyn.inventory.core"
            )
            old_root = root / "com.lingkyn.inventory.core"
            layout_root.mkdir(parents=True)
            package_root.mkdir(parents=True)
            old_root.mkdir()
            manifest = json.dumps({"name": "com.lingkyn.inventory.core"})
            (package_root / "package.json").write_text(manifest, encoding="utf-8")
            (old_root / "package.json").write_text(manifest, encoding="utf-8")
            (layout_root / "repository-layout.v1.json").write_text(
                (ROOT / "docs" / "architecture" / "repository-layout.v1.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            catalog = {
                "packages": [
                    {
                        "id": package_id,
                        "path": path,
                    }
                    for package_id, path in MODULE.package_paths_by_id(
                        MODULE.load_json(ROOT / "package-catalog.json")
                    ).items()
                ]
            }
            errors = MODULE.validate_repository_layout(root, catalog)
            self.assertTrue(any("Old root package paths are not allowed" in error for error in errors))

    def test_bug_template_rejects_package_catalog_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template_root = root / ".github" / "ISSUE_TEMPLATE"
            template_root.mkdir(parents=True)
            (template_root / "bug.yml").write_text(
                "options:\n  - com.lingkyn.inventory.core\n  - Repository tooling\n",
                encoding="utf-8",
            )
            catalog = {
                "packages": [
                    {
                        "id": "com.lingkyn.inventory.core",
                        "path": "packages/unity/systems/inventory/com.lingkyn.inventory.core",
                    },
                    {
                        "id": "com.lingkyn.inventory.ugui",
                        "path": "packages/unity/systems/inventory/com.lingkyn.inventory.ugui",
                    },
                ]
            }
            errors = MODULE.validate_bug_template_package_options(root, catalog)
            self.assertTrue(any("differ from the package catalog" in error for error in errors))

    def test_inventory_projection_rejects_dependency_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            standard_root = root / "docs" / "standards" / "inventory"
            package_root = (
                root
                / "packages"
                / "unity"
                / "systems"
                / "inventory"
                / "com.lingkyn.inventory.presentation"
            )
            standard_root.mkdir(parents=True)
            package_root.mkdir(parents=True)
            (root / "README.md").write_text("Inventory family", encoding="utf-8")
            (root / "ROADMAP.md").write_text(
                "| `com.lingkyn.inventory.presentation` | `0.1.0` | `incubating` | `local_clean_consumer` |\n",
                encoding="utf-8",
            )
            (standard_root / "README.md").write_text("Inventory family", encoding="utf-8")
            (standard_root / "inventory-standard.json").write_text(
                json.dumps(
                    {
                        "package_family": [
                            {
                                "id": "com.lingkyn.inventory.presentation",
                                "required_dependencies": [],
                                "implementation_status": "implemented_incubating",
                                "earliest_failed_gate": "local_clean_consumer",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (package_root / "package.json").write_text(
                json.dumps(
                    {
                        "name": "com.lingkyn.inventory.presentation",
                        "dependencies": {"com.lingkyn.inventory.core": "0.1.0"},
                    }
                ),
                encoding="utf-8",
            )
            (root / "package-catalog.json").write_text(
                json.dumps(
                    {
                        "packages": [
                            {
                                "id": "com.lingkyn.inventory.presentation",
                                "path": "packages/unity/systems/inventory/com.lingkyn.inventory.presentation",
                                "version": "0.1.0",
                                "maturity": "incubating",
                                "promotion": {
                                    "candidate_status": "blocked",
                                    "earliest_failed_gate": "local_clean_consumer",
                                    "satisfied": ["renderer_neutral_api_extracted"],
                                    "pending": ["local_clean_consumer"],
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "reference-catalog.json").write_text(
                json.dumps(
                    {
                        "artifacts": [
                            {"id": "unity-inventory-presentation", "maturity": "incubating"},
                            {"id": "inventory-package-family-standard", "maturity": "incubating"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            errors = MODULE.validate_inventory_projection_coherence(root)
            self.assertTrue(any("dependency projection drift" in error for error in errors))

    def test_inventory_projection_rejects_stale_unadmitted_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            standard_root = root / "docs" / "standards" / "inventory"
            standard_root.mkdir(parents=True)
            (root / "ROADMAP.md").write_text(
                "Implementation remains unadmitted until later.", encoding="utf-8"
            )
            (standard_root / "README.md").write_text("Core status", encoding="utf-8")
            (standard_root / "inventory-standard.json").write_text(
                json.dumps(
                    {
                        "core_implementation_admitted": True,
                        "package_family": [
                            {
                                "id": "com.lingkyn.inventory.core",
                                "implementation_status": "implemented_incubating",
                                "earliest_failed_gate": "persistence_round_trip_and_migration",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / "package-catalog.json").write_text(
                json.dumps(
                    {
                        "packages": [
                            {
                                "id": "com.lingkyn.inventory.core",
                                "maturity": "incubating",
                                "promotion": {
                                    "candidate_status": "blocked",
                                    "earliest_failed_gate": "persistence_round_trip_and_migration",
                                    "satisfied": ["architecture_gate"],
                                    "pending": ["persistence_round_trip_and_migration"],
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "reference-catalog.json").write_text(
                json.dumps(
                    {
                        "artifacts": [
                            {
                                "id": "unity-inventory-core",
                                "maturity": "incubating",
                            },
                            {
                                "id": "inventory-package-family-standard",
                                "maturity": "incubating",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            errors = MODULE.validate_inventory_projection_coherence(root)
            self.assertTrue(any("stale Inventory implementation claim" in error for error in errors))

    def test_passed_candidate_rejects_pending_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            standard_root = root / "docs" / "standards" / "inventory"
            standard_root.mkdir(parents=True)
            (root / "ROADMAP.md").write_text("Candidate Core", encoding="utf-8")
            (standard_root / "README.md").write_text("Candidate Core", encoding="utf-8")
            (standard_root / "inventory-standard.json").write_text(
                json.dumps(
                    {
                        "core_implementation_admitted": True,
                        "package_family": [
                            {
                                "id": "com.lingkyn.inventory.core",
                                "implementation_status": "implemented_candidate",
                                "earliest_failed_gate": "none",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / "package-catalog.json").write_text(
                json.dumps(
                    {
                        "packages": [
                            {
                                "id": "com.lingkyn.inventory.core",
                                "maturity": "candidate",
                                "promotion": {
                                    "candidate_status": "passed",
                                    "earliest_failed_gate": "none",
                                    "satisfied": ["candidate_gate"],
                                    "pending": ["should_not_remain"],
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "reference-catalog.json").write_text(
                json.dumps(
                    {
                        "artifacts": [
                            {"id": "unity-inventory-core", "maturity": "candidate"},
                            {"id": "inventory-package-family-standard", "maturity": "incubating"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            errors = MODULE.validate_inventory_projection_coherence(root)
            self.assertTrue(any("no failed or pending gate" in error for error in errors))

    def test_inventory_projection_rejects_stale_ugui_roadmap_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            standard_root = root / "docs" / "standards" / "inventory"
            standard_root.mkdir(parents=True)
            (root / "ROADMAP.md").write_text(
                "| `com.lingkyn.inventory.ugui` | `0.1.0` | `candidate` | `none` |\n",
                encoding="utf-8",
            )
            (standard_root / "README.md").write_text("UGUI correction", encoding="utf-8")
            (standard_root / "inventory-standard.json").write_text(
                json.dumps(
                    {
                        "package_family": [
                            {
                                "id": "com.lingkyn.inventory.ugui",
                                "implementation_status": "implemented_incubating",
                                "earliest_failed_gate": "immutable_git_url_functional_consumer",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "package-catalog.json").write_text(
                json.dumps(
                    {
                        "packages": [
                            {
                                "id": "com.lingkyn.inventory.ugui",
                                "version": "0.1.0",
                                "maturity": "incubating",
                                "promotion": {
                                    "candidate_status": "blocked",
                                    "earliest_failed_gate": "immutable_git_url_functional_consumer",
                                    "satisfied": ["wired_shipped_prefabs_local"],
                                    "pending": ["immutable_git_url_functional_consumer"],
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "reference-catalog.json").write_text(
                json.dumps(
                    {
                        "artifacts": [
                            {"id": "unity-inventory-ugui", "maturity": "incubating"},
                            {"id": "inventory-package-family-standard", "maturity": "incubating"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            errors = MODULE.validate_inventory_projection_coherence(root)
            self.assertTrue(any("stale or missing projection row" in error for error in errors))

    def test_inventory_projection_rejects_stale_xr_not_implemented_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            standard_root = root / "docs" / "standards" / "inventory"
            standard_root.mkdir(parents=True)
            (root / "README.md").write_text("XR adapter is incubating.", encoding="utf-8")
            (root / "ROADMAP.md").write_text(
                "XR is still not implemented.\n"
                "| `com.lingkyn.inventory.xr.ugui` | `0.1.0` | `incubating` | "
                "`immutable_git_url_clean_consumer` |\n",
                encoding="utf-8",
            )
            (standard_root / "README.md").write_text("XR adapter is incubating.", encoding="utf-8")
            (standard_root / "inventory-standard.json").write_text(
                json.dumps(
                    {
                        "package_family": [
                            {
                                "id": "com.lingkyn.inventory.xr.ugui",
                                "implementation_status": "implemented_incubating",
                                "earliest_failed_gate": "immutable_git_url_clean_consumer",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "package-catalog.json").write_text(
                json.dumps(
                    {
                        "packages": [
                            {
                                "id": "com.lingkyn.inventory.xr.ugui",
                                "version": "0.1.0",
                                "maturity": "incubating",
                                "promotion": {
                                    "candidate_status": "blocked",
                                    "earliest_failed_gate": "immutable_git_url_clean_consumer",
                                    "satisfied": ["xr_adapter_tests"],
                                    "pending": ["immutable_git_url_clean_consumer"],
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "reference-catalog.json").write_text(
                json.dumps(
                    {
                        "artifacts": [
                            {"id": "unity-inventory-xr-ugui", "maturity": "incubating"},
                            {"id": "inventory-package-family-standard", "maturity": "incubating"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            errors = MODULE.validate_inventory_projection_coherence(root)
            self.assertTrue(any("stale Inventory XR implementation claim" in error for error in errors))

    def test_consumer_project_marker_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = "VR" + "soundscape"
            (root / "README.md").write_text(marker, encoding="utf-8")
            errors = MODULE.scan_text_safety(root)
            self.assertTrue(any("non-public marker" in error for error in errors))

    def test_internal_system_marker_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = "AI" + "OS"
            (root / "README.md").write_text(marker, encoding="utf-8")
            errors = MODULE.scan_text_safety(root)
            self.assertTrue(any("non-public marker" in error for error in errors))

    def test_ignored_untracked_local_projection_is_not_a_publication_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(
                ["git", "init", "--quiet"], cwd=root, check=True, capture_output=True
            )
            (root / ".gitignore").write_text(".local-control/\n", encoding="utf-8")
            local_projection = root / ".local-control" / "runtime.json"
            local_projection.parent.mkdir()
            local_projection.write_text("AI" + "OS", encoding="utf-8")

            errors = MODULE.scan_text_safety(root)

            self.assertFalse(any("runtime.json" in error for error in errors))

    def test_force_added_ignored_marker_remains_a_publication_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(
                ["git", "init", "--quiet"], cwd=root, check=True, capture_output=True
            )
            (root / ".gitignore").write_text(".local-control/\n", encoding="utf-8")
            tracked_projection = root / ".local-control" / "tracked.md"
            tracked_projection.parent.mkdir()
            tracked_projection.write_text("AI" + "OS", encoding="utf-8")
            subprocess.run(
                ["git", "add", "--force", ".local-control/tracked.md"],
                cwd=root,
                check=True,
                capture_output=True,
            )

            errors = MODULE.scan_text_safety(root)

            self.assertTrue(
                any("tracked.md" in error and "non-public marker" in error for error in errors)
            )

    def test_project_profile_allows_only_declared_control_markers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control_markers = [
                "AI" + "OS",
                "agent" + "-os",
                "skill" + "-system",
                "_steward" + "ship",
                "work " + "packet",
                "." + "ai" + "os",
            ]
            (root / "PROJECT_PROFILE.json").write_text(
                json.dumps({"control_markers": control_markers}), encoding="utf-8"
            )

            self.assertEqual([], MODULE.scan_text_safety(root))

    def test_project_profile_still_rejects_product_secret_and_machine_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = "\n".join(
                [
                    "VR" + "soundscape",
                    "api" + "_key = 'not-a-real-secret'",
                    "C:" + "\\Users\\example\\workspace",
                ]
            )
            (root / "PROJECT_PROFILE.json").write_text(content, encoding="utf-8")

            errors = MODULE.scan_text_safety(root)

            self.assertTrue(any("non-public marker" in error for error in errors))
            self.assertTrue(any("possible credential" in error for error in errors))
            self.assertTrue(any("machine-local Windows path" in error for error in errors))

    def test_privacy_scan_covers_every_decodable_text_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = "VR" + "soundscape"
            suffixes = [
                ".py",
                ".xml",
                ".uxml",
                ".uss",
                ".prefab",
                ".asset",
                ".meta",
                ".custom",
            ]
            for index, suffix in enumerate(suffixes):
                (root / f"surface-{index}{suffix}").write_text(marker, encoding="utf-8")
            errors = MODULE.scan_text_safety(root)
            for index, suffix in enumerate(suffixes):
                self.assertTrue(
                    any(f"surface-{index}{suffix}" in error for error in errors),
                    suffix,
                )

    def test_unanchored_unity_build_ignore_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".gitignore").write_text("Build/\n", encoding="utf-8")
            errors = MODULE.validate_ignore_scope(root)
            self.assertTrue(any("root-anchored" in error for error in errors))

    def test_active_old_root_git_package_url_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text(
                "https://github.com/Lingkyn/xr-foundry.git?path=/"
                "com.lingkyn.inventory.core#" + "a" * 40,
                encoding="utf-8",
            )
            errors = MODULE.validate_active_repository_path_references(root)
            self.assertTrue(any("old root Git UPM path" in error for error in errors))

    def test_active_validation_template_rejects_old_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt_root = root / "docs" / "validation"
            receipt_root.mkdir(parents=True)
            (receipt_root / "receipt-template.md").write_text(
                "https://github.com/Lingkyn/xr-foundry.git?path=/"
                "com.lingkyn.inventory.core#" + "a" * 40,
                encoding="utf-8",
            )
            errors = MODULE.validate_active_repository_path_references(root)
            self.assertTrue(any("old root Git UPM path" in error for error in errors))

    def test_active_git_selector_must_match_catalog_canonical_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text(
                "?" + "path=/packages/unity/foundations/com.lingkyn.inventory.core",
                encoding="utf-8",
            )
            catalog = {
                "packages": [
                    {
                        "id": "com.lingkyn.inventory.core",
                        "path": "packages/unity/systems/inventory/com.lingkyn.inventory.core",
                    }
                ]
            }
            errors = MODULE.validate_active_git_upm_selectors(root, catalog)
            self.assertTrue(any("selector path drift" in error for error in errors))

    def test_readme_git_install_matrix_requires_catalog_and_dependency_closure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            core_path = "packages/unity/systems/inventory/com.lingkyn.inventory.core"
            renderer_path = "packages/unity/systems/inventory/com.lingkyn.inventory.ugui"
            (root / core_path).mkdir(parents=True)
            (root / renderer_path).mkdir(parents=True)
            (root / core_path / "package.json").write_text(
                json.dumps({"name": "com.lingkyn.inventory.core", "dependencies": {}}),
                encoding="utf-8",
            )
            (root / renderer_path / "package.json").write_text(
                json.dumps(
                    {
                        "name": "com.lingkyn.inventory.ugui",
                        "dependencies": {"com.lingkyn.inventory.core": "0.1.0"},
                    }
                ),
                encoding="utf-8",
            )
            (root / "README.md").write_text(
                '"com.lingkyn.inventory.ugui": "https://github.com/Lingkyn/'
                'xr-foundry.git?path=/packages/unity/systems/inventory/'
                'com.lingkyn.inventory.ugui#<full-40-character-commit-sha>"',
                encoding="utf-8",
            )
            catalog = {
                "packages": [
                    {"id": "com.lingkyn.inventory.core", "path": core_path},
                    {"id": "com.lingkyn.inventory.ugui", "path": renderer_path},
                ]
            }
            errors = MODULE.validate_readme_git_install_matrix(root, catalog)
            self.assertTrue(any("every package catalog entry" in error for error in errors))
            self.assertTrue(any("not dependency-closed" in error for error in errors))

    def test_readme_git_install_matrix_rejects_sibling_sha_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {
                "com.lingkyn.inventory.core": (
                    "packages/unity/systems/inventory/com.lingkyn.inventory.core"
                ),
                "com.lingkyn.inventory.presentation": (
                    "packages/unity/systems/inventory/com.lingkyn.inventory.presentation"
                ),
            }
            for package_id, package_path in paths.items():
                (root / package_path).mkdir(parents=True)
                (root / package_path / "package.json").write_text(
                    json.dumps({"name": package_id, "dependencies": {}}), encoding="utf-8"
                )
            (root / "README.md").write_text(
                "\n".join(
                    f'"{package_id}": "https://github.com/Lingkyn/xr-foundry.git?path=/'
                    f'{package_path}#{revision}"'
                    for (package_id, package_path), revision in zip(
                        paths.items(), ("a" * 40, "b" * 40)
                    )
                ),
                encoding="utf-8",
            )
            catalog = {
                "packages": [
                    {"id": package_id, "path": package_path}
                    for package_id, package_path in paths.items()
                ]
            }
            errors = MODULE.validate_readme_git_install_matrix(root, catalog)
            self.assertTrue(any("same full Git SHA" in error for error in errors))

    def test_missing_internal_namespace_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            (package / "Consumer.cs").write_text(
                "using Lingkyn.Unity.Missing; namespace Lingkyn.Unity.Consumer {}",
                encoding="utf-8",
            )
            errors = MODULE.validate_internal_namespace_links(package)
            self.assertTrue(any("no source declaration" in error for error in errors))

    def test_repository_path_is_rejected_as_unity_asset_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            (package / "BadAssetPath.cs").write_text(
                'namespace Lingkyn.Example { public static class Bad { '
                'public const string Path = "packages/unity/systems/inventory/'
                'com.lingkyn.inventory.core/Runtime/Item.asset"; } }',
                encoding="utf-8",
            )
            errors = MODULE.validate_unity_asset_path_literals(
                package, {"com.lingkyn.inventory.core"}
            )
            self.assertTrue(any("repository path used as a Unity asset path" in error for error in errors))

    def test_package_id_mount_is_accepted_as_unity_asset_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            (package / "GoodAssetPath.cs").write_text(
                'namespace Lingkyn.Example { public static class Good { '
                'public const string Path = "Packages/com.lingkyn.inventory.core/'
                'Runtime/Item.asset"; } }',
                encoding="utf-8",
            )
            self.assertEqual(
                [],
                MODULE.validate_unity_asset_path_literals(
                    package, {"com.lingkyn.inventory.core"}
                ),
            )

    def test_inventory_manifest_rejects_non_positive_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source-manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "schema": "xr-foundry.inventory_source_manifest.v1",
                        "derivation_policy": "admitted_positive_external_sources_only",
                        "consumer_material_allowed": False,
                        "screened_out_material_allowed": False,
                        "implementation_policy": "independently_authored_from_public_contracts",
                        "forbidden_source_scopes": [
                            "consumer_project",
                            "course_project",
                            "internal_prototype",
                            "screened_out_candidate",
                        ],
                        "sources": [
                            {
                                "id": "bad-seed",
                                "admission": "raw_material",
                                "provenance_scope": "external_public",
                                "code_seed_allowed": False,
                                "authority_class": "maintained_open_source_implementation",
                                "url": "https://example.com/bad-seed",
                                "positive_evidence": ["popular"],
                                "limits": ["not reviewed"],
                                "license_boundary": "unknown",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            errors = MODULE.validate_inventory_source_manifest(path)
            self.assertTrue(any("not an admitted positive source" in error for error in errors))

    def test_inventory_manifest_rejects_consumer_material(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source-manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "schema": "xr-foundry.inventory_source_manifest.v1",
                        "derivation_policy": "admitted_positive_external_sources_only",
                        "consumer_material_allowed": True,
                        "screened_out_material_allowed": False,
                        "implementation_policy": "independently_authored_from_public_contracts",
                        "forbidden_source_scopes": [
                            "consumer_project",
                            "course_project",
                            "internal_prototype",
                            "screened_out_candidate",
                        ],
                        "sources": [],
                    }
                ),
                encoding="utf-8",
            )
            errors = MODULE.validate_inventory_source_manifest(path)
            self.assertTrue(any("reject consumer material" in error for error in errors))

    def test_task_contract_rejects_inferred_write_permission(self) -> None:
        payload = json.loads(
            (ROOT / "docs" / "contributing" / "task-contract.example.json").read_text(
                encoding="utf-8"
            )
        )
        payload["authority"]["write_permission_not_inferred"] = False

        errors = MODULE.validate_task_contract(payload, "unsafe task")

        self.assertTrue(any("write_permission_not_inferred" in error for error in errors))

    def test_task_hall_positive_fixtures_pass(self) -> None:
        self.assertEqual([], MODULE.validate_task_hall_contract(ROOT))
        example = json.loads(
            (ROOT / "docs" / "contributing" / "task-contract.example.json").read_text(
                encoding="utf-8"
            )
        )
        continuation = json.loads(
            (ROOT / "docs" / "contributing" / "work-continuation.example.json").read_text(
                encoding="utf-8"
            )
        )
        registry = json.loads(
            (ROOT / "docs" / "contributing" / "tasks" / "task-registry.json").read_text(
                encoding="utf-8"
            )
        )
        live_task = json.loads(
            (
                ROOT
                / "docs"
                / "contributing"
                / "tasks"
                / "agent-commons-public-workbench.task.json"
            ).read_text(encoding="utf-8")
        )
        authority = json.loads(
            (ROOT / "docs" / "contributing" / "task-hall.v1.json").read_text(encoding="utf-8")
        )

        self.assertEqual("0.3.0", authority["version"])
        self.assertEqual([], MODULE.validate_task_hall_authority(authority))
        self.assertEqual([], MODULE.validate_task_contract(example, "Task Hall example"))
        self.assertEqual(
            [], MODULE.validate_work_continuation(continuation, "Task Hall continuation")
        )
        self.assertEqual([], MODULE.validate_task_registry(ROOT, registry))
        self.assertEqual(
            [],
            MODULE.validate_task_contract(
                live_task,
                "registered live task",
                require_canonical_repository=True,
            ),
        )

    def test_governance_contract_is_proposed_inactive_and_token_neutral(self) -> None:
        self.assertEqual([], MODULE.validate_governance_contract(ROOT))
        model = MODULE.load_json(
            ROOT / "docs" / "governance" / "governance-model.v1.json"
        )

        self.assertEqual("proposed", model["status"])
        self.assertEqual("G0", model["current_stage"])
        self.assertFalse(model["activation"]["active_policy"])
        self.assertFalse(model["promotion_policy"]["automatic_promotion"])
        self.assertEqual(MODULE.GOVERNANCE_TOKEN_POLICY, model["token_policy"])
        self.assertEqual(MODULE.GOVERNANCE_EXTERNAL_EFFECTS, model["external_effects"])
        self.assertEqual(
            ["G0", "G1", "G2", "G3", "G4"],
            [stage["id"] for stage in model["stages"]],
        )

    def test_governance_contract_rejects_authority_and_external_effect_drift(self) -> None:
        model_path = ROOT / "docs" / "governance" / "governance-model.v1.json"
        original_load_json = MODULE.load_json
        model = original_load_json(model_path)
        unsafe_cases = (
            ("external_effects", "wallet", True, "external effects must remain disabled"),
            ("token_policy", "token_balance_grants_vote", True, "token-neutral"),
            ("authority", "stage_eligibility_grants_role", True, "authority boundary"),
            ("activation", "active_policy", True, "remain inactive"),
        )
        for section, field, value, expected in unsafe_cases:
            with self.subTest(section=section, field=field):
                unsafe = copy.deepcopy(model)
                unsafe[section][field] = value

                def load_with_unsafe(candidate: Path) -> dict:
                    if Path(candidate) == model_path:
                        return unsafe
                    return original_load_json(candidate)

                with mock.patch.object(MODULE, "load_json", side_effect=load_with_unsafe):
                    errors = MODULE.validate_governance_contract(ROOT)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_governance_contract_rejects_window_and_stage_drift(self) -> None:
        model_path = ROOT / "docs" / "governance" / "governance-model.v1.json"
        original_load_json = MODULE.load_json
        model = original_load_json(model_path)

        unsafe_window = copy.deepcopy(model)
        unsafe_window["decision_classes"][1]["minimum_review_days"] = 6

        def load_with_window(candidate: Path) -> dict:
            if Path(candidate) == model_path:
                return unsafe_window
            return original_load_json(candidate)

        with mock.patch.object(MODULE, "load_json", side_effect=load_with_window):
            window_errors = MODULE.validate_governance_contract(ROOT)
        self.assertTrue(any("review window has drifted" in error for error in window_errors))

        unsafe_stage = copy.deepcopy(model)
        unsafe_stage["stages"][1]["order"] = 2

        def load_with_stage(candidate: Path) -> dict:
            if Path(candidate) == model_path:
                return unsafe_stage
            return original_load_json(candidate)

        with mock.patch.object(MODULE, "load_json", side_effect=load_with_stage):
            stage_errors = MODULE.validate_governance_contract(ROOT)
        self.assertTrue(any("stages or their order have drifted" in error for error in stage_errors))

        unsafe_emergency = copy.deepcopy(model)
        unsafe_emergency["decision_classes"][0]["emergency"] = True

        def load_with_emergency(candidate: Path) -> dict:
            if Path(candidate) == model_path:
                return unsafe_emergency
            return original_load_json(candidate)

        with mock.patch.object(MODULE, "load_json", side_effect=load_with_emergency):
            emergency_errors = MODULE.validate_governance_contract(ROOT)
        self.assertTrue(
            any("emergency classification has drifted" in error for error in emergency_errors)
        )

    def test_agent_membership_contract_is_proposed_inactive_and_a1_bounded(self) -> None:
        self.assertEqual([], MODULE.validate_agent_membership_contract(ROOT))
        model = MODULE.load_json(
            ROOT / "docs" / "governance" / "agent-membership-model.v1.json"
        )
        self.assertEqual("proposed", model["status"])
        self.assertEqual("G0xA0", model["current_cell"])
        self.assertEqual("G0xA1", model["phase_one_target"])
        self.assertFalse(model["activation"]["active_policy"])
        self.assertFalse(model["activation"]["active_agent_membership"])
        self.assertEqual("A1", model["activation"]["maximum_activatable_stage"])
        self.assertEqual(MODULE.AGENT_EXTERNAL_EFFECTS, model["external_effects"])

    def test_agent_member_requires_principal_lineage_action_identity_and_mandate(self) -> None:
        example_path = ROOT / "docs" / "governance" / "agent-member.example.json"
        original_load_json = MODULE.load_json
        example = original_load_json(example_path)
        for field in ("principal_ref", "lineage_id", "action_identities", "mandates"):
            with self.subTest(field=field):
                unsafe = copy.deepcopy(example)
                del unsafe[field]

                def load_without_field(candidate: Path) -> dict:
                    if Path(candidate) == example_path:
                        return unsafe
                    return original_load_json(candidate)

                with mock.patch.object(MODULE, "load_json", side_effect=load_without_field):
                    errors = MODULE.validate_agent_membership_contract(ROOT)
                self.assertTrue(any(field in error for error in errors), errors)

    def test_agent_membership_rejects_early_a2_to_a4_activation(self) -> None:
        model_path = ROOT / "docs" / "governance" / "agent-membership-model.v1.json"
        original_load_json = MODULE.load_json
        model = original_load_json(model_path)
        for stage_id in ("A2", "A3", "A4"):
            with self.subTest(stage_id=stage_id):
                unsafe = copy.deepcopy(model)
                stage = next(item for item in unsafe["agent_stages"] if item["id"] == stage_id)
                stage["activation_allowed"] = True

                def load_with_active_stage(candidate: Path) -> dict:
                    if Path(candidate) == model_path:
                        return unsafe
                    return original_load_json(candidate)

                with mock.patch.object(MODULE, "load_json", side_effect=load_with_active_stage):
                    errors = MODULE.validate_agent_membership_contract(ROOT)
                self.assertTrue(any("A2-A4" in error for error in errors), errors)

    def test_agent_membership_rejects_authority_and_external_effect_drift(self) -> None:
        model_path = ROOT / "docs" / "governance" / "agent-membership-model.v1.json"
        original_load_json = MODULE.load_json
        model = original_load_json(model_path)
        unsafe_cases = (
            ("authority_boundaries", "membership_grants_write", "authority boundary"),
            ("authority_boundaries", "contribution_grants_write", "authority boundary"),
            ("authority_boundaries", "deliberation_grants_write", "authority boundary"),
            ("authority_boundaries", "membership_grants_merge", "authority boundary"),
            ("authority_boundaries", "membership_grants_release", "authority boundary"),
            ("authority_boundaries", "membership_grants_admin", "authority boundary"),
            ("authority_boundaries", "token_grants_authority", "authority boundary"),
            ("external_effects", "account_operation", "external effects"),
            ("external_effects", "wallet", "external effects"),
            ("external_effects", "treasury", "external effects"),
            ("external_effects", "token", "external effects"),
            ("external_effects", "smart_contract", "external effects"),
            ("external_effects", "onchain_execution", "external effects"),
            ("external_effects", "remote_settings_change", "external effects"),
        )
        for section, field, expected in unsafe_cases:
            with self.subTest(section=section, field=field):
                unsafe = copy.deepcopy(model)
                unsafe[section][field] = True

                def load_with_unsafe(candidate: Path) -> dict:
                    if Path(candidate) == model_path:
                        return unsafe
                    return original_load_json(candidate)

                with mock.patch.object(MODULE, "load_json", side_effect=load_with_unsafe):
                    errors = MODULE.validate_agent_membership_contract(ROOT)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_agent_membership_rejects_false_independence_and_evidence_multiplication(self) -> None:
        model_path = ROOT / "docs" / "governance" / "agent-membership-model.v1.json"
        original_load_json = MODULE.load_json
        model = original_load_json(model_path)
        unsafe_cases = (
            (
                "independence_policy",
                "same_principal_counts_as_independent",
                "principal-and-lineage independence",
            ),
            (
                "independence_policy",
                "same_lineage_counts_as_independent",
                "principal-and-lineage independence",
            ),
            (
                "independence_policy",
                "same_principal_formal_review",
                "principal-and-lineage independence",
            ),
            (
                "independence_policy",
                "same_lineage_formal_review",
                "principal-and-lineage independence",
            ),
            (
                "evidence_policy",
                "same_ancestry_multiplies_evidence",
                "evidence ancestry",
            ),
        )
        for section, field, expected in unsafe_cases:
            with self.subTest(section=section, field=field):
                unsafe = copy.deepcopy(model)
                unsafe[section][field] = True

                def load_with_unsafe(candidate: Path) -> dict:
                    if Path(candidate) == model_path:
                        return unsafe
                    return original_load_json(candidate)

                with mock.patch.object(MODULE, "load_json", side_effect=load_with_unsafe):
                    errors = MODULE.validate_agent_membership_contract(ROOT)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_governance_deliberation_metadata_enforces_complete_review_windows(self) -> None:
        schema = ROOT / "docs" / "contributing" / "deliberation-record.schema.json"
        open_record = MODULE.load_json(
            ROOT / "docs" / "contributing" / "deliberation-record.open.example.json"
        )
        valid = copy.deepcopy(open_record)
        valid.update(
            {
                "decision_class": "governance_policy",
                "governance_stage": "G0",
                "review_opened_at": "2026-09-03T12:00:00Z",
                "review_not_before": "2026-09-10T12:00:00Z",
            }
        )
        self.assertEqual(
            [], MODULE.validate_json_schema_instance(valid, schema, "valid governance review")
        )
        self.assertEqual(
            [], MODULE.validate_governance_deliberation_metadata(valid, "valid governance review")
        )

        partial = copy.deepcopy(open_record)
        partial["decision_class"] = "governance_policy"
        self.assertTrue(
            MODULE.validate_json_schema_instance(partial, schema, "partial governance review")
        )
        self.assertTrue(
            any(
                "all-or-none" in error
                for error in MODULE.validate_governance_deliberation_metadata(
                    partial, "partial governance review"
                )
            )
        )

        short_policy = copy.deepcopy(valid)
        short_policy["review_not_before"] = "2026-09-10T11:59:59Z"
        self.assertTrue(
            any(
                "at least 7 days" in error
                for error in MODULE.validate_governance_deliberation_metadata(
                    short_policy, "short policy review"
                )
            )
        )

        non_utc = copy.deepcopy(valid)
        non_utc["review_opened_at"] = "2026-09-03T13:00:00+01:00"
        non_utc["review_not_before"] = "2026-09-10T13:00:00+01:00"
        self.assertTrue(
            any(
                "must use UTC" in error
                for error in MODULE.validate_governance_deliberation_metadata(
                    non_utc, "non-UTC governance review"
                )
            )
        )

        short_constitution = copy.deepcopy(valid)
        short_constitution["decision_class"] = "constitutional_change"
        short_constitution["review_not_before"] = "2026-09-17T11:59:59Z"
        self.assertTrue(
            any(
                "at least 14 days" in error
                for error in MODULE.validate_governance_deliberation_metadata(
                    short_constitution, "short constitutional review"
                )
            )
        )

        resolved = MODULE.load_json(
            ROOT / "docs" / "contributing" / "deliberation-record.resolved.example.json"
        )
        resolved.update(
            {
                "decision_class": "constitutional_change",
                "governance_stage": "G0",
                "review_opened_at": "2026-09-03T12:00:00Z",
                "review_not_before": "2026-09-17T12:00:00Z",
            }
        )
        resolved["decision"]["decided_at"] = "2026-09-17T11:59:59Z"
        self.assertTrue(
            any(
                "predates review_not_before" in error
                for error in MODULE.validate_governance_deliberation_metadata(
                    resolved, "early resolved governance review"
                )
            )
        )

    def test_deliberation_terminal_states_fail_closed(self) -> None:
        schema = ROOT / "docs" / "contributing" / "deliberation-record.schema.json"
        open_record = json.loads(
            (ROOT / "docs" / "contributing" / "deliberation-record.open.example.json").read_text(
                encoding="utf-8"
            )
        )
        resolved_record = json.loads(
            (ROOT / "docs" / "contributing" / "deliberation-record.resolved.example.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            [], MODULE.validate_json_schema_instance(open_record, schema, "open deliberation")
        )
        self.assertEqual(
            [], MODULE.validate_json_schema_instance(resolved_record, schema, "resolved deliberation")
        )

        unsafe_open = json.loads(json.dumps(open_record))
        unsafe_open["execution"]["readiness"] = "ready"
        self.assertTrue(
            MODULE.validate_json_schema_instance(unsafe_open, schema, "unsafe open deliberation")
        )
        missing_decision = json.loads(json.dumps(resolved_record))
        missing_decision["decision"] = None
        self.assertTrue(
            MODULE.validate_json_schema_instance(missing_decision, schema, "missing decision")
        )
        rejected_ready = json.loads(json.dumps(resolved_record))
        rejected_ready["status"] = "rejected"
        self.assertTrue(
            MODULE.validate_json_schema_instance(rejected_ready, schema, "rejected ready")
        )
        superseded_ready = json.loads(json.dumps(resolved_record))
        superseded_ready["status"] = "superseded"
        self.assertTrue(
            MODULE.validate_json_schema_instance(superseded_ready, schema, "superseded ready")
        )
        superseded_executable = json.loads(json.dumps(resolved_record))
        superseded_executable["status"] = "superseded"
        superseded_executable["execution"]["readiness"] = "superseded"
        self.assertTrue(
            MODULE.validate_json_schema_instance(
                superseded_executable, schema, "superseded executable task"
            )
        )
        rejected_executable = json.loads(json.dumps(resolved_record))
        rejected_executable["status"] = "rejected"
        rejected_executable["decision"] = None
        rejected_executable["execution"]["readiness"] = "not_ready"
        self.assertTrue(
            MODULE.validate_json_schema_instance(
                rejected_executable, schema, "rejected executable task"
            )
        )

    def test_independent_review_receipt_requires_distinct_agents_and_closed_findings(self) -> None:
        payload = json.loads(
            (ROOT / "docs" / "validation" / "independent-review-receipt.example.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            [], MODULE.validate_independent_review_receipt(payload, "review example", root=ROOT)
        )
        accepted = json.loads(json.dumps(payload))
        accepted["record_status"] = "accepted"
        accepted["reviewed_commit"] = public_fixture_commit()
        accepted["maintainer_decision"]["decision"] = "approved"
        accepted["checks"][0]["status"] = "pass"
        accepted["findings"][0]["status"] = "resolved"
        accepted["conclusion"] = "pass"
        accepted["independent_review"]["assisted_by"] = accepted["executor"]["assisted_by"]
        same_agent_errors = MODULE.validate_independent_review_receipt(
            accepted, "same-agent review", root=ROOT
        )
        self.assertTrue(any("disjoint executor and reviewer" in error for error in same_agent_errors))

        unsafe_finding = json.loads(json.dumps(accepted))
        unsafe_finding["independent_review"]["assisted_by"] = ["Independent Review Agent"]
        unsafe_finding["findings"][0]["status"] = "open"
        finding_errors = MODULE.validate_independent_review_receipt(
            unsafe_finding, "open-finding review", root=ROOT
        )
        self.assertTrue(any("JSON Schema violation" in error for error in finding_errors))

        valid_shared_maintainer = json.loads(json.dumps(accepted))
        valid_shared_maintainer["independent_review"]["assisted_by"] = [
            "Independent Review Agent"
        ]
        self.assertEqual(
            [],
            MODULE.validate_independent_review_receipt(
                valid_shared_maintainer, "shared-maintainer review", root=ROOT
            ),
        )

    def test_completed_high_risk_checkpoint_requires_immutable_review_evidence(self) -> None:
        payload = json.loads(
            (ROOT / "docs" / "contributing" / "task-contract.example.json").read_text(
                encoding="utf-8"
            )
        )
        checkpoint = payload["checkpoints"][2]
        evidence = [
            {
                "id": "E-DESIGN-ONLY",
                "kind": "design",
                "location": "docs/example.md",
                "commit": "0" * 40,
                "summary": "Implementation evidence is not independent review evidence.",
            }
        ]
        errors = MODULE.validate_checkpoint_routing(
            checkpoint["routing"],
            "high-risk without review",
            device=checkpoint["device"],
            evidence=evidence,
            status="completed",
        )
        self.assertTrue(
            any("completed high-risk checkpoint requires immutable review evidence" in error for error in errors)
        )

        forged_review = json.loads(json.dumps(evidence))
        forged_review[0]["kind"] = "review"
        forged_errors = MODULE.validate_checkpoint_routing(
            checkpoint["routing"],
            "high-risk forged review",
            device=checkpoint["device"],
            evidence=forged_review,
            status="completed",
            root=ROOT,
        )
        self.assertTrue(
            any("completed high-risk checkpoint requires immutable review evidence" in error for error in forged_errors)
        )

    def test_contract_test_gate_is_fail_fast_and_propagates_test_failure(self) -> None:
        repository_errors = ["repository contract failed"]
        with mock.patch.object(MODULE.subprocess, "run") as runner:
            skipped = MODULE.run_contract_test_gate(ROOT, repository_errors)
        runner.assert_not_called()
        self.assertEqual("skipped", skipped["status"])

        test_errors: list[str] = []
        failed_process = subprocess.CompletedProcess([], 1, stdout="failed", stderr="boom")
        with mock.patch.object(MODULE.subprocess, "run", return_value=failed_process):
            failed = MODULE.run_contract_test_gate(ROOT, test_errors)
        self.assertEqual("fail", failed["status"])
        self.assertTrue(any("Contract test suite failed" in error for error in test_errors))

        clean_errors: list[str] = []
        passed_process = subprocess.CompletedProcess([], 0, stdout="ok", stderr="")
        with mock.patch.object(MODULE.subprocess, "run", return_value=passed_process):
            passed = MODULE.run_contract_test_gate(ROOT, clean_errors)
        self.assertEqual("pass", passed["status"])
        self.assertEqual([], clean_errors)

    def test_task_contract_rejects_competing_umbrella_lifecycle(self) -> None:
        payload = json.loads(
            (ROOT / "docs" / "contributing" / "task-contract.example.json").read_text(
                encoding="utf-8"
            )
        )
        payload["state"] = "in_progress"

        errors = MODULE.validate_task_contract(payload, "stale lifecycle task")

        self.assertTrue(any("canonical Task Hall umbrella lifecycle" in error for error in errors))

    def test_task_contract_rejects_missing_and_duplicate_issue_projections(self) -> None:
        payload = json.loads(
            (ROOT / "docs" / "contributing" / "task-contract.example.json").read_text(
                encoding="utf-8"
            )
        )
        missing = json.loads(json.dumps(payload))
        missing["public_projection"]["checkpoint_issues"] = missing["public_projection"][
            "checkpoint_issues"
        ][:-1]
        missing_errors = MODULE.validate_task_contract(missing, "missing projection")
        self.assertTrue(any("missing checkpoint Issue projections" in error for error in missing_errors))

        duplicate = json.loads(json.dumps(payload))
        duplicate["public_projection"]["checkpoint_issues"].append(
            {
                "checkpoint_id": "CP-01",
                "issue": "https://github.com/example-org/example-repo/issues/199",
            }
        )
        duplicate_id_errors = MODULE.validate_task_contract(duplicate, "duplicate checkpoint projection")
        self.assertTrue(
            any("duplicate checkpoint Issue projections" in error for error in duplicate_id_errors)
        )

        duplicate_issue = json.loads(json.dumps(payload))
        duplicate_issue["public_projection"]["checkpoint_issues"][1]["issue"] = duplicate_issue[
            "public_projection"
        ]["checkpoint_issues"][0]["issue"]
        duplicate_issue_errors = MODULE.validate_task_contract(
            duplicate_issue, "duplicate issue projection"
        )
        self.assertTrue(any("duplicate Issue projections" in error for error in duplicate_issue_errors))

        umbrella_collision = json.loads(json.dumps(payload))
        umbrella_collision["public_projection"]["checkpoint_issues"][0]["issue"] = (
            umbrella_collision["public_projection"]["umbrella_issue"]
        )
        umbrella_errors = MODULE.validate_task_contract(
            umbrella_collision, "checkpoint equals umbrella"
        )
        self.assertTrue(
            any("checkpoint Issue cannot equal umbrella Issue" in error for error in umbrella_errors)
        )
        self.assertTrue(
            any("unique role-separated set" in error for error in umbrella_errors)
        )

    def test_task_contract_rejects_foreign_repository_projections(self) -> None:
        payload = json.loads(
            (ROOT / "docs" / "contributing" / "task-contract.example.json").read_text(
                encoding="utf-8"
            )
        )
        payload["public_projection"]["checkpoint_issues"][0]["issue"] = (
            "https://github.com/other-org/other-repo/issues/101"
        )

        errors = MODULE.validate_task_contract(payload, "foreign projection")

        self.assertTrue(any("foreign repository" in error for error in errors))

    def test_registered_task_requires_canonical_task_hall_project(self) -> None:
        payload = json.loads(
            (
                ROOT
                / "docs"
                / "contributing"
                / "tasks"
                / "agent-commons-public-workbench.task.json"
            ).read_text(encoding="utf-8")
        )
        payload["public_projection"]["project"] = "https://github.com/orgs/other-org/projects/9"

        errors = MODULE.validate_task_contract(
            payload,
            "non-canonical project",
            require_canonical_repository=True,
        )

        self.assertTrue(
            any("canonical Task Hall Project" in error for error in errors)
        )

    def test_task_contract_rejects_self_authorizing_and_unqualified_high_risk_routing(
        self,
    ) -> None:
        payload = json.loads(
            (ROOT / "docs" / "contributing" / "task-contract.example.json").read_text(
                encoding="utf-8"
            )
        )
        self_auth = json.loads(json.dumps(payload))
        self_auth["checkpoints"][0]["routing"]["self_report_grants_authority"] = True
        self_auth_errors = MODULE.validate_task_contract(self_auth, "self-authorizing")
        self.assertTrue(any("self-authorizing routing" in error for error in self_auth_errors))
        self.assertTrue(any("JSON Schema violation" in error for error in self_auth_errors))

        unqualified = json.loads(json.dumps(payload))
        routing = unqualified["checkpoints"][2]["routing"]
        routing["judgment_level"] = "security_or_release"
        routing["required_capabilities"] = []
        routing["qualification_evidence"] = []
        routing["independent_review"] = "not_required"
        unqualified_errors = MODULE.validate_task_contract(unqualified, "unqualified high-risk")
        self.assertTrue(
            any("unqualified high-risk execution" in error for error in unqualified_errors)
        )
        self.assertTrue(
            any("high-risk routing requires required_capabilities" in error for error in unqualified_errors)
        )

    def test_required_device_review_requires_device_capability_gate_and_evidence(self) -> None:
        payload = json.loads(
            (ROOT / "docs" / "contributing" / "task-contract.example.json").read_text(
                encoding="utf-8"
            )
        )
        incomplete = json.loads(json.dumps(payload))
        routing = incomplete["checkpoints"][0]["routing"]
        routing["independent_review"] = "required_device"
        routing["required_devices"] = []
        incomplete["checkpoints"][0]["device"] = {
            "required": False,
            "profiles": [],
            "acceptance": [],
            "evidence": [],
        }
        incomplete_errors = MODULE.validate_task_contract(incomplete, "incomplete device review")
        self.assertTrue(
            any("non-empty required_devices" in error for error in incomplete_errors)
        )
        self.assertTrue(
            any("coherent device gate" in error for error in incomplete_errors)
        )

        completed = json.loads(json.dumps(payload))
        completed_routing = completed["checkpoints"][0]["routing"]
        completed_routing["independent_review"] = "required_device"
        completed_routing["required_devices"] = ["pico-openxr-controller"]
        completed["checkpoints"][0]["device"] = {
            "required": True,
            "profiles": ["pico-openxr-controller"],
            "acceptance": ["Confirm world-space UI comfort on device"],
            "evidence": [],
        }
        completed["checkpoints"][0]["status"] = "completed"
        completed["checkpoints"][0]["evidence"] = [
            {
                "id": "E-NON-DEVICE",
                "kind": "test",
                "location": "docs/device-lab/README.md",
                "commit": "0000000000000000000000000000000000000000",
                "summary": "Not device evidence",
            }
        ]
        completed_errors = MODULE.validate_task_contract(completed, "completed without device evidence")
        self.assertTrue(
            any(
                "completed required_device checkpoint requires device evidence" in error
                for error in completed_errors
            )
        )

    def test_task_contract_rejects_duplicate_checkpoint_local_ids(self) -> None:
        payload = json.loads(
            (ROOT / "docs" / "contributing" / "task-contract.example.json").read_text(
                encoding="utf-8"
            )
        )
        duplicate_acceptance = json.loads(json.dumps(payload))
        duplicate_acceptance["checkpoints"][0]["acceptance"].append(
            {
                "id": "AC-01",
                "criterion": "Duplicate local acceptance id must fail closed.",
            }
        )
        acceptance_errors = MODULE.validate_task_contract(
            duplicate_acceptance, "duplicate acceptance ids"
        )
        self.assertTrue(
            any("duplicate acceptance id AC-01" in error for error in acceptance_errors)
        )

        duplicate_verification = json.loads(json.dumps(payload))
        duplicate_verification["checkpoints"][0]["verification"].append(
            {
                "id": "V-01",
                "procedure": "Repeat the same verification id.",
                "expected": "Validation fails closed.",
                "evidence_required": True,
            }
        )
        verification_errors = MODULE.validate_task_contract(
            duplicate_verification, "duplicate verification ids"
        )
        self.assertTrue(
            any("duplicate verification id V-01" in error for error in verification_errors)
        )

        duplicate_evidence = json.loads(json.dumps(payload))
        duplicate_evidence["checkpoints"][0]["evidence"].append(
            {
                "id": "E-CP01",
                "kind": "test",
                "location": "docs/architecture/example-duplicate.md",
                "commit": "0000000000000000000000000000000000000000",
                "summary": "Duplicate evidence id must fail closed.",
            }
        )
        evidence_errors = MODULE.validate_task_contract(
            duplicate_evidence, "duplicate evidence ids"
        )
        self.assertTrue(
            any("duplicate evidence id E-CP01" in error for error in evidence_errors)
        )

    def test_task_contract_rejects_unresolved_device_evidence_references(self) -> None:
        payload = json.loads(
            (ROOT / "docs" / "contributing" / "task-contract.example.json").read_text(
                encoding="utf-8"
            )
        )
        payload["checkpoints"][1]["device"] = {
            "required": True,
            "profiles": ["pico-openxr-controller"],
            "acceptance": ["Confirm the device evidence reference resolves locally"],
            "evidence": ["E-MISSING-DEVICE"],
        }

        errors = MODULE.validate_task_contract(payload, "unresolved device evidence")

        self.assertTrue(
            any(
                "device evidence reference 'E-MISSING-DEVICE' does not resolve within the checkpoint"
                in error
                for error in errors
            )
        )

    def test_task_contract_rejects_overlapping_concurrent_allowed_paths(self) -> None:
        payload = json.loads(
            (
                ROOT
                / "docs"
                / "contributing"
                / "tasks"
                / "agent-commons-public-workbench.task.json"
            ).read_text(encoding="utf-8")
        )
        for checkpoint in payload["checkpoints"]:
            if checkpoint["id"] == "WB-01V":
                activate_checkpoint_fixture(checkpoint)
            elif checkpoint["id"] == "WB-05":
                activate_checkpoint_fixture(checkpoint)
                checkpoint["allowed_paths"] = [
                    "scripts/validate_repository.py",
                    "docs/contributing/deliberation-protocol.md",
                ]
                break

        errors = MODULE.validate_task_contract(
            payload,
            "overlapping concurrent writes",
            require_canonical_repository=True,
        )

        self.assertTrue(
            any(
                "concurrent checkpoints WB-01V and WB-05 claim overlapping allowed_paths"
                in error
                for error in errors
            )
        )

    def test_allowed_paths_overlap_detects_docs_glob_starstar_witness(self) -> None:
        self.assertTrue(MODULE.allowed_paths_overlap("docs/**/foo", "docs/bar/**"))
        self.assertTrue(MODULE.allowed_path_matches("docs/bar/foo", "docs/**/foo"))
        self.assertTrue(MODULE.allowed_path_matches("docs/bar/foo", "docs/bar/**"))
        self.assertFalse(MODULE.allowed_paths_overlap("packages/a/**", "packages/b/**"))

        payload = json.loads(
            (
                ROOT
                / "docs"
                / "contributing"
                / "tasks"
                / "agent-commons-public-workbench.task.json"
            ).read_text(encoding="utf-8")
        )
        for checkpoint in payload["checkpoints"]:
            if checkpoint["id"] == "WB-01V":
                activate_checkpoint_fixture(checkpoint)
                checkpoint["allowed_paths"] = ["docs/**/foo"]
            elif checkpoint["id"] == "WB-05":
                activate_checkpoint_fixture(checkpoint)
                checkpoint["allowed_paths"] = ["docs/bar/**"]

        errors = MODULE.validate_task_contract(
            payload,
            "glob intersection witness",
            require_canonical_repository=True,
        )
        self.assertTrue(
            any(
                "concurrent checkpoints WB-01V and WB-05 claim overlapping allowed_paths"
                in error
                for error in errors
            )
        )

    def test_allowed_paths_unify_starstar_segment_grammar_docs_a_starstar_foo(self) -> None:
        # Embedded ** is illegal; previously matching treated docs/a**/foo as crossing
        # slash so it shared witness docs/a/x/foo with docs/a/x/foo while intersection
        # treated the patterns as disjoint.
        self.assertFalse(
            MODULE.is_safe_repository_relative_allowed_path("docs/a**/foo")
        )
        self.assertFalse(MODULE.allowed_path_matches("docs/a/x/foo", "docs/a**/foo"))
        self.assertTrue(MODULE.allowed_paths_overlap("docs/a**/foo", "docs/a/x/foo"))

        payload = json.loads(
            (
                ROOT
                / "docs"
                / "contributing"
                / "tasks"
                / "agent-commons-public-workbench.task.json"
            ).read_text(encoding="utf-8")
        )
        for checkpoint in payload["checkpoints"]:
            if checkpoint["id"] == "WB-01V":
                activate_checkpoint_fixture(checkpoint)
                checkpoint["allowed_paths"] = ["docs/a**/foo"]
            elif checkpoint["id"] == "WB-05":
                activate_checkpoint_fixture(checkpoint)
                checkpoint["allowed_paths"] = ["docs/a/x/foo"]

        errors = MODULE.validate_task_contract(
            payload,
            "embedded starstar grammar regression",
            require_canonical_repository=True,
        )
        self.assertTrue(
            any(
                "allowed_path 'docs/a**/foo' is not a safe repository-relative path" in error
                for error in errors
            ),
            errors,
        )
        self.assertTrue(
            any(
                "concurrent checkpoints WB-01V and WB-05 claim overlapping allowed_paths"
                in error
                for error in errors
            ),
            errors,
        )

    def test_allowed_paths_reject_unsafe_repository_relative_forms(self) -> None:
        unsafe_paths = [
            "../outside/**",
            "/tmp/**",
            "C:/temp/**",
            "c:\\temp\\**",
            "//server/share/**",
            "\\\\server\\share\\**",
            "docs/../scripts/**",
            "docs/./foo",
            "docs//foo",
            "docs/a**/foo",
            "",
            ".",
            "..",
            "**/../secret",
        ]
        for pattern in unsafe_paths:
            self.assertFalse(
                MODULE.is_safe_repository_relative_allowed_path(pattern),
                pattern,
            )

        self.assertTrue(
            MODULE.is_safe_repository_relative_allowed_path("docs/contributing/tasks/**")
        )
        self.assertTrue(
            MODULE.is_safe_repository_relative_allowed_path("docs/**/foo")
        )
        self.assertTrue(
            MODULE.is_safe_repository_relative_allowed_path("scripts/validate_repository.py")
        )

        payload = json.loads(
            (
                ROOT
                / "docs"
                / "contributing"
                / "tasks"
                / "agent-commons-public-workbench.task.json"
            ).read_text(encoding="utf-8")
        )
        for checkpoint in payload["checkpoints"]:
            if checkpoint["id"] == "WB-01V":
                checkpoint["allowed_paths"] = ["docs/../scripts/**"]
                break

        errors = MODULE.validate_task_contract(
            payload,
            "unsafe relative allowed_paths",
            require_canonical_repository=True,
        )
        self.assertTrue(
            any(
                "allowed_path 'docs/../scripts/**' is not a safe repository-relative path"
                in error
                for error in errors
            ),
            errors,
        )

        absolute_payload = json.loads(json.dumps(payload))
        for checkpoint in absolute_payload["checkpoints"]:
            if checkpoint["id"] == "WB-01V":
                checkpoint["allowed_paths"] = ["/tmp/**"]
                break
        absolute_errors = MODULE.validate_task_contract(
            absolute_payload,
            "absolute allowed_paths",
            require_canonical_repository=True,
        )
        self.assertTrue(
            any(
                "allowed_path '/tmp/**' is not a safe repository-relative path" in error
                for error in absolute_errors
            ),
            absolute_errors,
        )

        drive_payload = json.loads(json.dumps(payload))
        for checkpoint in drive_payload["checkpoints"]:
            if checkpoint["id"] == "WB-01V":
                checkpoint["allowed_paths"] = ["C:/temp/**"]
                break
        drive_errors = MODULE.validate_task_contract(
            drive_payload,
            "drive allowed_paths",
            require_canonical_repository=True,
        )
        self.assertTrue(
            any(
                "allowed_path 'C:/temp/**' is not a safe repository-relative path" in error
                for error in drive_errors
            ),
            drive_errors,
        )

        parent_payload = json.loads(json.dumps(payload))
        for checkpoint in parent_payload["checkpoints"]:
            if checkpoint["id"] == "WB-01V":
                checkpoint["allowed_paths"] = ["../outside/**"]
                break
        parent_errors = MODULE.validate_task_contract(
            parent_payload,
            "parent escape allowed_paths",
            require_canonical_repository=True,
        )
        self.assertTrue(
            any(
                "allowed_path '../outside/**' is not a safe repository-relative path"
                in error
                for error in parent_errors
            ),
            parent_errors,
        )

    def test_allowed_paths_casefold_ownership_aliases_overlap(self) -> None:
        self.assertTrue(MODULE.allowed_paths_overlap("README.md", "readme.md"))
        self.assertTrue(MODULE.allowed_paths_overlap("Docs/**", "docs/foo"))
        self.assertFalse(MODULE.allowed_paths_overlap("README.md", "LICENSE.md"))

        payload = json.loads(
            (
                ROOT
                / "docs"
                / "contributing"
                / "tasks"
                / "agent-commons-public-workbench.task.json"
            ).read_text(encoding="utf-8")
        )
        for checkpoint in payload["checkpoints"]:
            if checkpoint["id"] == "WB-01V":
                activate_checkpoint_fixture(checkpoint)
                checkpoint["allowed_paths"] = ["README.md"]
            elif checkpoint["id"] == "WB-05":
                activate_checkpoint_fixture(checkpoint)
                checkpoint["allowed_paths"] = ["readme.md"]

        errors = MODULE.validate_task_contract(
            payload,
            "casefold ownership alias",
            require_canonical_repository=True,
        )
        self.assertTrue(
            any(
                "concurrent checkpoints WB-01V and WB-05 claim overlapping allowed_paths"
                in error
                for error in errors
            ),
            errors,
        )

        same = json.loads(
            (
                ROOT
                / "docs"
                / "contributing"
                / "tasks"
                / "agent-commons-public-workbench.task.json"
            ).read_text(encoding="utf-8")
        )
        for checkpoint in same["checkpoints"]:
            if checkpoint["id"] == "WB-01V":
                checkpoint["allowed_paths"] = ["README.md", "readme.md"]
                break
        same_errors = MODULE.validate_task_contract(
            same,
            "casefold duplicate within checkpoint",
            require_canonical_repository=True,
        )
        self.assertTrue(
            any(
                "collides under portable ownership-key aliasing" in error
                for error in same_errors
            ),
            same_errors,
        )

    def test_allowed_paths_portable_ownership_key_rejects_windows_aliases_and_controls(
        self,
    ) -> None:
        import unicodedata

        nfd_readme = "README" + unicodedata.normalize("NFD", "é") + ".md"
        nfc_readme = unicodedata.normalize("NFC", nfd_readme)
        self.assertNotEqual(nfd_readme, nfc_readme)

        next_line = "docs/foo\u0085bar"
        zero_width = "docs/foo\u200bbar"
        bidi_cf = "docs/foo\u202ebar"
        self.assertEqual(unicodedata.category("\u0085"), "Cc")
        self.assertEqual(unicodedata.category("\u200b"), "Cf")
        self.assertEqual(unicodedata.category("\u202e"), "Cf")
        unsafe_aliases = [
            "README.md.",
            "README.md::",
            "README.md::$DATA",
            "README.md\x00",
            "README.md\x1f",
            "README.md\x7f",
            next_line,
            zero_width,
            bidi_cf,
            " CON",
            "CON ",
            "docs\\readme.md",
            " docs/foo",
            "docs/foo ",
            "NUL",
            "nul.txt",
            "COM1",
            "COM¹",
            "COM²",
            "COM³",
            "lpt9.log",
            "LPT¹",
            "LPT².txt",
            "LPT³.log",
            "AUX.cache",
            "PRN.md",
            "docs/foo.",
            "docs/foo /bar",
            nfd_readme,
        ]
        for pattern in unsafe_aliases:
            self.assertIsNone(
                MODULE.allowed_path_ownership_key(pattern),
                pattern,
            )
            self.assertFalse(
                MODULE.is_safe_repository_relative_allowed_path(pattern),
                pattern,
            )

        self.assertEqual(
            MODULE.allowed_path_ownership_key("README.md"),
            "readme.md",
        )
        self.assertEqual(
            MODULE.allowed_path_ownership_key(nfc_readme),
            nfc_readme.casefold(),
        )
        self.assertTrue(
            MODULE.is_safe_repository_relative_allowed_path("docs/**/foo")
        )
        self.assertTrue(
            MODULE.is_safe_repository_relative_allowed_path("docs/*/?.md")
        )

        # Unsafe aliases fail closed for overlap and never match canonically.
        self.assertTrue(MODULE.allowed_paths_overlap("README.md", "README.md."))
        self.assertTrue(MODULE.allowed_paths_overlap("README.md", "README.md::"))
        self.assertTrue(
            MODULE.allowed_paths_overlap("README.md", "README.md::$DATA")
        )
        self.assertTrue(MODULE.allowed_paths_overlap("README.md", nfd_readme))
        self.assertFalse(MODULE.allowed_path_matches("README.md.", "README.md."))
        self.assertFalse(
            MODULE.allowed_path_matches("README.md::$DATA", "README.md::$DATA")
        )
        self.assertTrue(MODULE.allowed_path_matches("README.md", "README.md"))
        self.assertTrue(MODULE.allowed_path_matches("readme.md", "README.md"))
        self.assertTrue(MODULE.allowed_path_matches(nfc_readme, nfc_readme))

        workbench = (
            ROOT
            / "docs"
            / "contributing"
            / "tasks"
            / "agent-commons-public-workbench.task.json"
        )

        def contract_errors(left: str, right: str, label: str) -> list[str]:
            payload = json.loads(workbench.read_text(encoding="utf-8"))
            for checkpoint in payload["checkpoints"]:
                if checkpoint["id"] == "WB-01V":
                    activate_checkpoint_fixture(checkpoint)
                    checkpoint["allowed_paths"] = [left]
                elif checkpoint["id"] == "WB-05":
                    activate_checkpoint_fixture(checkpoint)
                    checkpoint["allowed_paths"] = [right]
            return MODULE.validate_task_contract(
                payload,
                label,
                require_canonical_repository=True,
            )

        attack_pairs = [
            ("README.md.", "README.md", "trailing-dot ownership alias"),
            ("README.md::", "README.md", "ads-colon ownership alias"),
            ("README.md::$DATA", "README.md", "ads-data ownership alias"),
            ("README.md\x00", "README.md", "c0-control ownership alias"),
            (next_line, "README.md", "u+0085-cc ownership alias"),
            (zero_width, "README.md", "u+200b-cf ownership alias"),
            (bidi_cf, "README.md", "bidi-cf ownership alias"),
            ("NUL.txt", "README.md", "reserved-device ownership"),
            ("COM¹", "README.md", "superscript-com1 ownership"),
            ("LPT².txt", "README.md", "superscript-lpt2 ownership"),
            ("docs\\readme.md", "README.md", "backslash ownership alias"),
            (" README.md", "README.md", "outer-whitespace ownership alias"),
            (nfd_readme, nfc_readme, "nfd-nfc ownership alias"),
        ]
        for left, right, label in attack_pairs:
            errors = contract_errors(left, right, label)
            self.assertTrue(
                any(
                    f"allowed_path {left!r} is not a safe repository-relative path"
                    in error
                    for error in errors
                ),
                (label, errors),
            )
            self.assertTrue(
                any(
                    "concurrent checkpoints WB-01V and WB-05 claim overlapping allowed_paths"
                    in error
                    for error in errors
                ),
                (label, errors),
            )

        duplicate = json.loads(workbench.read_text(encoding="utf-8"))
        for checkpoint in duplicate["checkpoints"]:
            if checkpoint["id"] == "WB-01V":
                checkpoint["allowed_paths"] = [nfc_readme, nfc_readme]
                break
        duplicate_errors = MODULE.validate_task_contract(
            duplicate,
            "nfc ownership duplicate",
            require_canonical_repository=True,
        )
        self.assertTrue(
            any(
                "collides under portable ownership-key aliasing" in error
                for error in duplicate_errors
            ),
            duplicate_errors,
        )

    def test_task_contract_rejects_non_downstream_integration_fan_in(self) -> None:
        payload = json.loads(
            (ROOT / "docs" / "contributing" / "task-contract.example.json").read_text(
                encoding="utf-8"
            )
        )
        payload["integration"]["checkpoint_id"] = "CP-01"

        errors = MODULE.validate_task_contract(payload, "non-downstream fan-in")

        self.assertTrue(
            any(
                "integration checkpoint CP-01 must be downstream of CP-02" in error
                for error in errors
            )
        )
        self.assertTrue(
            any(
                "integration checkpoint CP-01 must be downstream of CP-03" in error
                for error in errors
            )
        )

    def test_task_registry_enforces_safe_unique_and_agreeing_entries(self) -> None:
        registry = json.loads(
            (ROOT / "docs" / "contributing" / "tasks" / "task-registry.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual([], MODULE.validate_task_registry(ROOT, registry))

        unsafe = json.loads(json.dumps(registry))
        unsafe["tasks"][0]["contract"] = "docs/contributing/tasks/../task-hall.v1.json"
        unsafe_errors = MODULE.validate_task_registry(ROOT, unsafe, "unsafe registry")
        self.assertTrue(any("contract path is unsafe" in error for error in unsafe_errors))

        missing = json.loads(json.dumps(registry))
        missing["tasks"][0]["contract"] = "docs/contributing/tasks/missing-task.task.json"
        missing_errors = MODULE.validate_task_registry(ROOT, missing, "missing registry")
        self.assertTrue(any("does not exist" in error for error in missing_errors))

        duplicate = json.loads(json.dumps(registry))
        duplicate["tasks"].append(json.loads(json.dumps(duplicate["tasks"][0])))
        duplicate_errors = MODULE.validate_task_registry(ROOT, duplicate, "duplicate registry")
        self.assertTrue(any("duplicate task id" in error for error in duplicate_errors))

        mismatched = json.loads(json.dumps(registry))
        current_state = mismatched["tasks"][0]["state"]
        mismatched["tasks"][0]["state"] = (
            "active" if current_state != "active" else "closed"
        )
        mismatched["tasks"][0]["umbrella_issue"] = "https://github.com/Lingkyn/xr-foundry/issues/999"
        mismatch_errors = MODULE.validate_task_registry(ROOT, mismatched, "mismatched registry")
        self.assertTrue(any("contract state must equal" in error for error in mismatch_errors))
        self.assertTrue(any("umbrella Issue must equal" in error for error in mismatch_errors))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract_rel = "docs/contributing/tasks/agent-commons-public-workbench.task.json"
            source = ROOT / contract_rel
            target = root / contract_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            task = json.loads(source.read_text(encoding="utf-8"))
            task["public_projection"]["repository"] = "https://github.com/other-org/other-repo"
            task["public_projection"]["umbrella_issue"] = (
                "https://github.com/other-org/other-repo/issues/34"
            )
            task["public_projection"]["project"] = "https://github.com/orgs/other-org/projects/1"
            for entry in task["public_projection"]["checkpoint_issues"]:
                number = entry["issue"].rsplit("/", 1)[-1]
                entry["issue"] = f"https://github.com/other-org/other-repo/issues/{number}"
            target.write_text(json.dumps(task), encoding="utf-8")
            for schema_rel in (
                "docs/contributing/tasks/task-registry.schema.json",
                "docs/contributing/task-contract.schema.json",
            ):
                schema_path = root / schema_rel
                schema_path.parent.mkdir(parents=True, exist_ok=True)
                schema_path.write_bytes((ROOT / schema_rel).read_bytes())
            foreign = json.loads(json.dumps(registry))
            foreign["tasks"][0]["umbrella_issue"] = task["public_projection"]["umbrella_issue"]
            foreign_errors = MODULE.validate_task_registry(root, foreign, "foreign registry")
            self.assertTrue(any("canonical repository" in error for error in foreign_errors))
            self.assertTrue(
                any("canonical Task Hall Project" in error for error in foreign_errors)
            )

    def test_task_registry_rejects_duplicate_paths_and_projection_urls(self) -> None:
        registry = json.loads(
            (ROOT / "docs" / "contributing" / "tasks" / "task-registry.json").read_text(
                encoding="utf-8"
            )
        )
        live = json.loads(
            (
                ROOT
                / "docs"
                / "contributing"
                / "tasks"
                / "agent-commons-public-workbench.task.json"
            ).read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_rel = "docs/contributing/tasks/agent-commons-public-workbench.task.json"
            second_rel = "docs/contributing/tasks/second-workbench.task.json"
            for schema_rel in (
                "docs/contributing/tasks/task-registry.schema.json",
                "docs/contributing/task-contract.schema.json",
            ):
                schema_path = root / schema_rel
                schema_path.parent.mkdir(parents=True, exist_ok=True)
                schema_path.write_bytes((ROOT / schema_rel).read_bytes())

            first = json.loads(json.dumps(live))
            second = json.loads(json.dumps(live))
            second["id"] = "second-workbench-task"
            second["public_projection"]["umbrella_issue"] = (
                "https://github.com/Lingkyn/xr-foundry/issues/134"
            )
            for index, entry in enumerate(second["public_projection"]["checkpoint_issues"]):
                entry["issue"] = f"https://github.com/Lingkyn/xr-foundry/issues/{200 + index}"
            (root / first_rel).parent.mkdir(parents=True, exist_ok=True)
            (root / first_rel).write_text(json.dumps(first), encoding="utf-8")
            (root / second_rel).write_text(json.dumps(second), encoding="utf-8")

            duplicate_contract = {
                "schema": "xr-foundry.task_registry.v1",
                "coverage": {"mode": "explicit_registration"},
                "authority": registry["authority"],
                "tasks": [
                    {
                        "task_id": first["id"],
                        "contract": first_rel,
                        "umbrella_issue": first["public_projection"]["umbrella_issue"],
                        "state": first["state"],
                    },
                    {
                        "task_id": second["id"],
                        "contract": first_rel,
                        "umbrella_issue": second["public_projection"]["umbrella_issue"],
                        "state": second["state"],
                    },
                ],
            }
            contract_errors = MODULE.validate_task_registry(
                root, duplicate_contract, "duplicate contract path registry"
            )
            self.assertTrue(any("duplicate contract path" in error for error in contract_errors))

            duplicate_umbrella = json.loads(json.dumps(duplicate_contract))
            duplicate_umbrella["tasks"][1]["contract"] = second_rel
            duplicate_umbrella["tasks"][1]["umbrella_issue"] = first["public_projection"][
                "umbrella_issue"
            ]
            second_collide = json.loads(json.dumps(second))
            second_collide["public_projection"]["umbrella_issue"] = first["public_projection"][
                "umbrella_issue"
            ]
            (root / second_rel).write_text(json.dumps(second_collide), encoding="utf-8")
            umbrella_errors = MODULE.validate_task_registry(
                root, duplicate_umbrella, "duplicate umbrella registry"
            )
            self.assertTrue(any("duplicate umbrella Issue" in error for error in umbrella_errors))

            second_ok = json.loads(json.dumps(second))
            second_ok["public_projection"]["checkpoint_issues"][0]["issue"] = first[
                "public_projection"
            ]["checkpoint_issues"][0]["issue"]
            (root / second_rel).write_text(json.dumps(second_ok), encoding="utf-8")
            duplicate_checkpoint = {
                "schema": "xr-foundry.task_registry.v1",
                "coverage": {"mode": "explicit_registration"},
                "authority": registry["authority"],
                "tasks": [
                    {
                        "task_id": first["id"],
                        "contract": first_rel,
                        "umbrella_issue": first["public_projection"]["umbrella_issue"],
                        "state": first["state"],
                    },
                    {
                        "task_id": second["id"],
                        "contract": second_rel,
                        "umbrella_issue": second["public_projection"]["umbrella_issue"],
                        "state": second["state"],
                    },
                ],
            }
            checkpoint_errors = MODULE.validate_task_registry(
                root, duplicate_checkpoint, "duplicate checkpoint issue registry"
            )
            self.assertTrue(
                any("duplicate checkpoint Issue URL" in error for error in checkpoint_errors)
            )

    def test_task_registry_rejects_symlink_contracts(self) -> None:
        registry = json.loads(
            (ROOT / "docs" / "contributing" / "tasks" / "task-registry.json").read_text(
                encoding="utf-8"
            )
        )
        live = (
            ROOT
            / "docs"
            / "contributing"
            / "tasks"
            / "agent-commons-public-workbench.task.json"
        ).read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract_rel = "docs/contributing/tasks/agent-commons-public-workbench.task.json"
            for schema_rel in (
                "docs/contributing/tasks/task-registry.schema.json",
                "docs/contributing/task-contract.schema.json",
            ):
                schema_path = root / schema_rel
                schema_path.parent.mkdir(parents=True, exist_ok=True)
                schema_path.write_bytes((ROOT / schema_rel).read_bytes())
            target = root / contract_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            real_file = root / "docs" / "contributing" / "tasks" / "real-source.task.json"
            real_file.write_bytes(live)
            try:
                target.symlink_to(real_file)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable in this environment")
            symlink_errors = MODULE.validate_task_registry(
                root, registry, "symlink registry"
            )
            self.assertTrue(any("must not be a symlink" in error for error in symlink_errors))

    def test_task_registry_rejects_hardlink_contracts(self) -> None:
        registry = json.loads(
            (ROOT / "docs" / "contributing" / "tasks" / "task-registry.json").read_text(
                encoding="utf-8"
            )
        )
        live = (
            ROOT
            / "docs"
            / "contributing"
            / "tasks"
            / "agent-commons-public-workbench.task.json"
        ).read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract_rel = "docs/contributing/tasks/agent-commons-public-workbench.task.json"
            for schema_rel in (
                "docs/contributing/tasks/task-registry.schema.json",
                "docs/contributing/task-contract.schema.json",
            ):
                schema_path = root / schema_rel
                schema_path.parent.mkdir(parents=True, exist_ok=True)
                schema_path.write_bytes((ROOT / schema_rel).read_bytes())
            target = root / contract_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            hardlink_source = root / "docs" / "contributing" / "tasks" / "hardlink-source.task.json"
            hardlink_source.write_bytes(live)
            try:
                os.link(hardlink_source, target)
            except (OSError, NotImplementedError, AttributeError):
                self.skipTest("hardlinks unavailable in this environment")
            hardlink_errors = MODULE.validate_task_registry(
                root, registry, "hardlink registry"
            )
            self.assertTrue(any("must not be a hardlink" in error for error in hardlink_errors))

    def test_task_registry_rejects_tasks_directory_parent_link_escape(self) -> None:
        registry = json.loads(
            (ROOT / "docs" / "contributing" / "tasks" / "task-registry.json").read_text(
                encoding="utf-8"
            )
        )
        live = (
            ROOT
            / "docs"
            / "contributing"
            / "tasks"
            / "agent-commons-public-workbench.task.json"
        ).read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = Path(directory) / "external-tasks"
            external.mkdir(parents=True, exist_ok=True)
            (external / "agent-commons-public-workbench.task.json").write_bytes(live)
            contributing = root / "docs" / "contributing"
            contributing.mkdir(parents=True, exist_ok=True)
            tasks_link = contributing / "tasks"
            linked = False
            if os.name == "nt":
                completed = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(tasks_link), str(external)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                linked = completed.returncode == 0 and tasks_link.exists()
            if not linked:
                try:
                    tasks_link.symlink_to(external, target_is_directory=True)
                    linked = True
                except (OSError, NotImplementedError):
                    self.skipTest("parent directory junction/symlink unavailable")

            for schema_rel in (
                "docs/contributing/tasks/task-registry.schema.json",
                "docs/contributing/task-contract.schema.json",
            ):
                schema_path = root / schema_rel
                schema_path.parent.mkdir(parents=True, exist_ok=True)
                schema_path.write_bytes((ROOT / schema_rel).read_bytes())

            errors = MODULE.validate_task_registry(root, registry, "parent-link registry")
            self.assertTrue(
                any(
                    "must not be a symlink, junction, or reparse point" in error
                    or "resolves outside the repository root" in error
                    for error in errors
                ),
                errors,
            )

    def test_task_registry_resolution_errors_fail_closed(self) -> None:
        registry = json.loads(
            (ROOT / "docs" / "contributing" / "tasks" / "task-registry.json").read_text(
                encoding="utf-8"
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract_rel = "docs/contributing/tasks/agent-commons-public-workbench.task.json"
            for schema_rel in (
                "docs/contributing/tasks/task-registry.schema.json",
                "docs/contributing/task-contract.schema.json",
            ):
                schema_path = root / schema_rel
                schema_path.parent.mkdir(parents=True, exist_ok=True)
                schema_path.write_bytes((ROOT / schema_rel).read_bytes())
            target = root / contract_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(
                (
                    ROOT
                    / "docs"
                    / "contributing"
                    / "tasks"
                    / "agent-commons-public-workbench.task.json"
                ).read_bytes()
            )
            original_resolve = Path.resolve

            def boom(self: Path, *args: object, **kwargs: object):
                text = self.as_posix().replace("\\", "/")
                if text.endswith("/docs/contributing/tasks") or text.endswith(contract_rel):
                    raise OSError("simulated resolution failure")
                return original_resolve(self, *args, **kwargs)

            with mock.patch.object(Path, "resolve", boom):
                errors = MODULE.validate_task_registry(
                    root, registry, "resolution-error registry"
                )
            self.assertTrue(
                any("unreadable" in error for error in errors),
                errors,
            )

    def test_resolution_runtime_error_fail_closed_at_three_sites(self) -> None:
        registry = json.loads(
            (ROOT / "docs" / "contributing" / "tasks" / "task-registry.json").read_text(
                encoding="utf-8"
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract_rel = "docs/contributing/tasks/agent-commons-public-workbench.task.json"
            for schema_rel in (
                "docs/contributing/tasks/task-registry.schema.json",
                "docs/contributing/task-contract.schema.json",
            ):
                schema_path = root / schema_rel
                schema_path.parent.mkdir(parents=True, exist_ok=True)
                schema_path.write_bytes((ROOT / schema_rel).read_bytes())
            target = root / contract_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(
                (
                    ROOT
                    / "docs"
                    / "contributing"
                    / "tasks"
                    / "agent-commons-public-workbench.task.json"
                ).read_bytes()
            )
            original_resolve = Path.resolve
            root_resolved = root.resolve()
            tasks_resolved = (root / "docs" / "contributing" / "tasks").resolve()
            contract_resolved = target.resolve()

            def boom_repo_root(self: Path, *args: object, **kwargs: object):
                candidate = original_resolve(self, *args, **kwargs)
                if candidate == root_resolved or self == root:
                    raise RuntimeError("simulated repo-root symlink loop")
                return candidate

            with mock.patch.object(Path, "resolve", boom_repo_root):
                repo_errors = MODULE.resolve_controlled_tasks_root(
                    root, "runtime-error repo root"
                )[2]
            self.assertTrue(
                any("repository root is unreadable" in error for error in repo_errors),
                repo_errors,
            )
            with mock.patch.object(Path, "resolve", boom_repo_root):
                registry_repo_errors = MODULE.validate_task_registry(
                    root, registry, "runtime-error repo root registry"
                )
            self.assertTrue(
                any("repository root is unreadable" in error for error in registry_repo_errors),
                registry_repo_errors,
            )

            def boom_tasks_root(self: Path, *args: object, **kwargs: object):
                text = self.as_posix().replace("\\", "/")
                if text.endswith("/docs/contributing/tasks"):
                    raise RuntimeError("simulated tasks-root symlink loop")
                candidate = original_resolve(self, *args, **kwargs)
                if candidate == tasks_resolved:
                    raise RuntimeError("simulated tasks-root symlink loop")
                return candidate

            with mock.patch.object(Path, "resolve", boom_tasks_root):
                tasks_errors = MODULE.resolve_controlled_tasks_root(
                    root, "runtime-error tasks root"
                )[2]
            self.assertTrue(
                any(
                    "controlled tasks directory is unreadable" in error
                    for error in tasks_errors
                ),
                tasks_errors,
            )
            with mock.patch.object(Path, "resolve", boom_tasks_root):
                registry_tasks_errors = MODULE.validate_task_registry(
                    root, registry, "runtime-error tasks root registry"
                )
            self.assertTrue(
                any(
                    "controlled tasks directory is unreadable" in error
                    for error in registry_tasks_errors
                ),
                registry_tasks_errors,
            )

            def boom_contract(self: Path, *args: object, **kwargs: object):
                text = self.as_posix().replace("\\", "/")
                if text.endswith(contract_rel):
                    raise RuntimeError("simulated contract symlink loop")
                candidate = original_resolve(self, *args, **kwargs)
                if candidate == contract_resolved:
                    raise RuntimeError("simulated contract symlink loop")
                return candidate

            with mock.patch.object(Path, "resolve", boom_contract):
                contract_path, contract_errors = MODULE.inspect_registered_contract_path(
                    root, contract_rel, "runtime-error contract"
                )
            self.assertIsNone(contract_path)
            self.assertTrue(
                any("registered contract is unreadable" in error for error in contract_errors),
                contract_errors,
            )
            with mock.patch.object(Path, "resolve", boom_contract):
                registry_contract_errors = MODULE.validate_task_registry(
                    root, registry, "runtime-error contract registry"
                )
            self.assertTrue(
                any(
                    "registered contract is unreadable" in error
                    for error in registry_contract_errors
                ),
                registry_contract_errors,
            )

    def test_task_contract_validation_uses_target_root_schema(self) -> None:
        payload = json.loads(
            (ROOT / "docs" / "contributing" / "task-contract.example.json").read_text(
                encoding="utf-8"
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            schema_path = root / "docs" / "contributing" / "task-contract.schema.json"
            schema_path.parent.mkdir(parents=True, exist_ok=True)
            schema_path.write_text("{", encoding="utf-8")
            errors = MODULE.validate_task_contract(
                payload, "foreign-root schema", root=root
            )
            self.assertTrue(any("invalid JSON" in error or "JSON" in error for error in errors))
            self.assertFalse(
                any("canonical Task Hall umbrella lifecycle" in error for error in errors)
            )

    def test_task_hall_lifecycle_and_policies_are_machine_enforced(self) -> None:
        payload = json.loads(
            (ROOT / "docs" / "contributing" / "task-hall.v1.json").read_text(
                encoding="utf-8"
            )
        )
        lifecycle = json.loads(json.dumps(payload))
        lifecycle["lifecycle"]["umbrella_states"][2:4] = ["active", "ready"]
        lifecycle_errors = MODULE.validate_task_hall_authority(lifecycle)
        self.assertTrue(any("umbrella lifecycle" in error for error in lifecycle_errors))

        durability = json.loads(json.dumps(payload))
        durability["durability_policy"]["local_only_progress_is_non_transferable"] = False
        durability_errors = MODULE.validate_task_hall_authority(durability)
        self.assertTrue(
            any("local_only_progress_is_non_transferable" in error for error in durability_errors)
        )

        routing = json.loads(json.dumps(payload))
        routing["routing_policy"]["self_report_grants_authority"] = True
        routing["routing_policy"]["model_or_agent_ranking"] = True
        routing_errors = MODULE.validate_task_hall_authority(routing)
        self.assertTrue(any("self_report_grants_authority" in error for error in routing_errors))
        self.assertTrue(any("model_or_agent_ranking" in error for error in routing_errors))

        registry = json.loads(json.dumps(payload))
        registry["registry_policy"]["registry"] = "tmp/evil-registry.json"
        registry_errors = MODULE.validate_task_hall_authority(registry)
        self.assertTrue(any("registry='tmp/evil-registry.json'" in error or "must keep registry=" in error for error in registry_errors))

    def test_task_hall_global_authority_rejects_every_permission_escalation(self) -> None:
        source = json.loads(
            (ROOT / "docs" / "contributing" / "task-hall.v1.json").read_text(
                encoding="utf-8"
            )
        )
        violations = {
            "claim_grants_repository_write": True,
            "claim_grants_merge": True,
            "external_agent_auto_write": True,
            "external_agent_auto_merge": True,
            "maintainer_controls_ready_and_merge": False,
            "issue_comment_is_untrusted_input": False,
        }
        for field, unsafe in violations.items():
            with self.subTest(field=field):
                payload = json.loads(json.dumps(source))
                payload["authority"][field] = unsafe
                errors = MODULE.validate_task_hall_authority(payload)
                self.assertTrue(any(field in error for error in errors))

    def test_device_profiles_keep_claim_gates_and_no_capability_steps(self) -> None:
        profiles = current_device_profiles()

        self.assertTrue(profiles["pico-openxr-controller"]["claim_allowed"])
        self.assertFalse(profiles["quest-openxr-controller"]["claim_allowed"])
        self.assertFalse(profiles["vision-pro-spatial-input"]["claim_allowed"])
        self.assertTrue(
            profiles["quest-openxr-controller"]["claim_gate_issue"].endswith("/issues/29")
        )
        self.assertTrue(
            profiles["vision-pro-spatial-input"]["claim_gate_issue"].endswith("/issues/30")
        )
        for profile_id, profile in profiles.items():
            self.assertNotIn("required_checks", profile, profile_id)
            self.assertNotIn("required_scenarios", profile, profile_id)
            self.assertEqual([], MODULE.validate_device_profile(profile, profile_id))

    def test_device_plan_enforces_duration_posture_sources_and_interaction_matrix(self) -> None:
        plan = json.loads(
            (ROOT / "docs" / "device-lab" / "test-plans" / "inventory-world-space-ui-v1.json").read_text(
                encoding="utf-8"
            )
        )
        plan["execution_requirements"]["minimum_duration_seconds"] = 119
        plan["execution_requirements"]["allowed_postures"] = []
        plan["allowed_targets"][0]["required_input_source_ids"] = []
        plan["required_checks"] = [
            check
            for check in plan["required_checks"]
            if check["id"] != "right-controller-disabled-no-mutation"
        ]

        errors = MODULE.validate_capability_test_plan(
            plan, current_device_profiles(), "weak device plan"
        )

        self.assertTrue(any("at least 120" in error for error in errors))
        self.assertTrue(any("allowed_postures" in error for error in errors))
        self.assertTrue(any("unique input source IDs" in error for error in errors))
        self.assertTrue(any("interaction matrix is incomplete" in error for error in errors))

    def test_device_receipt_rejects_missing_or_forged_lock_and_evidence(self) -> None:
        payload = completed_device_lab_receipt(self)
        payload["dependency_resolution"]["lock"]["ref"] = (
            "docs/validation/evidence/missing-lock.json"
        )
        payload["dependency_resolution"]["lock"]["sha256"] = "e" * 64
        target = next(check for check in payload["checks"] if check["status"] == "pass")
        target["evidence_refs"][0]["sha256"] = "f" * 64

        errors = MODULE.validate_device_lab_execution_receipt(
            payload, current_device_profiles(), current_device_plans(), "forged files"
        )

        self.assertTrue(any("lock repository file does not exist" in error for error in errors))
        self.assertTrue(any("evidence SHA-256 does not match file" in error for error in errors))

    def test_device_receipt_rejects_dependency_input_build_and_execution_tuple_drift(self) -> None:
        payload = completed_device_lab_receipt(self)
        payload["dependency_resolution"]["resolved_packages"] = [
            package
            for package in payload["dependency_resolution"]["resolved_packages"]
            if package["id"] != "com.unity.xr.openxr"
        ]
        payload["build"]["target"] = "latest"
        payload["input"]["sources"] = [
            source for source in payload["input"]["sources"] if source["id"] != "right-controller"
        ]
        payload["execution_context"] = {"posture": "prone", "duration_seconds": 119}

        errors = MODULE.validate_device_lab_execution_receipt(
            payload, current_device_profiles(), current_device_plans(), "tuple drift"
        )

        self.assertTrue(any("plan-required resolved packages are missing" in error for error in errors))
        self.assertTrue(any("build.target must be an exact" in error for error in errors))
        self.assertTrue(any("required input sources are missing" in error for error in errors))
        self.assertTrue(any("below the plan minimum" in error for error in errors))
        self.assertTrue(any("posture is not admitted" in error for error in errors))

    def test_device_receipt_rejects_placeholder_runtime_and_os_versions(self) -> None:
        payload = completed_device_lab_receipt(self)
        payload["software"]["runtime_version"] = "recorded-runtime-version"
        payload["device"]["os_version"] = "current"

        errors = MODULE.validate_device_lab_execution_receipt(
            payload, current_device_profiles(), current_device_plans(), "placeholder versions"
        )

        self.assertTrue(any("exact dotted runtime version" in error for error in errors))
        self.assertTrue(any("exact dotted OS version" in error for error in errors))

    def test_not_tested_template_is_not_an_execution_receipt(self) -> None:
        payload = json.loads(
            (ROOT / "docs" / "device-lab" / "device-receipt.template.json").read_text(
                encoding="utf-8"
            )
        )

        errors = MODULE.validate_device_lab_execution_receipt(
            payload,
            current_device_profiles(),
            current_device_plans(),
            "blank receipt",
        )

        self.assertTrue(any("not an execution receipt" in error for error in errors))

    def test_revision_bound_device_execution_receipt_is_admissible(self) -> None:
        self.assertEqual(
            [],
            MODULE.validate_device_lab_execution_receipt(
                completed_device_lab_receipt(self),
                current_device_profiles(),
                current_device_plans(),
                "revision-bound pass",
            ),
        )

    def test_device_receipt_rejects_local_only_revision_with_public_tree(self) -> None:
        payload = completed_device_lab_receipt(self)
        public_commit = payload["revision"]["commit_sha"]
        tree = subprocess.check_output(
            ["git", "rev-parse", f"{public_commit}^{{tree}}"], cwd=ROOT, text=True
        ).strip()
        payload["revision"]["commit_sha"] = subprocess.check_output(
            [
                "git",
                "-c",
                "user.name=XR Foundry Contract Test",
                "-c",
                "user.email=xr-foundry-contract-test@example.invalid",
                "commit-tree",
                tree,
            ],
            cwd=ROOT,
            input="device local-only evidence object\n",
            text=True,
        ).strip()

        errors = MODULE.validate_device_lab_execution_receipt(
            payload, current_device_profiles(), current_device_plans(), "local-only device"
        )

        self.assertTrue(any("fetched public origin ref" in error for error in errors))

    def test_device_receipt_rejects_unbound_revision_and_artifact(self) -> None:
        payload = completed_device_lab_receipt(self)
        payload["revision"]["commit_sha"] = None
        payload["artifact"] = {
            "kind": "android-apk",
            "file_name": "missing.apk",
            "sha256": None,
            "repository_path": None,
            "application_id": None,
        }

        errors = MODULE.validate_device_lab_execution_receipt(
            payload, current_device_profiles(), current_device_plans(), "unbound execution"
        )

        self.assertTrue(any("full 40-character commit SHA" in error for error in errors))
        self.assertTrue(any("artifact SHA-256" in error for error in errors))
        self.assertTrue(any("artifact.repository_path" in error for error in errors))
        self.assertTrue(any("artifact.application_id" in error for error in errors))

    def test_device_receipt_rejects_fake_or_lfs_pointer_artifact(self) -> None:
        payload = completed_device_lab_receipt(self)
        artifact_path = ROOT / payload["artifact"]["repository_path"]
        artifact_path.write_text(
            "version https://git-lfs.github.com/spec/v1\n"
            "oid sha256:" + "a" * 64 + "\nsize 123\n",
            encoding="utf-8",
        )
        payload["artifact"]["sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()

        errors = MODULE.validate_device_lab_execution_receipt(
            payload, current_device_profiles(), current_device_plans(), "lfs artifact"
        )

        self.assertTrue(any("materialized, not a Git LFS pointer" in error for error in errors))

    def test_device_receipt_rejects_fake_pk_bytes_and_missing_manifest(self) -> None:
        for mutation in ("fake-pk", "missing-manifest", "prefixed-zip"):
            with self.subTest(mutation=mutation):
                payload = completed_device_lab_receipt(self)
                artifact_path = ROOT / payload["artifact"]["repository_path"]
                if mutation == "fake-pk":
                    artifact_path.write_bytes(b"PK\x03\x04not-a-zip")
                elif mutation == "prefixed-zip":
                    original = artifact_path.read_bytes()
                    artifact_path.write_bytes(b"MZ-prefixed-polyglot" + original)
                else:
                    with zipfile.ZipFile(
                        artifact_path, "w", compression=zipfile.ZIP_DEFLATED
                    ) as archive:
                        archive.writestr("classes.dex", b"dex\n035\x00" + b"\x00" * 112)
                        archive.writestr(
                            "lib/arm64-v8a/libunity.so", b"\x7fELFunity"
                        )
                        archive.writestr(
                            "lib/arm64-v8a/libil2cpp.so", b"\x7fELFil2cpp"
                        )
                        archive.writestr(
                            "assets/bin/Data/globalgamemanagers", b"unity-player-data"
                        )
                payload["artifact"]["sha256"] = hashlib.sha256(
                    artifact_path.read_bytes()
                ).hexdigest()

                errors = MODULE.validate_device_lab_execution_receipt(
                    payload,
                    current_device_profiles(),
                    current_device_plans(),
                    f"{mutation} artifact",
                )

                marker = {
                    "fake-pk": "valid APK ZIP",
                    "missing-manifest": "must contain exactly one AndroidManifest.xml",
                    "prefixed-zip": "must begin with a ZIP local-file header",
                }[mutation]
                self.assertTrue(any(marker in error for error in errors), errors)

    def test_device_receipt_application_id_must_match_binary_manifest(self) -> None:
        payload = completed_device_lab_receipt(self)
        payload["artifact"]["application_id"] = "com.example.different"

        errors = MODULE.validate_device_lab_execution_receipt(
            payload, current_device_profiles(), current_device_plans(), "application drift"
        )

        self.assertTrue(any("must equal the APK manifest package ID" in error for error in errors))

    def test_device_receipt_rejects_renderer_xr_adapter_mismatch(self) -> None:
        payload = completed_device_lab_receipt(self)
        payload["package_tuple"]["xr_adapter"]["id"] = "com.lingkyn.inventory.xr.uitoolkit"

        errors = MODULE.validate_device_lab_execution_receipt(
            payload, current_device_profiles(), current_device_plans(), "mismatched adapter"
        )

        self.assertTrue(any("xr_adapter does not match" in error for error in errors))

    def test_device_receipt_rejects_runtime_device_and_input_mismatch(self) -> None:
        payload = completed_device_lab_receipt(self)
        payload["software"]["runtime_id"] = "openxr-meta-quest"
        payload["device"]["family_id"] = "quest-standalone-family"
        payload["input"]["routes"] = ["gaze-and-pinch"]

        errors = MODULE.validate_device_lab_execution_receipt(
            payload, current_device_profiles(), current_device_plans(), "mismatched profile"
        )

        self.assertTrue(any("runtime_id does not match" in error for error in errors))
        self.assertTrue(any("device family does not match" in error for error in errors))
        self.assertTrue(any("input routes do not match" in error for error in errors))

    def test_device_receipt_rejects_untested_required_check(self) -> None:
        payload = completed_device_lab_receipt(self)
        target = next(
            check
            for check in payload["checks"]
            if check["id"] == "left-controller-left-target-activate"
        )
        target.update({"status": "not_tested", "observation": "", "evidence_refs": []})

        errors = MODULE.validate_device_lab_execution_receipt(
            payload, current_device_profiles(), current_device_plans(), "untested required check"
        )

        self.assertTrue(any("required check cannot remain not_tested" in error for error in errors))

    def test_device_receipt_rejects_unsupported_optional_claim(self) -> None:
        payload = completed_device_lab_receipt(self)
        claim = next(item for item in payload["optional_claims"] if item["id"] == "direct-poke")
        claim["supported"] = True

        errors = MODULE.validate_device_lab_execution_receipt(
            payload, current_device_profiles(), current_device_plans(), "unsupported optional claim"
        )

        self.assertTrue(any("lacks a passed check" in error for error in errors))
        self.assertTrue(any("not admitted by profile" in error for error in errors))

    def test_device_receipt_rejects_profile_with_claim_disabled(self) -> None:
        payload = completed_device_lab_receipt(self)
        payload["device_profile_id"] = "quest-openxr-controller"
        payload["software"]["runtime_id"] = "openxr-meta-quest"
        payload["device"].update(
            {
                "family_id": "quest-standalone-family",
                "model": "Meta Quest 3",
                "os_family": "Meta Horizon OS",
            }
        )

        errors = MODULE.validate_device_lab_execution_receipt(
            payload, current_device_profiles(), current_device_plans(), "disabled profile claim"
        )

        self.assertTrue(any("claim_allowed=false" in error for error in errors))

    def test_device_receipt_rejects_free_text_or_cross_composition_claims(self) -> None:
        payload = completed_device_lab_receipt(self)
        payload["claims_supported"] = ["works-on-every-xr-headset"]
        payload["claims_not_supported"].remove("inventory-ui-toolkit-xr-required-suite")

        errors = MODULE.validate_device_lab_execution_receipt(
            payload, current_device_profiles(), current_device_plans(), "invented claim"
        )

        self.assertTrue(any("not enumerated by the plan" in error for error in errors))
        self.assertTrue(any("claims_supported must equal derived claim IDs" in error for error in errors))
        self.assertTrue(any("claims_not_supported must enumerate" in error for error in errors))

    def test_device_receipt_result_is_derived_from_required_checks(self) -> None:
        payload = completed_device_lab_receipt(self)
        payload["overall_result"] = "fail"
        payload["claims_supported"] = []
        payload["claims_not_supported"] = [
            "inventory-ugui-xr-required-suite",
            "inventory-ui-toolkit-xr-required-suite",
            "direct-poke",
            "hand-ray",
            "gaze-and-pinch",
        ]

        errors = MODULE.validate_device_lab_execution_receipt(
            payload, current_device_profiles(), current_device_plans(), "false failure"
        )

        self.assertTrue(any("required-check result=pass" in error for error in errors))

    def test_device_receipt_rejects_unbound_version_evidence_and_time(self) -> None:
        payload = completed_device_lab_receipt(self)
        payload["package_tuple"]["domain"]["version"] = "latest"
        target = next(check for check in payload["checks"] if check["id"] == "artifact-install")
        target["evidence_refs"] = [
            {
                "kind": "repository_file",
                "ref": "../private/evidence.txt",
                "sha256": "0" * 64,
            }
        ]
        payload["timestamps"] = {
            "started_at": "2026-07-15T12:05:00Z",
            "completed_at": "2026-07-15T12:00:00Z",
        }

        errors = MODULE.validate_device_lab_execution_receipt(
            payload, current_device_profiles(), current_device_plans(), "unbound evidence"
        )

        self.assertTrue(any("exact semantic version" in error for error in errors))
        self.assertTrue(any("repository evidence path is unsafe" in error for error in errors))
        self.assertTrue(any("evidence ref requires non-zero SHA-256" in error for error in errors))
        self.assertTrue(any("completed_at must not precede" in error for error in errors))

    def test_workflow_security_rejects_comment_trigger_and_unpinned_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "unsafe.yml").write_text(
                """name: Unsafe\non:\n  issue_comment:\npermissions:\n  contents: read\njobs:\n  run:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v6\n""",
                encoding="utf-8",
            )

            errors = MODULE.validate_workflow_security(root)

            self.assertTrue(any("comment-trigger workflows are forbidden" in error for error in errors))
            self.assertTrue(any("must use a full commit SHA" in error for error in errors))

    def test_workflow_security_parses_quoted_triggers_and_inline_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "unsafe.yml").write_text(
                """name: Unsafe\n"on":\n  "pull_request_target":\npermissions: {contents: write}\njobs:\n  run:\n    permissions: {issues: write}\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n        with: {persist-credentials: "false"}\n""",
                encoding="utf-8",
            )

            errors = MODULE.validate_workflow_security(root)

            self.assertTrue(any("pull_request_target" in error for error in errors))
            self.assertTrue(any("workflow-level permission" in error for error in errors))
            self.assertTrue(any("job 'run' permission" in error for error in errors))
            self.assertTrue(any("YAML boolean" in error for error in errors))

    def test_workflow_security_requires_explicit_top_level_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "missing.yml").write_text(
                """name: Missing permissions\non: [pull_request]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps: []\n""",
                encoding="utf-8",
            )

            errors = MODULE.validate_workflow_security(root)

            self.assertTrue(any("workflow-level permissions must be an explicit mapping" in error for error in errors))

    def test_repository_automation_contract_accepts_current_configuration(self) -> None:
        self.assertEqual([], MODULE.validate_repository_automation_contract(ROOT))

    def test_repository_automation_contract_rejects_matrix_and_dependabot_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "validate.yml").write_text(
                """name: Validate packages
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  python-contract-matrix:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    strategy:
      matrix:
        python-version: [\"3.12\"]
    steps:
      - uses: actions/checkout@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        with:
          persist-credentials: false
          fetch-depth: 1
      - uses: actions/setup-python@bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
        with:
          python-version: \"3.12\"
      - run: python scripts/validate_repository.py --json
  repository-contract:
    name: repository-contract
    if: ${{ always() }}
    needs: python-contract-matrix
    runs-on: ubuntu-latest
    timeout-minutes: 2
    permissions:
      contents: none
    steps:
      - env:
          CONTRACT_MATRIX_RESULT: ${{ needs.python-contract-matrix.result }}
        run: exit 0
""",
                encoding="utf-8",
            )
            (root / ".github" / "dependabot.yml").write_text(
                """version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: monthly
    open-pull-requests-limit: 5
""",
                encoding="utf-8",
            )

            errors = MODULE.validate_repository_automation_contract(root)

            self.assertTrue(any("missing required triggers" in error for error in errors))
            self.assertTrue(any("Python matrix must equal" in error for error in errors))
            self.assertTrue(any("fetch full history" in error for error in errors))
            self.assertTrue(any("canonical full validation command" in error for error in errors))
            self.assertTrue(any("matrix passes" in error for error in errors))
            self.assertTrue(any("one pip update entry" in error for error in errors))

    def test_public_leakage_scan_covers_all_decodable_text_and_skips_binary(self) -> None:
        marker = "vr" + "soundscape"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            suffixes = [".py", ".uxml", ".uss", ".asset", ""]
            for index, suffix in enumerate(suffixes):
                (root / f"surface-{index}{suffix}").write_text(marker, encoding="utf-8")
            (root / "binary.asset").write_bytes(b"\x00\xff" + marker.encode("utf-8"))
            git_dir = root / ".git"
            git_dir.mkdir()
            (git_dir / "ignored").write_text(marker, encoding="utf-8")

            errors = MODULE.scan_text_safety(root)

            leak_paths = [error for error in errors if "non-public marker" in error]
            self.assertEqual(len(suffixes), len(leak_paths))
            self.assertFalse(any("binary.asset" in error for error in errors))
            self.assertFalse(any(".git" in error for error in errors))

    def test_public_leakage_scan_rejects_undecodable_controlled_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "undecodable.md").write_bytes(b"public contract \x96 invalid utf-8")

            errors = MODULE.scan_text_safety(root)

            self.assertTrue(
                any("undecodable controlled text file: undecodable.md" in error for error in errors)
            )

    def test_namespace_contract_admits_attribute_only_assembly_info(self) -> None:
        source = (
            "using System.Runtime.CompilerServices;\n\n"
            '[assembly: InternalsVisibleTo("Lingkyn.Example.Editor.Tests")]\n'
        )

        self.assertTrue(
            MODULE.source_has_valid_namespace_contract("AssemblyInfo.cs", source)
        )
        self.assertFalse(
            MODULE.source_has_valid_namespace_contract("Other.cs", source)
        )

    def test_namespace_contract_rejects_types_hidden_in_assembly_info(self) -> None:
        source = (
            "using System.Runtime.CompilerServices;\n"
            '[assembly: InternalsVisibleTo("Lingkyn.Example.Editor.Tests")]\n'
            "internal sealed class HiddenType {}\n"
        )

        self.assertFalse(
            MODULE.source_has_valid_namespace_contract("AssemblyInfo.cs", source)
        )


if __name__ == "__main__":
    unittest.main()
