# Persistence package-family standard

Status: implemented, incubating; released in `unity-next-systems-v0.1.0`

Implementation Issue: [#54](https://github.com/Lingkyn/xr-foundry/issues/54)

**Start here: [install Persistence and save your first DTO](quickstart.md).**
The walkthrough installs only Persistence Core and its Unity local-file adapter,
shows the complete consumer script and configuration, and separates recorded
Windows Editor evidence from the smoke run you perform in your own project.

This standard defines reusable save-data mechanics, not the game-specific state
that a title chooses to save. It is derived only from the positive public sources
in [`source-manifest.json`](source-manifest.json). Consumer/private projects,
course work, private prompts, and previously improvised save code are excluded
from derivation material.

## Capability boundary

The family separates:

- immutable domain snapshots supplied by consumers;
- a versioned persistence envelope;
- replaceable payload codecs;
- deterministic, explicit migrations;
- integrity verification;
- replaceable storage providers and declared commit capabilities;
- orchestration that validates everything before returning a load candidate; and
- consumer-controlled application of the candidate to live state.

The family does not decide which gameplay state is authoritative, serialize a live
scene graph, mutate authored ScriptableObject assets, provide a save-slot UI, sync
cloud accounts, resolve multiplayer authority, or claim encryption/tamper
resistance.

## Package boundary

The released packages are `com.lingkyn.persistence.core` and
`com.lingkyn.persistence.unity`, both version `0.1.0` and still `incubating`.
The [release record](../../releases/unity-next-systems-v0.1.0.md) documents the
immutable batch. The engine-light Core and thin Unity adapter have these roles:

| Layer | Owns | Must not own |
| --- | --- | --- |
| Engine-light Core | envelopes, codecs, integrity contracts, migrations, storage capabilities, save/load orchestration and structured results | Unity types, file paths, scenes, UI, cloud SDKs, platform assumptions |
| Unity adapter | Unity-compatible JSON DTO codec, `persistentDataPath` path policy, local file provider and ScriptableObject configuration | domain snapshot selection, live-object serialization, universal atomicity/security claims |

## Evidence boundary

An Editor test can prove deterministic orchestration and one concrete file-provider
tuple. It cannot prove Android/iOS/WebGL/tvOS/console behavior, crash durability,
cloud synchronization, security, or every Unity version. Unsupported atomic file
replacement must be reported as a capability failure or a separately named weaker
commit mode; it must never inherit an `atomic` claim.

See also:

- [`api-surface.md`](api-surface.md) (public API inventory for the compatibility review)
- [`architecture-contract.md`](architecture-contract.md)
- [`coverage-matrix.md`](coverage-matrix.md)
- [`persistence-standard.json`](persistence-standard.json)
- [`verification-contract.md`](verification-contract.md)

## Coverage record

[`coverage-map.json`](coverage-map.json) maps every clause of the Core and Unity
adapter gates in the verification contract to named tests and lists the tests still
missing. An unmapped or partial clause is an open gap, not implied coverage, and the
map is not execution evidence.
