# Open Brush: bounded source audit for spatial drawing

Checked 2026-10-03 UTC. Open Brush revision: `140b2e73dd91280ee36ea69db7e1d124b4123370`. XR Foundry review baseline: `e57bc145ac35ad50918521567b138a673ad84101`.

## Decision and scope

Open Brush is useful positive implementation evidence for retained stroke samples, brush references, application undo/redo, snapshots, and versioned persistence. This review closes the **bounded Open Brush source-inspection questions** about persistence/migration, test inventory, current maintenance, dependency context, and exclusion of licensed implementation/assets. It does not admit the family, establish every proposed Core capability, or clear Open Brush for extraction or redistribution.

The proposed derivation is **architecture facts only**. No Open Brush implementation, brush, shader, model, texture, audio, test fixture, branding, or dependency is selected for vendoring. No source files or assets were placed in XR Foundry. Source retrieval used read-only official GitHub APIs at the pinned revision; no Unity, upstream tests, runtime, or device execution occurred.

The most important correction is that the existing proposal's nonserialized-seed claim is wrong at this pin. Actual serialization supersedes stale comments. Full deterministic replay nevertheless remains unsupported.

## Persistence and migration observations

| Pinned evidence | Observed behavior | Limit on the proposal |
| --- | --- | --- |
| [SketchWriter.cs][writer], lines 15–101, 197–330, 544–760 | Binary stroke records have an explicit version; writer emits 5 and reader accepts 5–6. Samples contain position/orientation and pressure/timestamp extensions. Stroke fields include brush index, color, width, flags, scale, group, seed, layer and optional point colors. Unknown extensions are skipped. | This is a specific application format, not an engine-neutral interchange contract. Skipping data is not preserving it. |
| [SketchWriter.cs][writer], lines 231–255, 592–603, 676–677 | Writer includes and writes the seed; reader restores it. Legacy records lacking it receive a seed derived from stroke position in the stream and brush/color/size hash codes. | Do not repeat the stale “not serialized” comment in [StrokeData.cs][data], lines 36–38, or the enum's “random” fallback comment. Hash behavior across runtimes and full rendering determinism were not established. |
| [Stroke.cs][stroke], lines 162–191; [SketchWriter.cs][writer] record layout | A constructed or cloned stroke receives a new GUID. The inspected sketch record layout does not persist that stroke GUID. | Durable stable stroke identity across save/load is Foundry synthesis. Brush GUID persistence does not prove stroke identity persistence. |
| [TiltFile.cs][tilt], lines 31–54, 57–257, 320–345 | The container uses a versioned 16-byte header followed by ZIP, with metadata.json, data.sketch and image entries; directory form is also supported. Its writer stages at `_part`, renames the old destination to `_previous`, then moves the replacement. | This supports a staged-save comparison, not a demonstrated crash-consistent transaction. The two renames are distinct operations; no fault-injection result is claimed. |
| [SketchSnapshot.cs][snapshot], lines 60–171, 218–235, 285–333 | Snapshot construction is timesliced and reads application state. File writing writes stroke data, assigns its brush index to metadata, then commits through TiltFile. Save maps compatible superseding brushes backward. | A useful snapshot/storage boundary, but not an independent immutable document library or byte-canonical save guarantee. |
| [SketchMetadata.cs][metadata], lines 797–917; [MetadataUtils.cs][migration], lines 472–608 | Current metadata schema is 3. Upgrade functions address old sets, model transforms, pinned/tinted defaults and versions 0→1→2→3. VerifyMetadataVersion upgrades old versions; the inspected method does not reject future metadata schema numbers. | Concrete migration evidence exists. This does not establish lossless migration or a strict unknown-version policy. Binary version rejection and metadata version handling differ. |
| [SaveLoadScript.cs][load], lines 631–643, 653–664, 703–715, 769–800, 904–915 | Missing declared playback capabilities can reject loading; compatible brush supersession is followed on load; legacy layer scale zero is replaced with one. Some JSON deserialization errors are marked handled and reported. | Migration includes application policies and recovery/defaulting. Do not convert this into strict schema validation or format-fidelity claims. |

The decoder's ReadMemory path clears redo and, for replacement loads, current memory before parsing (SketchWriter lines 478–508). Parsing also resolves application groups/layers. This specifically fails to supply evidence for the proposed requirement that invalid import leaves the existing document untouched. Stage/validate-before-replace remains a new Foundry obligation.

