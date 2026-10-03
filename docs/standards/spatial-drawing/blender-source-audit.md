# Blender Grease Pencil source audit (WI-033)

Status: **research evidence only; reference_only; proposal_not_admitted**.
Retrieved and reviewed 2026-10-03 UTC. Capability: `ai_tokens_only` (source
inspection and repository checks; no Blender, Unity, renderer or headset run).
This artifact completes the scoped evidence assessment, including negative
outcomes; it grants no source-gate admission or implementation permission.

## Result and revision boundary

Blender supplies one independent implementation lineage for retained stroke
attributes, layer-relative geometry, structural edits and snapshot-based local
undo. It does **not** establish the entire proposed Foundry kernel. Stable stroke
value IDs, atomic multi-operation rollback, a hard history-byte ceiling, one
attributed revision-checked write path, deterministic intent replay and the full
safe-import contract remain unsupported by this review. The evidence supports
retaining those as questions or independently justified design obligations, not
calling them inherited Blender guarantees.

The implementation baseline is Blender **v4.3.0**, resolved through the
[official mirror's tag API][tag] to commit
`2b18cad88b138a1b16617c27540858fba59e66f5`.
Its [commit metadata][revision] is dated 2024-11-19T08:52:10Z. This release was
chosen to bind the proposal's existing 4.3 migration references to actual source.
All S01–S25 links below use that full immutable commit, not the tag or a mutable
branch. Complete file text was retrieved through the GitHub connector; the named
functions/sections were inspected. This is a bounded architecture audit, not an
exhaustive verification of Blender.

The audited Foundry proposal baseline was remote
`b83db66b6cd6cf47d1902f73494f83fc04227a82`, with an identical tree at local
`f7cf379419e4d6b8379e3bd5f73fe260d2304a0f`. The separate research-scope declaration
`e57bc145ac35ad50918521567b138a673ad84101` was added during research. Acceptance
results for the integrated research tree are recorded below; neither baseline
nor a passing repository check proves upstream behavior.

### Dated maintenance observations

On 2026-10-03, the mirror's default-branch commit listing returned
[`bbfc8f3ec2ecb3a214c59d3696f8ad06c70c4638`][maintenance],
committed 2026-10-02T22:47:08Z, a documentation-link maintenance change.
A path-filtered query for the Grease Pencil undo file returned
[`69f5d770c4f17b1688af1f9dceb12bb84d1591af`][undo-maintenance],
dated 2026-08-11T04:01:33Z. Its commit message describes work on mixing global
and edit-mode undo. These are observed recent maintenance records, not CI results
or proof that v4.3.0 is currently supported. The latter change also demonstrates
why the 4.3 snapshot must not be described as current undo semantics. No current
release support horizon, issue backlog, binary behavior or full newer-source
comparison was established.

## Retrieval, source locations and licenses

For every S entry: retrieval outcome = **complete text fetched at immutable ref**
on 2026-10-03 using the official `blender/blender` GitHub mirror. The link supplies
the exact repository path; L numbers identify reviewed locations within that
revision. Notices are observed first-file SPDX notices, not a license inferred
from the repository badge.

| ID | Exact source path | Reviewed location | Per-file notice |
| --- | --- | --- | --- |
| S01 | [source/blender/makesdna/DNA_grease_pencil_types.h][s1] | GreasePencilDrawing, GreasePencilFrame, GreasePencil (L83–164, L442–499) | GPL-2.0-or-later; 2023 Blender Authors |
| S02 | [source/blender/makesdna/DNA_curves_types.h][s2] | CurvesGeometry and curve_offsets (L93–150) | GPL-2.0-or-later; 2023 Blender Authors |
| S03 | [source/blender/blenkernel/BKE_grease_pencil.hh][s3] | DrawingRuntime, Drawing accessors, shared drawing users (L42–163) | GPL-2.0-or-later; 2023 Blender Authors |
| S04 | [source/blender/blenkernel/intern/grease_pencil.cc][s4] | serialization (L188–237, L3953–3998); layer transforms (L1436–1497); drawing compaction (L2909–3006) | GPL-2.0-or-later; 2023 Blender Authors |
| S05 | [source/blender/blenkernel/intern/curves_geometry.cc][s5] | copy/assignment (L93–138), writable offsets (L369–379), resize/removal (L1045–1063, L1262–1326), serialization (L1578–1626) | GPL-2.0-or-later; 2023 Blender Authors |
| S06 | [source/blender/editors/sculpt_paint/grease_pencil_paint.cc][s6] | point/curve attributes (L512–619), random/time initialization (L1023–1067) | GPL-2.0-or-later; 2023 Blender Authors |
| S07 | [source/blender/editors/grease_pencil/intern/grease_pencil_edit.cc][s7] | delete (L468–514), duplicate (L1323–1369) | GPL-2.0-or-later; 2023 Blender Authors |
| S08 | [source/blender/editors/grease_pencil/intern/grease_pencil_utils.cc][s8] | DrawingPlacement construction and projection (L38–117, L310–343) | GPL-2.0-or-later; 2023 Blender Authors |
| S09 | [source/blender/editors/transform/transform_convert_grease_pencil.cc][s9] | createTransGreasePencilVerts and recalcData_grease_pencil (L25–279) | GPL-2.0-or-later; 2023 Blender Authors |
| S10 | [source/blender/editors/grease_pencil/intern/grease_pencil_undo.cc][s10] | StepDrawingGeometry, StepDrawingReference, StepObject, encode/decode and registration (L48–431) | GPL-2.0-or-later; 2023 Blender Authors |
| S11 | [source/blender/blenkernel/intern/undo_system.cc][s11] | limit steps/memory (L407–465), step push (L519–619), undo/redo traversal (L733–909) | GPL-2.0-or-later; 2023 Blender Authors |
| S12 | [source/blender/editors/undo/ed_undo.cc][s12] | ED_undo_push (L104–147) | GPL-2.0-or-later; 2004 Blender Authors |
| S13 | [source/blender/blenkernel/intern/grease_pencil_convert_legacy.cc][s13] | legacy drawing conversion (L787–1015), legacy_main (L3078–3142) | GPL-2.0-or-later; 2023 Blender Authors |
| S14 | [source/blender/blenloader/intern/writefile.cc][s14] | BLO_write_file_impl temporary write/history/rename (L1595–1755) | GPL-2.0-or-later; 2001-2002 NaN Holding BV. All rights reserved. |
| S15 | [source/blender/blenloader/intern/versioning_400.cc][s15] | radius/hardness migration helpers and version gates (L2725–2770, L3655–3672, L4410–4435) | GPL-2.0-or-later; 2023 Blender Authors |
| S16 | [source/blender/makesrna/intern/rna_grease_pencil_api.cc][s16] | drawing add/remove/resize RNA entry points (L36–113) | GPL-2.0-or-later; 2024 Blender Authors |
| S17 | [source/blender/makesrna/intern/rna_curves_api.cc][s17] | add/remove/resize size and index validation (L26–129) | GPL-2.0-or-later; 2024 Blender Authors |
| S18 | [scripts/modules/bpy_types.py][s18] | GreasePencilDrawing.strokes and invalidation note (L1403–1424) | GPL-2.0-or-later; 2009-2023 Blender Authors |
| S19 | [scripts/modules/_bpy_internal/grease_pencil/stroke.py][s19] | indexed helpers, direct attribute setters and slices (L5–46, L139–337) | GPL-2.0-or-later; 2024 Blender Authors |
| S20 | [source/blender/blenkernel/intern/grease_pencil_test.cc][s20] | data/layer/frame tests (L39–570) | GPL-2.0-or-later; 2023 Blender Authors |
| S21 | [source/blender/editors/grease_pencil/tests/grease_pencil_merge_test.cc][s21] | merge tests (L40–265) | Apache-2.0; 2024 Blender Authors |
| S22 | [tests/python/bl_pyapi_grease_pencil.py][s22] | TestGreasePencil, TestGreasePencilLayers, TestGreasePencilDrawing (L13–187) | Apache-2.0; 2024 Blender Authors |
| S23 | [tests/python/ui_simulate/test_undo.py][s23] | view3d_simple (L303–324); complete test-function inventory | GPL-2.0-or-later; 2019-2023 Blender Authors |
| S24 | [tests/python/bl_blendfile_versioning.py][s24] | TestBlendFileOpenAllTestFiles and fixture exclusions (L22–147) | Apache-2.0; 2023 Blender Authors |
| S25 | [tests/python/bl_blendfile_io.py][s25] | TestBlendFileSaveLoadBasic and partial/runtime tests (L14–190) | Apache-2.0; 2020-2023 Blender Authors |

Also fetched in full at the same revision:

- [README.md][readme], License section, identifies Blender as a whole as GPL
  version 3 while allowing compatible per-file licenses.
- [COPYING][copying] points to the GPL; [GPL-license.txt][gpl2] contains GPL v2
  and [GPL3-license.txt][gpl3] contains GPL v3. The root notice alone would not
  describe every file correctly; S21, S22, S24 and S25 carry Apache-2.0 notices.
- [blenkernel/CMakeLists.txt][cmake-kernel] (GPL-2.0-or-later, 2006 Blender
  Authors), [editors/grease_pencil/CMakeLists.txt][cmake-editor]
  (GPL-2.0-or-later, 2006–2023 Blender Authors) and
  [tests/python/CMakeLists.txt][cmake-python] (GPL-2.0-or-later, 2011–2023 Blender
  Authors), for test registration.
- [editors/undo/memfile_undo.cc][memfile] and
  [blenkernel/intern/blender_undo.cc][global-undo] (both GPL-2.0-or-later,
  2023 Blender Authors), for the distinction between editor snapshots and global
  in-memory blend-file undo.

**Reuse disposition:** original factual summaries and links only. No upstream
implementation, test code, brush, shader, artwork or documentation text is copied
into Foundry. GPL-marked implementation is comparison material, not authorized
raw material for a differently licensed package. Any future extraction needs its
own exact-file/dependency/license review and applicable notices. The Apache
notices on some tests do not license the engine, its assets or all fixtures.
This records source notices; it does not assert legal compatibility of a future
derivative. External test assets and their rights were not reviewed.

### Documentation and unsuccessful retrievals

Failures are preserved here even when source code answered the same question.
Search-index text is navigation/context only and does not become an immutable
documentation review.

| Attempt on 2026-10-03 | Outcome and evidence treatment |
| --- | --- |
| [Official project-host DNA source at v4.3.0][project-dna] | Web tool reported inaccessible. Exact implementation was subsequently fetched from the official GitHub mirror at the full commit (S01). |
| [GitHub v4.3.0 tree][tag-tree] | Web tool returned cache miss; connector tag/directory/file retrieval succeeded. |
| [Architecture, normalized URL][architecture] and [indexed double-slash URL][architecture-index] | Normalized direct fetch returned HTTP 402. Search returned indexed content; no complete pinned document revision or documentation terms were established. S01–S06 provide independently retrieved implementation evidence for the scoped data claims. |
| [4.3 migration documentation][migration-doc] | Direct fetch returned HTTP 402; search returned indexed content. Documentation revision and terms remain unverified. S13, S15, S18 and S19 supply pinned implementation evidence, including helper invalidation. |
| [4.3 undo manual][undo-manual43] | Direct fetch was inaccessible. Search surfaced the mutable [latest undo manual][undo-manual]; this was not treated as a 4.3 document or immutable evidence. S10–S12 supply implementation evidence instead. |
| `source/blender/blenkernel/intern/undo_system_test.cc`, `source/blender/blenkernel/intern/blendfile_undo.cc`, `scripts/modules/_bpy_types.py` at the audited commit | Candidate paths failed connector retrieval. Corrected paths, directory inventories and CMake registrations were inspected; a failed guessed test path is not proof that no such tests exist anywhere. |

The successful source files do not retroactively change the failed documentation
fetches into successes. A full documentation revision/terms review remains open.

## Observations and implications

“Supported” below means a narrowly described behavior is visible in pinned
source. “Partial” means only part of the Foundry obligation has evidence.
“Unsupported” means this review cannot substantiate the proposed guarantee,
sometimes with a concrete counterexample. “Inaccessible” applies to the failed
material above. None of these labels is an admission or test-execution result.

### SD-01: document, attributes, identity and ownership — partial

**Observed.** S01 represents a Grease Pencil data-block with a layer tree,
drawings array, material array and layer custom data. A drawing embeds
`CurvesGeometry`; layer frames refer to drawings by array index. S02 stores
contiguous point attributes, curve attributes and offsets delimiting each curve.
Offsets require at least one point per curve. S06's stroke creation writes point
position, radius, opacity, optional vertex color, point-relative time, and curve
material index, cyclicity, softness, caps and initial time. This is positive
evidence for ordered samples and typed attribute domains, not a universal brush
contract. [S01][s1] [S02][s2] [S06][s6]

**Identity counterexamples.** S18 explicitly invalidates a previously obtained
stroke slice when point/curve counts change; S19's helpers retain drawing plus
curve/point indices and write attributes through those indices. S04 compacts the
drawing array and remaps frame indices when removing unused drawings. S20's
`remove_drawings_with_no_users` asserts changed drawing indices after that
operation. A data-block ID or array index therefore cannot be promoted into
a stable external stroke ID. No persistent document/stroke/brush value-ID
contract was found in these paths. [S18][s18] [S19][s19] [S04][s4] [S20][s20]

**Ownership counterexample.** S03 permits multiple frames to share a drawing and
allows each user to mutate it. S05 uses shared offset storage and
`CustomData_init_from` during geometry copies, with writable-offset handling
through implicit-sharing helpers. This is concrete storage/ownership machinery,
but it is not evidence that every public object is immutable or that arbitrary
references remain safe across edits. [S03][s3] [S05][s5]

**Validation observed.** S16 routes RNA add/remove/resize calls to S17. Those
helpers reject nonpositive curve sizes, out-of-range indices, unsorted or
duplicate indices, and inconsistent size/index counts before the corresponding
mutation call. This is a real bounded validation example. It does not prove
finite-coordinate checks, typed brush-version resolution, a document revision
counter, arbitrary channel validation or point/stroke/byte budgets. [S16][s16]
[S17][s17]

**Foundry implication.** Retain ordered samples, explicit attribute domains and
validation-before-mutation as comparison-backed candidates. Retain stable IDs,
external reference lifetime and immutable ownership only as explicitly designed
and independently reviewed Foundry obligations. Do not equate a material slot,
a brush used to generate a stroke, and a durable brush contract/version.

### SD-02: coordinate context — partial

**Observed.** S04's `Layer::to_world_space` composes object/layer transforms or
parent transform, parent inverse and layer transform. The armature-parent path
also depends on a pose-bone transform. S08 captures layer-to-world and inverse
matrices, derives projection from scene/view settings and transforms projected
world coordinates into layer space. S09 passes layer-to-world transforms into the
editor's transform machinery; auto-keying can duplicate a frame before editing.
These are positive examples of separating stored local points from placement.
[S04][s4] [S08][s8] [S09][s9]

S03 documents radius in Blender units and the legacy thickness-to-radius factor
of 1/2000; S13 applies that conversion before pressure scaling. The architecture
search excerpt uses a meters description, but the pinned source's Blender-unit
convention is the reviewed evidence. Do not silently infer SI metadata or a
unit-scale conversion from that excerpt. [S03][s3] [S13][s13]

**Unverified.** These files do not establish the proposed interchange basis,
handedness declaration, per-document unit metadata, nonuniform/negative/zero
scale rejection, precision tolerance, origin rebasing or XR host-target-loss
behavior. S08's projection may fall back to view placement when depth is absent;
that is an editor policy, not proof of explicit missing-target failure.

**Foundry implication.** Retain an explicit document-local frame and adapter
conversion seam. Basis/units and transform failure rules need independent
fixtures and a deliberate narrower contract. A replay must capture resolved
positions/transforms if it is to avoid consulting changing view, scene or parent
state; Blender's interactive projection is not that replay guarantee.

### SD-04: structural edits and local history — partial

**Observed edit paths.** S06 creates a curve and writes its attributes directly.
S07's delete operator removes selected curves or replaces geometry with the
result of point removal/splitting; its duplicate operator mutates selected
curves/points. Both update geometry/notifiers and register undo support. S05
implements curve removal by assigning geometry built from the retained
selection; removing everything assigns empty geometry. S09 supplies transform
data and cache updates within Blender's editing context. [S06][s6] [S07][s7]
[S05][s5] [S09][s9]

These are real create/delete/replace/transform mechanisms. They do not define
Foundry-style whole-stroke transactions, expected-revision refusal, cross-drawing
all-or-nothing commit, rollback on allocation failure, or cancellation with no
history entry. An undo-enabled operator flag alone proves none of those.

**Observed undo ownership and restoration.** S10 stores drawing geometry or
drawing references, indices/flags, layer tree/custom data and an active-node
name per object. Decode resizes the drawing array, reestablishes drawing types,
assigns saved geometry, restores layers and active node, and invalidates
topology. Blender object/scene references and editor-mode restoration are part
of the operation. The implementation restores snapshots; it does not replay an
attributed stroke-command journal. It uses S05's geometry copy/assignment
machinery rather than demonstrating an engine-neutral immutable snapshot API.
[S10][s10] [S05][s5]

**Divergent edits: supported narrowly.** S11 clears undo steps after the active
step when pushing a new step (L539–544), providing direct evidence for redo
truncation. It performs that clearing before attempting step encoding
(L588–591). The possibility of a later encode failure returning failure after
the redo branch has been cleared is a concrete reason not to infer
“every failed action leaves history unchanged” from this implementation.
[S11][s11]

**Limits: supported mechanism, unproven hard resource guarantee.** S12 reads
configured undo steps and memory and calls S11's limit function. S11 counts
non-skipped steps, sums `UndoStep.data_size`, retains a minimum history and can
preserve a memfile step outside ordinary eviction. S10's complete Grease Pencil
encoder does not assign `step.data_size`. Thus the general limit algorithm and
step eviction are visible, but exact GP snapshot memory accounting and a strict
cap on retained bytes are not established. Disabled/unavailable history and
global/edit-mode interactions also depend on editor policy. [S12][s12]
[S11][s11] [S10][s10]

**Foundry implication.** Local snapshot restoration, redo truncation and explicit
history policy have independent precedent. Keep atomic validation/rollback,
stable-ID restoration, cancellation and resource-accounting guarantees as open
requirements; narrow or defer any mandatory claim lacking further evidence.
Do not transplant Blender's global editor history into the proposed kernel.

### SD-05: one write path, snapshot and deterministic replay — unsupported as a whole

**Observed.** S16 exposes add/remove/resize RNA mutations, S19 exposes direct
attribute setters, and S07/S06 contain editor/paint paths. These are multiple
application entry paths sharing some lower-level structures, not a demonstrated
single attributed revision-checked intent interface. None of the inspected
signatures establishes actor attribution, expected revision or
`state.stale`. [S16][s16] [S19][s19] [S07][s7] [S06][s6]

S06 initializes a fresh random generator and reads the current clock at stroke
start. It then stores resolved attributes and time values. Reusing the same
abstract gesture/brush parameters is consequently insufficient evidence for
identical regenerated data. Stored `delta_time` and `init_time` are useful
sample metadata, not proof of a deterministic edit-log format, canonical
fingerprint, numerical encoding or replay seed persistence. S10's snapshot undo
does not supply those missing replay properties. [S06][s6] [S10][s10]

**Foundry implication.** Distinguish restoring a saved document from reproducing
it through input or commands. Keep one attributed intent seam as Foundry
synthesis requiring its own source justification and tests. If deterministic
replay remains mandatory, capture every input-derived value and relevant
random/time/space decision, define canonical serialization and test it. No
geometry/pixel determinism follows from document equality.

### SD-06: persistence and migration — partial

**Observed serialization.** S04 writes/reads drawing data, layer tree, layer
custom data, material pointers and vertex-group names. S05 serializes point and
curve custom-data arrays and offsets, then reconstructs runtime data/type
caches on read. That is actual persistent stroke data separate from runtime
caches, within the Blender `.blend`/ID system. It is not a standalone Foundry
versioned DTO or a compatible interchange promise. [S04][s4] [S05][s5]

**Observed migration and loss.** S13 converts legacy polyline/Bezier drawing data
into curve/point domains. It combines legacy thickness and pressure into radii,
maps strength to opacity, transfers point time in the polyline path, derives
softness from hardness and transfers material indices. Zero-point legacy
strokes are skipped; initial stroke time is converted through millisecond
integer/float representation. Its `legacy_main` separates annotations and leaves
annotation data in the legacy representation while remapping object Grease
Pencil IDs. These are important semantic transformations, not proof of lossless
round trips or stable stroke-ID preservation. [S13][s13]

S15 also contains explicit file-version-gated radius scaling (before version
401.1) and hardness-to-softness conversion (before 402.38). A schema/version
migration mechanism is visible, but the scoped code does not establish a
machine-readable report of all unsupported brushes or format losses.
[S15][s15]

**Observed save failure handling.** S14 writes a temporary file, removes it on
write failure, then handles version backups and renames the successful temporary
file over the destination. It reports backup/rename failures. This is useful
staged-save precedent, but backup rotation precedes the final rename; the
review does not establish the stronger invariant that every failure/crash
leaves the prior committed save at exactly the original pathname. No failure
injection or filesystem durability test was run. [S14][s14]

**Open boundary.** Corrupt/truncated/oversize/unknown-version rejection before
live-state replacement, no external URL fetching, sandboxed untrusted import,
persistent history, and Foundry Persistence integration were not established by
these selected serializers. Generic blend-file tests below are not substitutes
for hostile-input and Grease Pencil identity/fidelity fixtures.

**Foundry implication.** Retain versioned persistence, separated runtime caches
and explicit migration/loss diagnostics as design targets. Defer Blender
interchange and persistent undo history. Require dedicated malformed-input,
migration and failed-save tests through the existing Persistence seam.

### SD-07: adapters and editor/renderer coupling — partial, with counterexamples

S02 intentionally separates reusable curve storage from ID data-block handling.
S03 places triangulation, normals and texture matrices in runtime caches;
S04 invalidates those caches when geometry changes. This supports distinguishing
authoritative samples from derived geometry. [S02][s2] [S03][s3] [S04][s4]

However, S06 uses active object, material/brush, scene, region, evaluated object
and viewport depth. S09 consults scene/time/dependency-graph state. S10 restores
editor object mode/scene context, resolves an active node by name and triggers
dependency-graph/UI notifications; S11 uses the application-wide main state.
These are explicit coupling examples, not fake-port dependency-inversion proof.
No renderer-cache-failure isolation, explicit construction/disposal test or
missing-brush/host-target contract was found in the scoped test inventory.
[S06][s6] [S09][s9] [S10][s10] [S11][s11]

**Foundry implication.** Retain data/derived-cache separation as evidence-backed
comparison. Engine-light ports, explicit bindings, missing-member failure and
independent renderer/input/storage lifecycles remain Foundry obligations that
must be implemented and tested independently.

### SD-10: license and import boundary — partial

Pinned file notices and root license files have been reviewed above; no source
or assets are incorporated. That supports factual architecture comparison and
the exclusion boundary. It does not clear dependency/asset rights for a future
package or establish security against malicious imports. GPL runtime files,
Apache-marked tests, documentation terms and unreviewed binary fixtures must
remain distinct. No import codec or compatible brush library is admitted.

## Test inventory (inspected, never executed)

All paths and symbols below refer to the same 4.3 commit. Inspection establishes
what assertions are present, not that they passed on this or any machine.

| Inventory | Actual assertions inspected | What it does not establish |
| --- | --- | --- |
| [S20: blenkernel Grease Pencil tests][s20] | `create_grease_pencil_id` checks empty drawings/tree; `add_empty_drawings` checks count; `remove_drawings`, `remove_drawings_last_unused`, `remove_drawings_no_change` and `remove_drawings_with_no_users` check counts and frame/index remapping. Layer-tree tests check traversal/order, node kinds, active-node fallback and removal. Frame tests check drawing lookup, duplicate start rejection, holds, duration and removal. | Stable external stroke IDs, all-attribute undo equality, exception rollback, corruption rejection, performance or device behavior. |
| [S21: editor merge tests][s21] | `merge_simple`, `merge_in_same_group`, `merge_in_different_group` assert layer counts/names, parent grouping and frame keys; `merge_keyframes` asserts resulting point counts; `merge_layer_attributes` checks merged float values (including averaging). | Generic transaction isolation or identity-preserving editing; merging may intentionally combine attributes. |
| [S22: Python Grease Pencil API][s22] | Creation and layer rename/remove/move tests assert names/order/counts. `test_grease_pencil_drawing_add_strokes`, removal, resize, point-add/remove and slice tests assert resulting stroke/point counts and slice behavior. Removal of indices 0 and 2 leaves the former 5- and 11-point strokes; over-removal via the stroke helper retains a point. | Tests do not assert actor/revision rejection, finite points, serialized units, undo/redo, randomized replay or full channel fidelity. |
| [S23: UI undo tests][s23] | `view3d_simple` creates/duplicates/joins/subdivides meshes, checks object/polygon counts, undoes to zero objects and redoes to 16 polygons. Other listed functions exercise text, mesh, sculpt, texture-paint and multi-window/mode scenarios. | No Grease Pencil-specific test function occurs in this file's inspected inventory. General editor undo assertions are not GP stroke-attribute proof. |
| [S24: blend-file versioning][s24] | `test_open`, `test_link`, `test_append` traverse supplied blend files and exercise loading/linking/appending. The script has named broken-file exclusions and platform-specific exclusions. | The fixture set was not retrieved or licensed here. No GP migration golden-value/ID/loss-report assertion was established by inspecting this harness. |
| [S25: blend-file IO][s25] | `TestBlendFileSaveLoadBasic.test_save_load` compares converted data tuples before/after save and reload; partial-save tests check object/mesh/material presence and users; runtime-tag tests inspect save/load/linking behavior. | No GP-specific malformed/oversize import, save-failure injection or persistence of undo history was established. |

Registration was also inspected: kernel CMake includes
`intern/grease_pencil_test.cc`; editor CMake registers
`tests/grease_pencil_merge_test.cc` under its GTest configuration; Python CMake
registers `script_pyapi_grease_pencil` and a specific `WITH_UI_TESTS` undo list.
Python CMake also names Grease Pencil rendering/geometry-node test groups.
Those entries are inventory leads only: their external assets, detailed
assertions and execution were not reviewed. [Kernel registration][cmake-kernel]
[Editor registration][cmake-editor] [Python registration][cmake-python]

## Comparison and exact next source-gate review

Blender is **one** independent implementation lineage. As already recorded in
[source-to-capability.md](source-to-capability.md), Open Brush and MultiBrush
share the Tilt Brush lineage; MultiBrush is experience-only/proprietary material.
InkML supplies normative vocabulary rather than a second implemented history
system. Three.js is an input/render example, and the recorded Remote Assist
material is product behavior rather than reusable document/edit implementation.
This audit does not add another source hunt or count pages/tests as lineages.

Answered questions:

1. Is there an independent retained stroke representation with ordered points?
   **Yes**, curve offsets and point/curve attribute domains are directly visible.
2. Does it use local geometry and separate derived caches?
   **Yes**, with substantial Blender-specific scene, layer, material and editor
   coupling.
3. Are there real structural edit, snapshot undo, redo-truncation and history
   eviction implementations? **Yes**, within Blender's editor; transactional
   rollback, stable external IDs and a strict GP byte cap do not follow.
4. Is persistence/migration implemented? **Yes**, with concrete conversion and
   loss cases. A secure, lossless Foundry import/DTO contract does not follow.
5. Are relevant tests and licenses identifiable? **Yes**, at this pin; none of
   those tests was executed and external fixtures were not reviewed.

The exact next review is a capability-by-capability source-gate assessment of
this audit together with the already pinned Open Brush/InkML evidence: mark each
mandatory clause retained, narrowed or deferred; resolve identity/ownership,
transaction failure and history accounting; distinguish snapshot restore from
deterministic replay; specify basis/units and migration loss reporting; and
complete selected dependency/asset/fixture rights review. A reviewer must also
decide whether the historical 4.3 baseline is sufficient or require a separately
pinned current-release comparison, especially for undo changes. Failed official
documentation retrieval and unresolved document revisions/terms remain visible
until actually resolved.

Research completion may accept explicit partial/unsupported findings under
WI-033. It does not set the family to admitted, close every blocker, complete
milestone 2b, create external-contributor evidence or authorize scaffolding.

## Repository acceptance record

Acceptance commands ran on 2026-10-03 for the audit tree committed as
`9cbad2f5f28f`; the closeout changes only this result record and WI-033 status/proof.
These checks validate repository structure/process, not Blender source truth or
runtime behavior.

| Command | Result |
| --- | --- |
| `python scripts/validate_repository.py --json` | PASS: repository contract validation. |
| `python -m unittest discover -s tests -p "test_*.py"` | PASS: 368 tests (65.231 seconds). |
| `python scripts/merge_readiness.py --base origin/main --head HEAD --markdown` | BLOCKED: all seven technical checks pass; independent review is UNKNOWN without PR metadata. Exit 1 is recorded, not suppressed. |

Blender tests: **not run**. Blender/Unity builds, renderer, headset, performance,
import-fidelity and clean-consumer validation: **not run**.

[s1]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/makesdna/DNA_grease_pencil_types.h
[s2]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/makesdna/DNA_curves_types.h
[s3]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/blenkernel/BKE_grease_pencil.hh
[s4]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/blenkernel/intern/grease_pencil.cc
[s5]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/blenkernel/intern/curves_geometry.cc
[s6]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/editors/sculpt_paint/grease_pencil_paint.cc
[s7]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/editors/grease_pencil/intern/grease_pencil_edit.cc
[s8]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/editors/grease_pencil/intern/grease_pencil_utils.cc
[s9]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/editors/transform/transform_convert_grease_pencil.cc
[s10]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/editors/grease_pencil/intern/grease_pencil_undo.cc
[s11]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/blenkernel/intern/undo_system.cc
[s12]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/editors/undo/ed_undo.cc
[s13]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/blenkernel/intern/grease_pencil_convert_legacy.cc
[s14]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/blenloader/intern/writefile.cc
[s15]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/blenloader/intern/versioning_400.cc
[s16]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/makesrna/intern/rna_grease_pencil_api.cc
[s17]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/makesrna/intern/rna_curves_api.cc
[s18]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/scripts/modules/bpy_types.py
[s19]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/scripts/modules/_bpy_internal/grease_pencil/stroke.py
[s20]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/blenkernel/intern/grease_pencil_test.cc
[s21]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/editors/grease_pencil/tests/grease_pencil_merge_test.cc
[s22]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/tests/python/bl_pyapi_grease_pencil.py
[s23]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/tests/python/ui_simulate/test_undo.py
[s24]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/tests/python/bl_blendfile_versioning.py
[s25]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/tests/python/bl_blendfile_io.py
[tag]: https://api.github.com/repos/blender/blender/git/ref/tags/v4.3.0
[revision]: https://github.com/blender/blender/commit/2b18cad88b138a1b16617c27540858fba59e66f5
[maintenance]: https://github.com/blender/blender/commit/bbfc8f3ec2ecb3a214c59d3696f8ad06c70c4638
[undo-maintenance]: https://github.com/blender/blender/commit/69f5d770c4f17b1688af1f9dceb12bb84d1591af
[readme]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/README.md
[copying]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/COPYING
[gpl2]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/doc/license/GPL-license.txt
[gpl3]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/doc/license/GPL3-license.txt
[cmake-kernel]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/blenkernel/CMakeLists.txt
[cmake-editor]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/editors/grease_pencil/CMakeLists.txt
[cmake-python]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/tests/python/CMakeLists.txt
[memfile]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/editors/undo/memfile_undo.cc
[global-undo]: https://github.com/blender/blender/blob/2b18cad88b138a1b16617c27540858fba59e66f5/source/blender/blenkernel/intern/blender_undo.cc
[project-dna]: https://projects.blender.org/blender/blender/src/tag/v4.3.0/source/blender/makesdna/DNA_grease_pencil_types.h
[tag-tree]: https://github.com/blender/blender/tree/v4.3.0
[architecture]: https://developer.blender.org/docs/features/grease_pencil/architecture/
[architecture-index]: https://developer.blender.org/docs/features//grease_pencil/architecture/
[migration-doc]: https://developer.blender.org/docs/release_notes/4.3/grease_pencil_migration/
[undo-manual43]: https://docs.blender.org/manual/en/4.3/interface/undo_redo.html
[undo-manual]: https://docs.blender.org/manual/en/latest/interface/undo_redo.html

