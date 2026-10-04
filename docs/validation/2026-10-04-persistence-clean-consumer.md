# Persistence clean consumer preparation

## Purpose and boundary

The first consumer walkthrough previously required manually copying a long C#
caller and three dependency entries. The materializer now extracts those exact
canonical blocks from `docs/standards/persistence/quickstart.md` into a new
external directory. It adds the guide's Editor version and a hash receipt, and
refuses to replace an existing project. It neither embeds a second copy of the
packages nor resolves their Git dependencies.

This record establishes reproducible preparation and a source-level dependency
closure check. Unity package resolution, Editor import/compilation, scene/config
creation, save/load/restart/backup execution, and player/device behavior remain
unexecuted. `prepared_only` is not an installation or compatibility receipt.

## Reproduce preparation

From the repository checkout, with Python and Git available:

```bash
python scripts/materialize_persistence_quickstart.py --output ../persistence-clean-consumer
python -m unittest discover -s tests -p test_materialize_persistence_quickstart.py -v
```

Inspect `fixture-receipt.json` in the output. The prepared project contains the
canonical Git manifest, the complete caller, `ProjectVersion.txt`, and the guide.
It deliberately has no generated `packages-lock.json`, scene, config asset, or
runtime result. An existing output directory is rejected before any write;
choose a different directory to prepare another fixture. A filesystem error may
leave partial output, which is also refused on retry. Inspect and retain it until
you decide whether to remove it. Files are emitted as UTF-8 bytes with LF newlines
so recorded digests match on Windows as well as Unix hosts.

The generated caller SHA-256 was
`3c44a660288ecc613345699751b72aec43ac496f97d9a3a5720189b1e2686e55`, identical to
the caller in the [previous static compiler record](2026-10-03-persistence-consumer-entry.md).
That identity preserves the earlier narrow evidence; no compiler or Editor was
run for this preparation check.

## Immutable package source inspection

The two Git selectors were inspected at
`1b67c092b8c0f38e3c4fcf0b040a8807c97e701e`. Both paths contain `package.json`
with their expected package names and version `0.1.0`. Core declares no package
dependencies. Unity declares Core `0.1.0`, matched by the explicit sibling Git
selector at the same revision. The fixture also directly requests JSON Serialize
`1.0.0`. This checks the selected repository manifests, not Unity's dependency
solver or the availability/behavior of its built-in module on another tuple.

Package manifest SHA-256 values:

- Core: `de677fae40853c72ed7d317de5bc11da5a2fd765141f7e49484781e6f1758172`
- Unity: `901e979366a1bda8f94ee5e1d02cec79770da85aa2133d9a8ed20a694065996d`

To independently inspect the manifests from an authorized clone containing the
release commit:

```bash
git show 1b67c092b8c0f38e3c4fcf0b040a8807c97e701e:packages/unity/systems/persistence/com.lingkyn.persistence.core/package.json
git show 1b67c092b8c0f38e3c4fcf0b040a8807c97e701e:packages/unity/systems/persistence/com.lingkyn.persistence.unity/package.json
```

## Next required consumer evidence

Open the fixture with the guide's recorded Editor version. Preserve Unity's real
resolved lock and compilation logs, then execute the guide's first save, restart
load, backup selection, and missing-slot procedures with the exact host tuple.
The fixture does not pre-fill a passing receipt or elevate an unmatched host to a
verified profile. An unavailable Editor/license or execution permission remains
a blocker for that stage, not a reason to substitute source checks for runtime
results.