## History and other stronger contracts

[SketchMemoryScript.cs][memory], lines 442–508, 888–895 and 1047–1069, supplies more direct history evidence than the previously inspected command files alone. Recording a new command clears redo, can merge commands, calls Redo and pushes onto the operation stack. Undo/redo move commands between two stacks. No history-count or byte-budget eviction policy was established in these inspected methods. There are distinct local and network recording paths; one universal attributed intent route cannot be inferred.

The following remain proposed Foundry requirements, not observed Open Brush guarantees:

- Atomic validated edits with rollback and unchanged revisions on rejection
- Durable value IDs preserved through import, clone, save and load
- Bounded history with explicit eviction behavior
- A single engine-light write path with actor attribution and stale-revision refusal
- Canonical document fingerprints and deterministic replay across a declared runtime tuple
- Lossless interchange, unknown-channel preservation, strict import budgets and crash-safe storage
- Dependency inversion without scene singletons, and installation in independent clean consumers

Seed serialization is useful positive evidence, but cannot establish these contracts. The existing command review also shows application/network time reads. Document replay and geometry/pixel determinism should remain separate and deferred unless specifically designed and verified.

## Test inventory actually inspected

The pinned [Editor test directory][tests] contains **40 C# files**, including helpers; this is a file count, not a test-case count or pass count. Selected test bodies were fetched and inspected:

| File | Actual inspected scope |
| --- | --- |
| [TestMemory.cs][test-memory] | EnumerateAdjustedSnapshots grouping flags as strokes become inactive |
| [TestFile.cs][test-file] | Skipping non-seekable ZIP substreams through both ZIP implementations; binary writer output compared with BinaryWriter |
| [TestBinaryReaderWriter.cs][test-binary] | BaseStream behavior, length-prefixed list round trip, invalid element size, overflowing requested byte count, zero-size data |
| [TestJsonGlue.cs][test-json] | Transform/color/palette JSON and historical palette representation |
| [TestStatelessRng.cs][test-rng] | Numeric conversion, correlation and distribution checks; one salt-reuse section is compile-disabled |
| [TestBrush.cs][test-brush] | Edit-time subset construction; the timing/geometry-generation section is compile-disabled |
| [TestStrokeCropping.cs][test-crop] | Geometric clipping, re-entry/splitting and transformed canvas cases |
| [TestStrokeSculptInfluence.cs][test-sculpt] | Influence weights, pressure fallback, captured-point manipulation, smoothing and orientation calculations |

There are also [HTTP API PlayMode tests][http-tests] with 57 UnityTest attributes and a [test assembly][http-asmdef]. They exercise application commands and depend on application readiness; some cases explicitly skip depending on VR/monoscopic state. The separate [TestPackInt.cs][packint] is a shader test harness supporting a prefab/menu/manual execution route; it is not evidence of a Unity Test Runner pass.

The reviewed tests do **not** establish end-to-end .tilt durable round-trip fidelity, stable stroke IDs, transactional import failure, crash-safe commit, metadata migration fixtures across supported versions, bounded undo, or canonical replay. This is a coverage limitation of this selected review, not a claim that every upstream file was searched and no other relevant test exists.

Remaining Editor-directory inventory (not body-reviewed): ManualColocationSolverTests, TestApiSecurity, TestColor, TestDefaultMediaSeeder, TestExport, TestFileUtils, TestFuture, TestGeometryPool, TestGsplatMigrationConfiguration, TestGsplatModelOwnership, TestHdrTextureLoader, TestIcosaAssetCatalog, TestImageCache, TestListExtensions, TestLuaManager, TestMathUtils, TestMembraneFill, TestMisc, TestOpenBrushExportPlugin, TestPlaneExtensions, TestQuaternionExtensions, TestRingBuffer, TestTbTaskExtensions, TestTrTransform, TestTransformExtensions, TestVisualizerManagedAnalysis, TestVrAssetService and TestVrJpeg. Helper files: AsyncTestUtils, ColorTestUtils, MathTestUtils and Stats. The pinned TestData directory contains data.zip and two images; none were downloaded or reused.

## Maintenance, releases and compatibility context

