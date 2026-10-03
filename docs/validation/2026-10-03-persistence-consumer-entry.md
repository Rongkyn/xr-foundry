# Persistence consumer entry verification, 2026-10-03

This is standalone C# compilation using compiler/runtime binaries and reference
assemblies from the official Linux Unity Editor 6000.3.19f1 distribution. Unity
Editor was not launched. This does not establish package resolution/import,
Unity-generated compilation settings, EditMode/PlayMode execution, a successful
save/load, player builds, filesystem behavior, or device support.

## Compiler context

- Runtime: Mono JIT 6.13.0, `explicit/dc7ab1aa`, amd64.
- Compiler: bundled `MonoBleedingEdge/lib/mono/4.5/csc.exe`,
  `3.7.0-5.20367.1 (f96dcbb6)`.
- Arguments: `-nologo -noconfig -nostdlib+ -target:library -langversion:8.0 -deterministic+`.
- Explicit framework reference: `NetStandard/ref/2.1.0/netstandard.dll`.
- Adapter/consumer engine references: `Managed/UnityEngine/UnityEngine.CoreModule.dll`
  and `Managed/UnityEngine/UnityEngine.JSONSerializeModule.dll`.
- Core and Unity adapter compiled as separate assemblies; consumers referenced
  those assemblies. All source snapshots, outputs, and logs stayed outside the repo.

## Independent checks

1. Snapshot Core and Unity runtime sources with `git show` from
   `ff3ac8b0110e5a1b225a88b740460ce2780b11ea`; compile each assembly: **exit 0**.
2. Compile that commit's unchanged `LocalFilePersistenceExample.cs` separately
   against those assemblies: **exit 1**, `CS0246` at `(16,57)`:
   `PersistenceUnityConfig` could not be found.
3. Compile the working-tree sample, whose sole source change is adding
   `using Lingkyn.Persistence.Unity;`: **exit 0**, no diagnostics.
4. Extract the sole C# block of `docs/standards/persistence/quickstart.md`
   as `PersistenceQuickstart.cs`; compile against the main snapshot: **exit 0**.
5. Independently snapshot and compile both packages from the guide's actual
   release pin `1b67c092b8c0f38e3c4fcf0b040a8807c97e701e`; compile the same
   quickstart source against those assemblies: **exit 0**.
6. Compile the current sample together with the README's `RunLocalFilePersistence`
   wrapper against the main snapshot: **exit 0**.

Warnings: main adapter reports `CS0649` for serialized `currentSchemaVersion`;
release adapter also reports existing `CS0168` for unused `exception`.
Both consumer MonoBehaviour snippets report `CS0649` for their Inspector-assigned
`config` field. Compilation emitted no errors except the expected baseline defect.

## SHA-256 evidence

| Input | SHA-256 |
| --- | --- |
| Mono binary | `c5a56e5eb598ec11fb60a3d0f2040847b4b7d669bedd95f126c8d137667588a4` |
| C# compiler | `7228085c2028c2426f8ae4272c9ba7efdcaa76b08b8ea8ea9168c203bb0bcb15` |
| netstandard reference | `79a49049c360a3ff282e747c311fcd567834efde564a96689872564164756e84` |
| CoreModule reference | `fd4f326a781bfc6328f8e9b87a5dba3479346f463b5477b316a81f3d2b33443d` |
| JSONSerializeModule reference | `9d893ca9ef42794dc0fbeccc7e279fc9f8dd98b32afddda9dfbdbc2219b3d1de` |
| Baseline sample | `af29fea4784406e4e55dfc808fbb309003b73b21de12ec3557ffba63723db2e2` |
| Fixed working-tree sample | `43f190422f3c2ce465ade728f1f713d900e5487a11891b8f15342a6de8dfcf62` |
| Quickstart C# block (one final LF) | `3c44a660288ecc613345699751b72aec43ac496f97d9a3a5720189b1e2686e55` |
| Sample README C# block (one final LF) | `6a295ca3c251e864a4236cfcc5ece844215830ab62383874aadf68c4f70e5b8c` |

