# SettingsAuthoring

Import this sample from the Settings Unity package in Package Manager. It converts
ScriptableObject definitions into the Core registry, applies one transaction to
observable consumer-owned state, and demonstrates rollback after a later
applicator rejects the change. It does not change Unity audio, create a settings
menu, save choices, or implement a package/schema upgrade.

The earlier example only demonstrated registration and returned success from
no-op applicators. `Run(catalog)` remains available for existing callers. To
observe the effect and failure diagnostics, use `ApplyMute` with a host you own:

```csharp
var catalog = SettingsAuthoringExample.CreateSampleCatalog();
var host = new SettingsAuthoringHost(); // Muted starts false, matching the catalog.
var applied = SettingsAuthoringExample.ApplyMute(catalog, host, true);
Debug.Log($"{applied.Outcome}: muted={host.Muted}, revision={applied.CommittedRevision}");
// Expected: Applied: muted=True, revision=1
```

Use `Lingkyn.Settings.Unity.Samples` for the sample types and `UnityEngine` for
`Debug`. The sample's assembly is `Lingkyn.Settings.Unity.Samples.SettingsAuthoring`;
add that reference if your caller is in its own assembly definition. Use a fresh
host/catalog for each scenario below. Each `ApplyMute` invocation builds a new
coordinator from catalog defaults; it is a one-transaction example, not a
persistent application session.

For a failure after the first applicator has changed the host:

```csharp
host = new SettingsAuthoringHost(); // Fresh false host for this scenario.
var rejected = SettingsAuthoringExample.ApplyMute(catalog, host, true, failAfterApply: true);
Debug.Log($"{rejected.Outcome}: muted={host.Muted}, revision={rejected.CommittedRevision}");
Debug.Log(rejected.PrimaryFailure.Message);
```

With a fresh false host, expect `ApplicatorFailed`, `muted=False`, revision `0`,
and the deliberate failure message. Rollback restores the captured *actual host
state*, even if it differed from the catalog's old value. The failing applicator
makes no writes. The coordinator rolls back previously successful applicators;
an applicator that mutates and then fails must compensate its own partial work.
This demonstrates transaction rollback, not package upgrade/rollback or crash
recovery.

Check `Outcome` and its diagnostics before announcing success. An invalid catalog
or missing `audio.mute` definition returns `ValidationFailed` without changing
the host. A transaction that already matches the snapshot returns `NoOp` and does
not synchronize a drifted host. Real consumers retain their coordinator and
explicitly initialize their actual host state from the loaded/effective snapshot.
Do not interpret catalog defaults or a no-op result as an engine-side effect.

`CreateSampleCatalog` creates transient ScriptableObjects. Destroy each generated
definition and the catalog when the demonstration ends (`Destroy` during play or
`DestroyImmediate` in an Editor test). Never destroy persistent assets merely to
clean up this example.

## Run the imported sample tests

The imported `Editor` folder contains six NUnit cases, covering observable apply,
rollback from two prior host states, a missing key, invalid-catalog diagnostics,
and no-op state drift. In a disposable project with Unity Test Framework installed,
open Test Runner, select EditMode, and run
`Lingkyn.Settings.Unity.Samples.SettingsAuthoring.Tests`.

`Samples~` is excluded from normal package compilation and the repository's source
inventory. These tests become discoverable only after importing the sample into
`Assets`; the normal package test receipt does not include them. A source inventory
check after copying the sample into a disposable fixture detects six cases, but
this revision has **not** run them in Unity. The expected output above is a test
procedure, not a recorded passing runtime result. Existing package compatibility
receipts do not automatically cover this modified sample or another host tuple.
