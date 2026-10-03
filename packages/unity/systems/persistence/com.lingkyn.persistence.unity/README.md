# Lingkyn Persistence Unity

Incubating Unity adapter for `com.lingkyn.persistence.core`.

**[Install and save your first DTO](https://github.com/Lingkyn/xr-foundry/blob/main/docs/standards/persistence/quickstart.md).**
The quickstart includes both pinned package dependencies, configuration that
allows a first save, a complete consumer script, save location, recovery/reset
steps, and the exact historical Windows Editor evidence. It needs no other
XR Foundry family.

## Claim ceiling

This package proves only what its exact consumer tuple validates:

- ScriptableObject authoring for schema id/version, safe path policy, migration-edge shape, integrity provider, and required commit capability.
- JsonUtility encoding for explicitly supported plain DTO snapshots.
- Local-file staging, flush, commit, backup, and recovery inspection under a persistent-data root policy.
- EditMode tests with injected temporary directories and file-operation fault seams.

It does **not** claim crash durability, mobile/device behavior, cloud sync, authentication, encryption, cross-version release support, or catalog maturity.

## Consumer wiring

1. Create a `PersistenceUnityConfig` asset with **Create > Lingkyn > Persistence > Unity Config**. For a first save, use `RecoverableCopyReplace` with required capability `RecoverableReplace`, a dedicated storage subdirectory, and empty migration edges when no migration is needed. See the quickstart for all field values.
2. Freeze consumer-owned plain DTO snapshots: concrete `[Serializable]` types with explicitly serialized fields only (public fields or `[SerializeField]`). Require strict UTF-8 payloads at decode. Unsupported shapes fail closed, including `UnityEngine.Object`, dictionaries, delegates, generic/polymorphic roots, cyclic graphs, and readonly serialized fields.
3. Build `JsonUtilitySaveCodec<TState>` and consumer migrations implementing `ISaveMigration<TState>`.
4. Create a coordinator through `PersistenceUnityFactory.CreateCoordinator(...)` with `PersistentDataRootProvider` or an injected test root.
5. Call `SaveCoordinator<TState>.Save` / `LoadValidated` / `LoadAndApply`; let Core decide recovery between primary and backup. Staging is exposed for inspection only and is never promoted by Core policy.

## Capability semantics

- `AtomicReplace` is advertised only when the configured strategy uses supported `File.Replace` semantics with backup preconditions on replacement commits.
- Initial create commits use staged move semantics. `AtomicReplace` fails closed when no primary exists yet.
- Required commit capabilities are a minimum gate; the configured strategy selects the commit algorithm.
- `RecoverableReplace` and `BestEffortWrite` are separate, conservative claims. Preservation is verified when expected prior-primary bytes survive in either the primary or backup path after failure.

See `Samples~/LocalFilePersistence` for a minimal DTO snapshot and coordinator wiring example.