- The [reviewed commit][commit] was committed on 2026-10-02 at 16:44:58 UTC and concerns a membrane brush outline variant.
- GitHub's [latest stable release][stable] was 2.32.0, published 2026-09-01. The inspected [release collection][releases] also listed 2.32.27–2.32.29 from September 25–26 as prereleases, with Android, Desktop, Linux, Mac and Quest assets. Release metadata/artifact presence is activity evidence; no binaries were downloaded, verified or executed.
- For this exact pin, the [pre-commit run][precommit-run] completed successfully. The [Builds run][build-run] completed with overall failure. Its [job results][jobs] show ten platform build jobs succeeded, while macOS/iOS publication and DMG notarization jobs failed; GitHub release creation was skipped. Do not summarize this as either “all builds broken” or “tests passed.”
- The inspected [build workflow][build-workflow] contains build/publish orchestration, but no Unity test-runner, runTests, EditMode/PlayMode or test-results step was found. Test-file presence and successful build jobs supply no test execution receipt.
- [ProjectVersion.txt][unity-version] specifies **6000.6.0f1**, revision f7f8ed4d1e24. The pinned [README][readme] still names **2022.3.34f1** in prerequisites and describes old tested setup steps. Report the discrepancy; do not use the README to infer the current build tuple.

These sources close “is there recent upstream maintenance?” for this review date. They do not establish Foundry compatibility, independent-consumer operation, headset behavior, maintenance promises, or future availability.

## Dependency and rights boundary

[Packages/manifest.json][manifest] records a substantial application dependency graph: URP 17.6.0, Input System 1.20.0, Unity Test Framework 1.8.0, OpenXR 1.18.0, XR Management 4.7.0, SharpZipLib 1.3.9, plus Git dependencies for tools, importers, audio, scripting and device support. Several requested Git revisions are branch names or omit a ref. [packages-lock.json][lock] records concrete Git hashes, including the Open Brush Unity tools at 8163316eb52b519d5c12dcf246447dc48ce16f53. A lock record is not an executed clean resolution.

The selected persistence implementation itself references Unity types/application state, Newtonsoft JSON and selectable ZIP implementations. It therefore does not establish an engine-neutral package seam. The [ThirdParty directory][thirdparty] includes additional bundled code and vendor assets; the README describes optional Photon Fusion/Voice installation. None are proposed Core dependencies.

The [root license][license] is Apache-2.0, and the selected stroke/save/history implementation files carry Apache headers. [GeneratedThirdPartyNotices.txt][notices] contains separate notices for David Eberly, FluxJpeg, GlTF, GraphicsAnton, Ionic.Zip and SimplexNoise. The [generator][notice-generator] searches selected notice filenames under Assets/ThirdParty and its NuGet subtree; that mechanism is not a complete dependency/asset license inventory. The [notice-check workflow][notice-workflow] checks generated-file drift.

The [brand guidelines][brand] treat Tilt Brush trademarks separately. The README also explicitly documents historical replacement of components for licensing reasons and warns about experimental-brush compatibility. No root-license inference should be extended to every asset, bundled SDK, font, third-party notice, trademark or external service. A proposed brush reference supplies no permission to distribute the referenced brush implementation/artwork.

For this architecture-only proposal, the useful outcome is an explicit **zero-copy/zero-asset selection** and a scoped provenance record. Any later decision to copy, adapt or redistribute a file or dependency reopens the applicable per-file/transitive rights review. A guessed Ionic.Zip/LICENSE.txt path returned 404; no license conclusion was drawn from that failed fetch.

## Exact proposal corrections and remaining gate

1. `source-manifest.json`: update `open-brush-stroke-data` admitted role/claims to say its seed comment is stale; cite SketchWriter serialization and hash-derived legacy backfill. Replace claims of nonserialized seeds with these observations. Add pinned evidence records for serializer/container/metadata/migration, test inventory, project/lock manifests and notices. Maintenance can now cite the commit, releases and exact CI outcome, dated 2026-10-03.
2. `source-to-capability.md`: replace “nonserialized random seed” as the replay basis; record seed preservation but no canonical replay guarantee. Separate transient stroke GUIDs from persistent brush references. Add real command-stack behavior to undo evidence, while leaving bounded history and transactionality unproven.
3. `verification-contract.md`: replace its final “random seed caveat” paragraph with the actual remaining risks: legacy hash-derived seeds, runtime-dependent reconstruction, absent durable stroke IDs, application-coupled loading and unverified format fidelity. SD clauses remain planned and unexecuted.
4. `admission.draft.json`: the Open Brush audit blocker can become “Review the completed bounded Open Brush evidence, correct stale seed/identity assumptions, and resolve every mandatory claim; any future selected code/assets/dependencies need their applicable rights review.” Do not leave it implying that current maintenance, serializer paths or test inventory are still wholly unknown. Do not automatically flip authoritative admission/licensing checks solely because this report exists.
5. Keep the family proposal-only. Independent evidence, the common-kernel mapping, exact-consumer plan and explicit public implementation/admission decisions remain the repository's gates.

