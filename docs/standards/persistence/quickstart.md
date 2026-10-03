# Persistence: install and save a DTO

This walkthrough saves `{ level: 3, checkpoint: "town-square" }` to a local file,
loads and validates it, and reports which file supplied the result. It uses the
public API in the incubating `0.1.0` Core and Unity packages. No other XR Foundry
family, scene framework, or XR setup is needed.

## 1. Check the evidence boundary

The recorded profiles are
[`unity-6000.3-persistence-core-windows-editor`](../../validation/evidence/unity-6000.3-persistence-core-windows-editor/compatibility-receipt.json)
and
[`unity-6000.3-persistence-unity-windows-editor`](../../validation/evidence/unity-6000.3-persistence-unity-windows-editor/compatibility-receipt.json).
Their exact tuple is Unity Editor **6000.3.19f1**, Windows host **10.0.26200**,
`WindowsEditor`, `Mono`, `x86_64`, and graphics API `Null` (batch execution).
Renderer, XR provider/runtime, and input routes are `not_applicable`.
The test consumers request Test Framework `1.6.0` and resolve NUnit `2.0.5`,
IMGUI `1.0.0`, and JSON Serialize `1.0.0`.

Those receipts record Editor compilation and EditMode tests only: 49 passing
tests for the Core consumer at `469f69a6899508e0978f9bb7bcccf7e74878429e`, and
79 total passing tests in the combined Core + Unity consumer at
`4a2f358000b9704700f8f90e1a15907938bb2ce4`. The latter total is not 79 Unity-only
tests. Neither receipt executes this new walkthrough or its Play Mode menus.

The release pin below is the commit of
[`unity-next-systems-v0.1.0`](../../releases/unity-next-systems-v0.1.0.md).
Its Persistence runtime sources match the recorded combined consumer's runtime
sources. This guide's pin, signatures, defaults, and file behavior were checked
against source; that check is not a fresh Unity compile, test, or interactive
smoke result. A separate [static compiler check](../../validation/2026-10-03-persistence-consumer-entry.md)
compiled the script against both release and current APIs; it did not launch the
Editor or run the script. Follow the steps below to obtain your own smoke result.

