# Lingkyn Persistence Core

`com.lingkyn.persistence.core` provides a Unity-engine-light save orchestration
kernel. Its namespaces start with `Lingkyn.Persistence.Core`. It contains:

- deterministic binary save envelope encoding/decoding with strict bounds;
- validated slot identifiers and stable stage/error results;
- integrity abstraction with SHA-256 implementation;
- deterministic migration pipeline with explicit rejection paths; and
- capability-declared opaque store contract with fail-closed coordinator behavior.

The package intentionally excludes storage backends, Unity adapter code, UI, cloud,
encryption, and project-specific configuration. See the package `README.md` for
the full public surface.

New Unity consumers can use the
[Persistence quickstart](https://github.com/Lingkyn/xr-foundry/blob/main/docs/standards/persistence/quickstart.md)
for a pinned Core + Unity install, asset configuration, runnable caller, and
save/load smoke procedure. The receipt history and current-source behavior have
different revision boundaries; the guide identifies both.

## Save pipeline

`SaveCoordinator<TState>.Save(slotId, snapshot, cancellationToken)` runs the
`Snapshot`, `Encode`, `Integrity`, `StageWrite`, `Flush`, and `Commit` stages
through the injected `ISaveCodec<TState>`, `IIntegrityProvider`, and `ISaveStore`,
and returns a `SaveCommitResult`.

- `Committed` is true only after the store reports a durable commit.
- `PriorCommittedRecordPreserved` reports whether the previous committed record
  survived a failed replacement, as the store declared it.
- A codec, integrity provider, or store exception is captured as a
  `ProviderFailure` at the stage where it happened instead of propagating.
- The coordinator compares the store's advertised `SaveCommitCapabilities` with
  its own required capabilities before commit and fails with
  `UnsupportedCommitCapability` on a mismatch. It never downgrades a capability
  claim silently.
- Cancellation is checked immediately before commit and reported as `Cancelled`.
- Registered `ISaveCommitObserver<TState>` instances run only after a durable
  commit and receive the slot id, snapshot, and envelope bytes.

## Load pipeline

`LoadValidated(slotId, validator)` runs `Read`, `Envelope`, `Verify`, `Decode`,
`Migrate`, and `Validate`, then returns a `SaveLoadReceipt<TState>` that carries
the state, the selected candidate kind and id, whether recovery occurred, and the
primary failure diagnostic when a backup was used. `LoadAndApply` adds the
consumer's `Apply` step. Every stage fails closed: a malformed envelope, schema id
mismatch, digest mismatch, rejected migration, or validator rejection returns a
`SaveResult` with the failing `SaveStage` and `SaveErrorCode` rather than a
partial state.

## Recovery policy

`ISaveStore.ReadCandidates` returns a `SaveReadCandidateSet` of `Primary`,
`Backup`, and `Staging` candidates. `SaveRecoveryCandidateSelector` applies the
coordinator's `SaveRecoveryPolicy`:

| Policy | Behavior |
| --- | --- |
| `PrimaryOnly` (default) | Only the primary candidate may load; a missing or rejected primary is the load error |
| `PrimaryThenBackup` | A primary that is missing, has an unsupported envelope, or fails integrity verification falls through to the backup; the receipt records `RecoveryOccurred` and the primary diagnostic |

Only those three primary failures are eligible for backup recovery. Staging
candidates are never promoted by Core policy. Duplicate or structurally ambiguous
candidates are rejected before selection. A zero-byte candidate is classified as a
malformed envelope so the primary corruption diagnostic survives backup recovery.

## Migration rules

`MigrationPipeline<TState>` is built from `ISaveMigration<TState>` edges
(`FromVersion`, `ToVersion`, `Migrate`). Graph construction and traversal reject:

- an edge whose `ToVersion` is not greater than its `FromVersion`
  (`NonMonotonicMigration`, which takes precedence over other graph errors);
- two edges that start from the same version (`AmbiguousMigration`);
- a stored version newer than the target version (`FutureSchema`);
- a missing edge on the path to the target version (`MissingMigration`);
- an edge that jumps past the target version (`OvershootMigration`); and
- a traversal that revisits a version (`CyclicMigration`, a defensive fallback).

An invalid graph fails every migration at the `Migrate` stage; a pipeline with no
edges is valid only when the stored and target versions already match.

## Commit capabilities

`SaveCommitCapabilities` is a flag set of `BestEffortWrite`, `RecoverableReplace`,
and `AtomicReplace`. A store advertises what it can prove for its exact tuple; a
coordinator requires a minimum. The Unity adapter documents which local-file
strategies advertise which flags. Core never infers atomicity from a platform
name.

## Sample

Import the `BasicPersistence` sample and call `BasicPersistenceExample.Run()`. It
saves a text state into an in-memory store, then loads it through one schema
migration and validation without a scene or any `UnityEngine` API.