Runtime source inputs are bound to the full commits above. Individual source hashes,
full commands, compiler diagnostics, and output hashes are retained in the local
`receipt.json` and `consumer-receipt.json`. The source manifest digests are
`3c2f78c06ceded49121264c51ea7d24871e65a5f37be4ba940e3eeda1646ed46` (main) and
`be53d95f4996add005d4e6bc5c208c68233917645eee630cc4210e50d5d58630` (release),
over sorted lines of `SHA256`, two spaces, repository-relative source path, LF.

## Reproduce the static check

The following Bash recipe requires Git, Python, ripgrep and the already installed
official Linux Editor distribution. Set `XR_REPO` to this checkout's absolute
root, `UNITY_DATA` to its installed `Editor/Data` directory and `XR_EVIDENCE` to a
new writable directory outside the checkout. It invokes the bundled compiler;
it never launches Unity Editor or executes the output assemblies. Its baseline
failure is expected and checked separately from the fixed/consumer results.

```bash
#!/usr/bin/env bash
# Static C# compilation only. Does not launch Unity Editor or execute assemblies.
set -euo pipefail
: "${XR_REPO:?Set XR_REPO to the repository root}"
: "${UNITY_DATA:?Set UNITY_DATA to the extracted Unity 6000.3.19f1 Editor/Data directory}"
: "${XR_EVIDENCE:?Set XR_EVIDENCE to a new writable directory outside the repository}"
if [[ -e "$XR_EVIDENCE" ]]; then
    echo 'Choose a new XR_EVIDENCE directory.' >&2
    exit 1
fi
mkdir -p "$XR_EVIDENCE"
mono="$UNITY_DATA/MonoBleedingEdge/bin/mono"
csc="$UNITY_DATA/MonoBleedingEdge/lib/mono/4.5/csc.exe"
package='packages/unity/systems/persistence'
core="$package/com.lingkyn.persistence.core/Runtime"
unity="$package/com.lingkyn.persistence.unity/Runtime"
sample="$package/com.lingkyn.persistence.unity/Samples~/LocalFilePersistence/LocalFilePersistenceExample.cs"
main='ff3ac8b0110e5a1b225a88b740460ce2780b11ea'
release='1b67c092b8c0f38e3c4fcf0b040a8807c97e701e'
common=("$mono" "$csc" -nologo -noconfig -nostdlib+ -target:library -langversion:8.0 -deterministic+ "-r:$UNITY_DATA/NetStandard/ref/2.1.0/netstandard.dll")
engine_refs=("-r:$UNITY_DATA/Managed/UnityEngine/UnityEngine.CoreModule.dll" "-r:$UNITY_DATA/Managed/UnityEngine/UnityEngine.JSONSerializeModule.dll")
"$mono" --version
"$mono" "$csc" -version

for entry in "main:$main" "release:$release"; do
    label="${entry%%:*}"
    pin="${entry#*:}"
    while IFS= read -r source; do
        [[ "$source" == *.cs ]] || continue
        mkdir -p "$XR_EVIDENCE/$label/$(dirname "$source")"
        git -C "$XR_REPO" show "$pin:$source" > "$XR_EVIDENCE/$label/$source"
    done < <(git -C "$XR_REPO" ls-tree -r --name-only "$pin" -- "$core" "$unity")
    "${common[@]}" "-out:$XR_EVIDENCE/$label/Lingkyn.Persistence.Core.dll" "$XR_EVIDENCE/$label/$core/"*.cs
    "${common[@]}" "${engine_refs[@]}" "-r:$XR_EVIDENCE/$label/Lingkyn.Persistence.Core.dll" "-out:$XR_EVIDENCE/$label/Lingkyn.Persistence.Unity.dll" "$XR_EVIDENCE/$label/$unity/"*.cs
done

mkdir -p "$XR_EVIDENCE/baseline" "$XR_EVIDENCE/working-tree"
git -C "$XR_REPO" show "$main:$sample" > "$XR_EVIDENCE/baseline/LocalFilePersistenceExample.cs"
cp "$XR_REPO/$sample" "$XR_EVIDENCE/working-tree/LocalFilePersistenceExample.cs"
python - "$XR_REPO" "$XR_EVIDENCE" <<'PY'
from pathlib import Path
import re
import sys
repo, evidence = map(Path, sys.argv[1:])
doc = (repo / 'docs/standards/persistence/quickstart.md').read_text()
blocks = re.findall(r'```csharp\n(.*?)\n```', doc, re.S)
assert len(blocks) == 1, f'Expected one C# block, found {len(blocks)}'
(evidence / 'working-tree/PersistenceQuickstart.cs').write_text(blocks[0] + '\n')
sample_readme = repo / 'packages/unity/systems/persistence/com.lingkyn.persistence.unity/Samples~/LocalFilePersistence/README.md'
wrapper_blocks = re.findall(r'```csharp\n(.*?)\n```', sample_readme.read_text(), re.S)
assert len(wrapper_blocks) == 1, f'Expected one sample wrapper C# block, found {len(wrapper_blocks)}'
(evidence / 'working-tree/RunLocalFilePersistence.cs').write_text(wrapper_blocks[0] + '\n')
PY
main_refs=("${engine_refs[@]}" "-r:$XR_EVIDENCE/main/Lingkyn.Persistence.Core.dll" "-r:$XR_EVIDENCE/main/Lingkyn.Persistence.Unity.dll")
if "${common[@]}" "${main_refs[@]}" "-out:$XR_EVIDENCE/Sample.Baseline.dll" "$XR_EVIDENCE/baseline/LocalFilePersistenceExample.cs" > "$XR_EVIDENCE/baseline.log" 2>&1; then
    echo 'ERROR: baseline unexpectedly compiled' >&2
    exit 1
fi
cat "$XR_EVIDENCE/baseline.log"
rg "error CS0246:.*PersistenceUnityConfig" "$XR_EVIDENCE/baseline.log" > /dev/null
"${common[@]}" "${main_refs[@]}" "-out:$XR_EVIDENCE/Sample.Fixed.dll" "$XR_EVIDENCE/working-tree/LocalFilePersistenceExample.cs"
"${common[@]}" "${main_refs[@]}" "-out:$XR_EVIDENCE/Sample.WithWrapper.dll" "$XR_EVIDENCE/working-tree/LocalFilePersistenceExample.cs" "$XR_EVIDENCE/working-tree/RunLocalFilePersistence.cs"
for label in main release; do
    "${common[@]}" "${engine_refs[@]}" "-r:$XR_EVIDENCE/$label/Lingkyn.Persistence.Core.dll" "-r:$XR_EVIDENCE/$label/Lingkyn.Persistence.Unity.dll" "-out:$XR_EVIDENCE/Quickstart.$label.dll" "$XR_EVIDENCE/working-tree/PersistenceQuickstart.cs"
done
```

## Consumer and repository checks

At baseline `ff3ac8b0110e5a1b225a88b740460ce2780b11ea`, the existing reference
materializer successfully copied 11 packages. Auditing its complete source
inventory produced 15 assemblies, 286 EditMode and 10 PlayMode cases, with no
inventory errors. These are source counts, not executed tests. The seven-suite
146/4 result published in PR #88 remains historical evidence for its own inputs.

The smaller existing command was also run:

```bash
python scripts/run_unity_gates.py --host com.lingkyn.persistence.unity --dry-run
```

It returned `PLANNED`, with two assemblies (54 Core and 34 Unity Editor cases),
zero passed and zero failed. No Editor was selected or launched. The generated
host embeds only the two Persistence siblings and requests Test Framework 1.6.0.
The quickstart's runtime-only manifest explicitly includes JSON Serialize because
it does not depend on the test framework to bring that module transitively.

Repository composition and validation pass. Full Python test and final
committed-head merge-readiness results are recorded with the pull request.
Static compilation does not update a compatibility profile, version, maturity,
release or the composition's `runtime_ready: false` claim.

