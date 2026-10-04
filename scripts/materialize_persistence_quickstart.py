"""Prepare the documented Git-based consumer; never resolve or launch Unity."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/standards/persistence/quickstart.md"
PACKAGE_PREFIX = "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/persistence/"


def block(text: str, language: str) -> str:
    blocks = re.findall(r"^```" + language + r"\n(.*?)^```\s*$", text, re.MULTILINE | re.DOTALL)
    if len(blocks) != 1:
        raise ValueError(f"guide must contain exactly one {language} block")
    return blocks[0]


def prepare(guide: str) -> tuple[str, str, str]:
    manifest_text = block(guide, "json")
    script = block(guide, "csharp")
    manifest = json.loads(manifest_text)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("dependencies"), dict):
        raise ValueError("guide manifest must contain a dependencies object")
    dependencies = manifest["dependencies"]
    ids = ("com.lingkyn.persistence.core", "com.lingkyn.persistence.unity")
    if set(dependencies) != {*ids, "com.unity.modules.jsonserialize"}:
        raise ValueError("guide must describe only the two Persistence packages and JSON Serialize")
    pins = []
    for package_id in ids:
        selector = dependencies[package_id]
        if not isinstance(selector, str):
            raise ValueError(f"{package_id} selector must be a string")
        match = re.fullmatch(re.escape(PACKAGE_PREFIX + package_id) + r"#([0-9a-f]{40})", selector)
        if not match:
            raise ValueError(f"{package_id} requires its canonical Git path and full immutable SHA")
        pins.append(match[1])
    if pins[0] != pins[1]:
        raise ValueError("Persistence package revisions differ")
    if dependencies["com.unity.modules.jsonserialize"] != "1.0.0":
        raise ValueError("unexpected JSON Serialize version; review the consumer tuple")
    if not re.search(r"public sealed class PersistenceQuickstart\s*:\s*MonoBehaviour", script):
        raise ValueError("guide is missing the PersistenceQuickstart component")
    return manifest_text, script, pins[0]


def materialize(output: Path) -> dict:
    output = output.expanduser().resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("output must be outside the XR Foundry repository")
    if output.exists():
        raise ValueError("output already exists; choose a new disposable directory")
    guide = GUIDE.read_text(encoding="utf-8")
    manifest, script, pin = prepare(guide)
    # This is the walkthrough's historical Editor version, not a new support claim.
    version_matches = re.findall(r"Unity Editor \*\*([0-9]+\.[0-9]+\.[0-9]+[abfp][0-9]+)\*\*", guide)
    if len(version_matches) != 1:
        raise ValueError("guide must identify exactly one Editor version")
    files = {
        "Packages/manifest.json": manifest,
        "Assets/PersistenceQuickstart.cs": script,
        "ProjectSettings/ProjectVersion.txt": f"m_EditorVersion: {version_matches[0]}\n",
        "README.md": "# Disposable Persistence consumer\n\nPrepared only; Unity has not resolved, compiled, or run this project.\n"
        "Open with the recorded Editor version, wait for Package Manager, then\n"
        "follow the accompanying GUIDE.md from step 3 to create the config asset\n"
        "and scene. No scene or config asset is generated, and nothing saves\n"
        "automatically. Retain the generated packages-lock.json after resolution.\n",
        "GUIDE.md": guide,
    }
    receipt = {
        "schema": "xr-foundry.persistence_quickstart_fixture.v1",
        "status": "prepared_only",
        "package_revision": pin,
        "editor_version": version_matches[0],
        "guide_sha256": hashlib.sha256(guide.encode()).hexdigest(),
        "files_sha256": {name: hashlib.sha256(value.encode()).hexdigest() for name, value in files.items()},
        "unity_resolution": "not_run", "unity_compilation": "not_run", "runtime_smoke": "not_run",
    }
    output.mkdir(parents=True, exist_ok=False)
    for name, value in files.items():
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(value.encode("utf-8"))
    (output / "fixture-receipt.json").write_bytes((json.dumps(receipt, indent=2) + "\n").encode("utf-8"))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = materialize(args.output)
    except (ValueError, OSError, TypeError) as error:
        print(json.dumps({"status": "fail", "error": str(error)}))
        return 1
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