XR Foundry's AGENTS guidance asks for the smallest relevant artifact and review of its license, maintenance, architecture, tests, compatibility and migration. System admission requires provenance and multiple-source support per mandatory Core capability. The spatial-drawing queue and SD-10 call for **per-file/selected** dependency and asset review. None of those texts explicitly requires auditing every unrelated file/asset in Open Brush before recording original architecture facts. Treating the draft's broad audit wording as a whole-repository security/license certification would add a stronger policy. Narrowing the record to the actual selected facts and excluded reuse is appropriate; expanding implementation scope later expands the audit scope.

## Primary source links

All repository-file links below bind to the reviewed full commit SHA. Directory listings, release metadata and workflow observations were retrieved on the review date.

[writer]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Scripts/Save/SketchWriter.cs
[data]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Scripts/StrokeData.cs
[stroke]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Scripts/Stroke.cs
[tilt]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Scripts/Save/TiltFile.cs
[snapshot]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Scripts/Save/SketchSnapshot.cs
[metadata]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Scripts/Save/SketchMetadata.cs
[migration]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Scripts/Save/MetadataUtils.cs
[load]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Scripts/Save/SaveLoadScript.cs
[memory]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Scripts/SketchMemoryScript.cs
[tests]: https://github.com/icosa-foundation/open-brush/tree/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Editor/Tests
[test-memory]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Editor/Tests/TestMemory.cs
[test-file]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Editor/Tests/TestFile.cs
[test-binary]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Editor/Tests/TestBinaryReaderWriter.cs
[test-json]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Editor/Tests/TestJsonGlue.cs
[test-rng]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Editor/Tests/TestStatelessRng.cs
[test-brush]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Editor/Tests/TestBrush.cs
[test-crop]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Editor/Tests/TestStrokeCropping.cs
[test-sculpt]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Editor/Tests/TestStrokeSculptInfluence.cs
[http-tests]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Tests/PlayMode/TestHttpApiCommandsPlayMode.cs
[http-asmdef]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/Tests/PlayMode/TestHttpApiCommandsPlayMode.asmdef
[packint]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/PlaymodeTests/PackInt/TestPackInt.cs
[commit]: https://github.com/icosa-foundation/open-brush/commit/140b2e73dd91280ee36ea69db7e1d124b4123370
[stable]: https://github.com/icosa-foundation/open-brush/releases/tag/2.32.0
[releases]: https://api.github.com/repos/icosa-foundation/open-brush/releases?per_page=3
[precommit-run]: https://github.com/icosa-foundation/open-brush/actions/runs/37036031458
[build-run]: https://github.com/icosa-foundation/open-brush/actions/runs/37036031466
[jobs]: https://api.github.com/repos/icosa-foundation/open-brush/actions/runs/37036031466/jobs?per_page=100
[build-workflow]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/.github/workflows/build.yml
[unity-version]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/ProjectSettings/ProjectVersion.txt
[readme]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/README.md
[manifest]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Packages/manifest.json
[lock]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Packages/packages-lock.json
[thirdparty]: https://github.com/icosa-foundation/open-brush/tree/140b2e73dd91280ee36ea69db7e1d124b4123370/Assets/ThirdParty
[license]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/LICENSE
[notices]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Support/ThirdParty/GeneratedThirdPartyNotices.txt
[notice-generator]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/Support/Python/unitybuild/generate_notice.py
[notice-workflow]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/.github/workflows/third_party_notices.yml
[brand]: https://github.com/icosa-foundation/open-brush/blob/140b2e73dd91280ee36ea69db7e1d124b4123370/TILT_BRUSH_BRAND_GUIDELINES.md