The packages' `"unity": "6000.0"` manifests do not establish a tested Unity
version range. Other Unity versions, operating systems, renderers, dependency
locks, graphics APIs, backends, architectures, and device tuples remain
unverified. There is no player-build, headset, mobile, console, WebGL, cloud,
crash-durability, encryption, or authentication claim. For an unmatched tuple,
take the [target-specific raw-material route](#using-an-unmatched-tuple).

## 2. Install both packages at the same commit

Use a disposable Unity project for the walkthrough, with Git available to Unity
Package Manager. Merge these entries into the `dependencies` object of your
project's `Packages/manifest.json`; preserve the project's other entries:

```json
{
  "dependencies": {
    "com.lingkyn.persistence.core": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/persistence/com.lingkyn.persistence.core#1b67c092b8c0f38e3c4fcf0b040a8807c97e701e",
    "com.lingkyn.persistence.unity": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/persistence/com.lingkyn.persistence.unity#1b67c092b8c0f38e3c4fcf0b040a8807c97e701e",
    "com.unity.modules.jsonserialize": "1.0.0"
  }
}
```

JSON Serialize supplies `JsonUtility`; keep the entry if your template already
contains it. The Unity adapter's Core dependency is a package version, not a
second Git URL, so add **both** sibling selectors explicitly. Both must stay on
the same full SHA. A branch name is not an immutable pin.

Let Package Manager finish resolving. Confirm both Lingkyn Persistence packages
show version `0.1.0`, then inspect `Packages/packages-lock.json` for the two Git
entries and the requested full revision. Keep that lock with your project.
If Core cannot resolve, check its explicit Git entry before changing registries
or substituting versions. Resolve Console compilation errors before proceeding.

Test Framework is not required for this walkthrough. To reproduce package tests,
use the separate [recorded test consumer manifest](../../validation/evidence/unity-6000.3-persistence-unity-windows-editor/consumer-manifest.json)
and [Unity gate instructions](../../validation/run-unity-gates.md); a successful
manual round trip does not replace those tests or recreate their exact tuple.

## 3. Create the configuration asset

In the Project window choose **Create > Lingkyn > Persistence > Unity Config**.
Name the asset `PersistenceQuickstartConfig` and set these Inspector values:

| Field | Value for this walkthrough |
| --- | --- |
| Schema Id | `example.persistence-quickstart` |
| Current Schema Version | `0` |
| Commit Id | `quickstart` (envelope metadata, not the Git install pin) |
| File Extension | `.save` |
| Storage Subdirectory | `persistence-quickstart` |
| Commit Strategy | `RecoverableCopyReplace` |
| Required Commit Capability | `RecoverableReplace` only |
| Recovery Policy | `PrimaryThenBackup` |
| Integrity Algorithm | `sha-256` |
| Migration Edges | empty, size `0` |

The asset's actual defaults use `AtomicFileReplace` with a minimum requirement of
`RecoverableReplace`. Here we select `RecoverableCopyReplace` explicitly for
both first save and replacement. A first save stages and moves into an empty
primary path; subsequent saves copy the previous primary to one backup before
replacing it. This is a recoverable strategy, not an atomicity guarantee.

**Do not require `AtomicReplace` for a new slot.** It fails with
`Commit / UnsupportedCommitCapability` when there is no primary to replace.
Even with `AtomicFileReplace`, a lower minimum requirement does not turn its
replacement algorithm into a copy fallback. Choose capabilities deliberately
for the target filesystem. Keep migrations empty here: this example saves and
loads schema version `0`, and provides no migration implementations.

## 4. Add and run the consumer script

Create `Assets/PersistenceQuickstart.cs` with the complete contents below. This
uses the same public factory and coordinator as the shipped LocalFilePersistence
sample; importing that sample is not needed. Put it outside custom assembly
definition folders for the simplest setup. If you use your own `.asmdef`, add
references to both `Lingkyn.Persistence.Core` and `Lingkyn.Persistence.Unity`.

```csharp
using System;
using System.IO;
using Lingkyn.Persistence.Core;
using Lingkyn.Persistence.Unity;
using UnityEngine;

[Serializable]
public sealed class PersistenceQuickstartState
{
    public int level;
    public string checkpoint;
}

public sealed class PersistenceQuickstart : MonoBehaviour
{
    [SerializeField] private PersistenceUnityConfig config;

    [ContextMenu("Persistence/Save then load")]
    public void SaveThenLoad() => Run(writeFirst: true);

    [ContextMenu("Persistence/Load only")]
    public void LoadOnly() => Run(writeFirst: false);

    private void Run(bool writeFirst)
    {
        if (!Application.isPlaying)
        {
            Debug.LogWarning("Enter Play mode before running the quickstart.");
            return;
        }

        var created = PersistenceUnityFactory.CreateCoordinator(
            config, new PersistentDataRootProvider(),
            new JsonUtilitySaveCodec<PersistenceQuickstartState>());
        if (!created.Succeeded) { Report(created.Error); return; }

        var slot = SaveSlotId.TryCreate("slot_main");
        if (!slot.Succeeded) { Report(slot.Error); return; }
        var coordinator = created.Value;
        Debug.Log("Save folder: " + Path.Combine(
            Application.persistentDataPath, config.StorageSubdirectory));

        if (writeFirst)
        {
            var saved = coordinator.Save(slot.Value,
                new PersistenceQuickstartState { level = 3, checkpoint = "town-square" });
            if (!saved.Committed)
            {
                Report(saved.Error);
                Debug.LogWarning("Prior record preserved: " + saved.PriorCommittedRecordPreserved);
                return;
            }
            foreach (var warning in saved.Diagnostics)
                Debug.LogWarning($"{warning.Stage} / {warning.Code}: {warning.Message}");
        }

        var loaded = coordinator.LoadValidated(slot.Value, state =>
            state != null && state.level >= 0 && !string.IsNullOrEmpty(state.checkpoint)
                ? SaveResult.Success()
                : SaveResult.Fail(SaveStage.Validate, SaveErrorCode.ValidateRejected,
                    "Expected nonnegative level and a checkpoint."));
        if (!loaded.Succeeded) { Report(loaded.Error); return; }

        var receipt = loaded.Value;
        Debug.Log($"Loaded level={receipt.State.level}, checkpoint={receipt.State.checkpoint}; " +
            $"candidate={receipt.SelectedCandidateKind}, recovered={receipt.RecoveryOccurred}");
        if (receipt.PrimaryFailureDiagnostic.HasValue)
        {
            var diagnostic = receipt.PrimaryFailureDiagnostic.Value;
            Debug.LogWarning($"Primary: {diagnostic.Stage} / {diagnostic.Code}: {diagnostic.Message}");
        }
    }

    private static void Report(SaveError error) =>
        Debug.LogError($"Persistence failed: {error.Stage} / {error.Code}: {error.Message}");
}
```

1. Create an empty GameObject in a scene and add `PersistenceQuickstart`.
2. Drag `PersistenceQuickstartConfig` into its **Config** field and save the scene.
3. Enter Play mode. From the component's context menu choose
   **Persistence > Save then load**. Nothing writes automatically on entering Play.
4. Expect `Loaded level=3, checkpoint=town-square; candidate=Primary, recovered=False`
   and a `Save folder:` path in the Console.
5. Stop and re-enter Play mode, then choose **Persistence > Load only**. Expect
   the same values without a write. This checks that the data survived the run.

These are expected results for your smoke check, not a recorded execution result
for this documentation revision. Do not use a result's `Value` after failure or
apply partially loaded state. The script logs only; a real application applies
the validated DTO to its own state after success, or supplies an explicit
`LoadAndApply` callback.

## 5. Inspect, repeat, and reset

The printed directory is
`Application.persistentDataPath/persistence-quickstart`. Use that actual path;
the root depends on the project's company/product settings and platform. The
files for this example are:

- `slot_main.save`: current binary envelope containing the JSON payload;
- `slot_main.backup.save`: previous primary after the second successful save;
- `slot_main.staging.<token>.save`: a possible leftover staging file after failure.

The primary is a binary envelope, not a standalone JSON file. Every **Save then
load** invocation overwrites `slot_main` with level `3` and `town-square`; repeated
saves also replace the single backup. Use **Load only** to inspect existing data.
Changing schema id/version, folder, or extension is not a migration.

For a backup smoke check in this disposable project: save twice, stop Play mode,
move `slot_main.save` outside the save directory, re-enter Play mode, and choose
**Load only**. With the backup still present, expect `candidate=Backup`,
`recovered=True`, and a primary `NotFound` diagnostic. Loading does not restore
the primary file automatically. Keep the displaced file until you have inspected
the result; do not run a new save first because that would hide the condition.

To start fresh, stop Play mode and remove only this walkthrough's primary,
backup, and matching staging files from the printed directory, after keeping
anything you need. There is no public slot-deletion API. **Load only** should then
return `Read / NotFound`; **Save then load** creates a new primary. Deleting the
scene, component, or config asset alone does not delete persisted files. Do not
delete a whole production `persistentDataPath` to reset this example.

## Failure and recovery scope

Always check `SaveCommitResult.Committed` for a save and `Succeeded` for a load
or factory result. Retain the stage, error code, and message when reporting a
failure. A committed save can carry warning diagnostics; retrying it blindly can
replace the backup. `PriorCommittedRecordPreserved` reports preservation of the
previous primary in primary or backup after failure, not preservation of all
historical backups or proof against a process/power crash.

`PrimaryThenBackup` permits fallback for a missing primary, an unsupported or
malformed envelope, or payload integrity failure, when a valid backup candidate
can be read. It does not promise recovery from any error: store read failures,
ambiguous candidates, decode failures, missing/future migrations, and rejected
state validation fail closed. Staging files are never selected. In the pinned
release, a **zero-byte** primary/backup/staging file is an additional known limit:
candidate construction rejects it and the read fails rather than recovering.
The later source fix is not part of the release pin above. SHA-256 detects
accidental payload changes; it does not authenticate a save or encrypt its data.

For `UnsupportedCommitCapability`, check both strategy and minimum capability,
including the first-create rule. For `IoDenied`/`OutOfSpace`, inspect the reported
stage and the printed destination before retrying. For `MissingMigration` or
`FutureSchema`, supply reviewed migrations or select the matching schema; do not
erase a real save to suppress the error. If compilation cannot find `JsonUtility`,
check the JSON Serialize module entry. The release's optional imported
`LocalFilePersistenceExample.cs` also lacks `using Lingkyn.Persistence.Unity;`;
this standalone script avoids that issue. The current source sample fixes the
import, but the immutable release does not change.

Keep real gameplay snapshots plain `[Serializable]` DTOs with serialized fields.
The shipped codec rejects live `UnityEngine.Object` references, dictionaries,
generic/polymorphic shapes, cycles, and readonly serialized fields. Capture a
consistent snapshot yourself, keep file operations serialized for a slot, and
call this Unity root provider on the main thread. Use a consumer-owned codec,
store, or root provider through the [public seams](api-surface.md) when needed.

## Using an unmatched tuple

Record your exact Unity/editor, OS, renderer, package lock, build target, graphics
API, backend, architecture, XR/provider/runtime, input, and device tuple. Follow
the [version-adaptive reference route](../../architecture/version-adaptive-reference-model.md):
use `raw_material` to adapt a candidate, then validate that candidate's own
resolution, compilation, tests, independent consumer, and applicable build/device
gates. Do not infer support from the manifest or from a successful round trip here.

For a reproducible package failure, [open an issue](https://github.com/Lingkyn/xr-foundry/issues/new/choose)
with the package IDs, full Git pin, exact tuple, minimal reproduction, stage/code,
expected versus actual result, and relevant redacted logs. See
[Support](../../../SUPPORT.md); private save contents and secrets are not needed.
