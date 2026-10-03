# LocalFilePersistence

Minimal plain DTO snapshot and coordinator wiring. For a complete first-use path,
follow the [Persistence quickstart](https://github.com/Lingkyn/xr-foundry/blob/main/docs/standards/persistence/quickstart.md):
it installs both packages and provides a standalone caller, so importing this
sample is optional.

## Run this sample from current source

1. In Package Manager select **Lingkyn Persistence Unity** and import the
   **LocalFilePersistence** sample from its Samples section. It contains code, not
   an automatically running scene or component.
2. Create a config with **Create > Lingkyn > Persistence > Unity Config**. Set
   schema id `example.persistence-quickstart`, version `0`, commit id `quickstart`,
   extension `.save`, subdirectory `persistence-quickstart`, strategy
   `RecoverableCopyReplace`, required capability `RecoverableReplace`, recovery
   `PrimaryThenBackup`, integrity `sha-256`, and no migration edges. Requiring
   `AtomicReplace` prevents the first save to an empty slot.
3. Create `Assets/RunLocalFilePersistence.cs` with the following code, add it to an
   empty GameObject, and assign the config. Enter Play mode and choose
   **Persistence > Run sample** from the component's context menu.

```csharp
using Lingkyn.Persistence.Samples;
using Lingkyn.Persistence.Unity;
using UnityEngine;

public sealed class RunLocalFilePersistence : MonoBehaviour
{
    [SerializeField] private PersistenceUnityConfig config;

    [ContextMenu("Persistence/Run sample")]
    public void RunSample()
    {
        if (!Application.isPlaying)
        {
            Debug.LogWarning("Enter Play mode before running the sample.");
            return;
        }
        var result = LocalFilePersistenceExample.Run(config);
        if (!result.Succeeded)
        {
            Debug.LogError($"{result.Error.Stage} / {result.Error.Code}: {result.Error.Message}");
            return;
        }
        Debug.Log($"Loaded level={result.Value.level}, checkpoint={result.Value.checkpoint}");
        Debug.Log("Persistent root: " + Application.persistentDataPath);
    }
}
```

Expected output is `Loaded level=3, checkpoint=town-square`. This is a procedure
for you to run, not a recorded execution result. If using a custom `.asmdef`, keep
the caller and imported sample in the same assembly or reference the sample's
assembly, and reference `Lingkyn.Persistence.Core` and `Lingkyn.Persistence.Unity`.

Every call saves before loading, overwriting `slot_main` under
`Application.persistentDataPath/persistence-quickstart`. The first run creates
`slot_main.save`; later successful runs keep the previous primary at
`slot_main.backup.save`. Use the quickstart's **Load only** command for an existing
save or backup check, and its reset instructions to remove only these demo files.
This sample accepts any decoded DTO in its validator and returns just the state;
production callers must validate their own domain rules and inspect commit/load
receipts and warning diagnostics directly. Keep live scene objects and authored
ScriptableObject assets out of mutable DTO state.

## Immutable release caveat

The sample at release `unity-next-systems-v0.1.0` (commit
`1b67c092b8c0f38e3c4fcf0b040a8807c97e701e`) lacks the
`using Lingkyn.Persistence.Unity;` directive in `LocalFilePersistenceExample.cs`.
This source revision adds it; the old release remains unchanged. The quickstart's
standalone script works through the release's public API without importing that
sample. If you choose to import the old sample, add that directive to the imported
copy in your own `Assets/Samples` folder before compilation.

Claim ceiling: the recorded evidence covers the exact Windows Editor compile and
EditMode-test tuple linked by the quickstart. It does not prove this imported
sample's interactive run, other platforms, devices, cloud, security, or crash
durability.
