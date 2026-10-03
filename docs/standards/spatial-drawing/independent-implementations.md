# Spatial drawing, annotation, and collaboration: independent source comparison

Research date: 2026-10-03 UTC. Status: public-source proposal evidence; no admission, implementation or runtime validation.

## Recommendation

Use **3D Slicer Markups** as the strongest newly inspected independent implementation for annotation identity, coordinate handling, editing, storage separation, and opt-in bounded history. Use **Hubs Foundation drawing plus its exact Networked A-Frame dependency** to distinguish transient shared ink from durable documents and to scope deferred collaboration. Retain **A-Painter** as a historical comparison only. The research papers below explain why a networked undo policy needs a separate decision and validation plan.

This supports a small stroke/document kernel with explicit coordinates and edit boundaries, an annotation extension/adapter for target attachment and semantic metadata, and a deferred collaboration layer. It does not demonstrate that every proposed atomicity, rollback, canonical replay, or convergence guarantee already exists upstream.

## Evidence method and scope

The repository's AGENTS.md, Foundry README/manifest, first batch, source-gate queue, system-admission rules, and spatial-drawing source manifest/matrix were read. Repository source was retrieved through read-only GitHub APIs at full commit IDs. Repository metadata and branch/path history are time-of-review observations. Papers were read from explicit arXiv versions; mutable official support pages supply only maintenance context.

No upstream implementation, artwork, sounds, models, fixtures, or paper figures are included in this report or copied into Foundry. No application, upstream test suite, network session, or headset was run. Source inspection is not successful-runtime evidence. Root licensing is recorded separately from the uncompleted dependency and asset audits.

## Selected sources and maintenance

| Source | Immutable review reference | Maintenance observation | Disposition |
| --- | --- | --- | --- |
| Slicer/Slicer | `f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e` | Unarchived; reviewed main commit dated 2026-10-01. The selected Markups node was last changed by [e4f214ec](https://github.com/Slicer/Slicer/commit/e4f214ec204fba6ebb259449f5182c5bc65ade21), 2026-09-25. | Independent annotation/edit implementation comparison |
| Hubs-Foundation/hubs | `986d07a758e9d1184cb355385c6460391bd238d0` | Unarchived; reviewed head dated 2026-08-23. Selected networked-drawing.js was last touched by [4a1d3404](https://github.com/Hubs-Foundation/hubs/commit/4a1d34042f166dfc868bc8f726930519b7e7811f), 2022-11-26. Recent repository work does not establish recent drawing-subsystem validation. | Retained collaboration implementation, with explicit maintenance caveat |
| Hubs-Foundation/networked-aframe | `6093c3a0b2867a9e141cd5c19f7d13dfa7c38479` | Exact dependency identified in Hubs' pinned package.json; not an independently selected current NAF release. | Part of the Hubs architectural example |
| aframevr/a-painter | `0deba1f3314ee4cd053bf2a2ae2854994014dd65` | Unarchived, but master commit dated 2022-10-26; selected brush system last touched 2022-03-31. Repository push timestamp 2024-03-28 is not proof of a newer implementation. | Historical reference only |

Mozilla ended its Hubs service support on 2024-05-31 and identifies Hubs Foundation as the codebase's successor. Do not label the reviewed Foundation repository as archived Mozilla service code. Conversely, Foundation documentation explicitly warns that substantial content is outdated. [Mozilla support notice](https://support.mozilla.org/en-US/kb/end-support-mozilla-hubs); [Foundation documentation notice](https://docs.hubsfoundation.org/).

Open Brush/MultiBrush remain one Tilt Brush lineage. Slicer is materially independent. Hubs and its NAF dependency are one architectural example, not two independent drawing implementations. A-Painter shares the A-Frame/Mozilla ecosystem; no separate-independence credit should be inferred merely from its different repository name. Its exact code genealogy relative to Hubs was not audited.

## 1. Slicer: annotation is more than a painted polyline

### Retained state and ownership

A Markups node retains an ordered list of control points. Each point has an ID, position, orientation, label, description, associated-node ID, selection/lock/visibility flags, and position status. Position can be undefined, preview, defined, or missing; undefined coordinates must not be treated as an actual origin point. Coordinates are local to the markup, with explicit world-coordinate accessors. These are stronger annotation semantics than a visual tube alone. [Node header](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Libs/MRML/Core/vtkMRMLMarkupsNode.h#L49).

The node owns the control-point objects: removal deletes the point and updates retained geometry/measurements; destruction clears them. CopyContent deep-copies the points at this revision. This is mutable application state with explicit lifecycle management, not an immutable value document. Auto-generated point IDs come from a node-local incrementing counter; AddControlPoint generates one only when the supplied ID is empty. This is not evidence for globally unique stroke IDs or rejection of duplicate externally supplied IDs. [Node implementation: copy](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Libs/MRML/Core/vtkMRMLMarkupsNode.cxx#L163), [add](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Libs/MRML/Core/vtkMRMLMarkupsNode.cxx#L601), [remove](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Libs/MRML/Core/vtkMRMLMarkupsNode.cxx#L814), [ID generation](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Libs/MRML/Core/vtkMRMLMarkupsNode.cxx#L1934).

### Edits, locking, and history

The implementation supports point insertion/removal, position edits, and transforms, with point-level events and measurement recomputation. A transform overload controls whether locked points participate. Locking therefore belongs to an explicit editing policy; a lock flag must not be described as a universal security or access-control guarantee. An event blocker or batched notifications also does not establish transaction rollback. [Transform implementation](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Libs/MRML/Core/vtkMRMLMarkupsNode.cxx#L1798).

The Markups widget calls scene SaveStateForUndo before actions such as reset, snap-to-slice, and point placement. Scene history defaults to **20 saved undo states but is disabled by default**. When enabled, SaveStateForUndo clears redo, retains scene structure and copies selected undo-enabled node state; Undo restores changed/deleted nodes and removes nodes absent from the prior state; TrimUndoStack removes oldest entries. Calls are skipped in relevant undo/batch conditions. This is independent evidence for explicit history capture, bounded snapshots, and redo invalidation, with scene-level coupling. It does not prove a renderer-free transaction API or persisted undo history. [Widget calls](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Modules/Loadable/Markups/VTKWidgets/vtkSlicerMarkupsWidget.cxx#L243), [placement](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Modules/Loadable/Markups/VTKWidgets/vtkSlicerMarkupsWidget.cxx#L1176), [scene defaults](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Libs/MRML/Core/vtkMRMLScene.cxx#L146), [capture](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Libs/MRML/Core/vtkMRMLScene.cxx#L2720), [undo](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Libs/MRML/Core/vtkMRMLScene.cxx#L2961), [eviction](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Libs/MRML/Core/vtkMRMLScene.cxx#L3950).

### Storage and coordinates

The JSON storage node writes markup type, coordinate system, units, point metadata, optional measurements, and display state through distinct functions. Point ID and associated-node ID are serialized separately from position. The writer explicitly accepts RAS/LPS and flips the first two coordinate axes for LPS output; it also converts orientation. Non-defined points are written without a numeric position. The reader checks position/orientation array shape and position-status values. This is valuable evidence for a codec boundary and explicit conversion, not permission to impose medical coordinate conventions on XR. [Storage implementation](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Modules/Loadable/Markups/MRML/vtkMRMLMarkupsJsonStorageNode.cxx#L919), [point reader](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Modules/Loadable/Markups/MRML/vtkMRMLMarkupsJsonStorageNode.cxx#L730), [schema v1.0.4](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Modules/Loadable/Markups/Resources/Schema/markups-schema-v1.0.4.json).

The source preserves an old master-branch URL as the schema identifier for compatibility. A schema identifier and a retrievable source URL are distinct concepts. Foundry should version its durable schema deliberately and test migrations, rather than treating a branch URL as an immutable schema. [Compatibility comment](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Modules/Loadable/Markups/MRML/vtkMRMLMarkupsJsonStorageNode.cxx#L39).

No claim is made that this reader is fully atomic, scales all units, validates every malformed document, or preserves an undo stack. The inspected coordinateUnits read path contains a mismatch-checking intention, but intention/comments are not sufficient proof of enforced conversion or rejection.

### Tests and license boundary

Read test sources include:
- [vtkMRMLMarkupsNodeEventsTest.cxx](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Modules/Loadable/Markups/Testing/Cxx/vtkMRMLMarkupsNodeEventsTest.cxx): checks add/remove, lock, defined/undefined/missing, modification, and fixed-point-count event occurrence.
- [MarkupsCurveCoordinateFrameTest.py](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/Modules/Loadable/Markups/Testing/Python/MarkupsCurveCoordinateFrameTest.py): checks expected coordinate-frame matrices for several curve cases.

These tests were inspected, not executed. They do not establish rollback, multiplayer behavior, Foundry integration, or device results.

Selected C++ files carry a Brigham and Women's Hospital copyright header referring to COPYRIGHT.txt. The repository's [License.txt](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/License.txt) and [COPYRIGHT.txt](https://github.com/Slicer/Slicer/blob/f1b7931d4dfc3a3a6b8db47902019382f4a0bf9e/COPYRIGHT.txt) contain the **3D Slicer Contribution and Software License Agreement, version 1.0**, described there as BSD-style with extensions. Do not relabel it unqualified BSD-3-Clause. VTK/ITK/Qt, extensions, datasets, and other assets remain separate audit subjects. This report uses architectural observations only.

## 2. Hubs: shared transient ink has different guarantees from a document

### State, writer, and network behavior

The drawing manager creates a networked drawing entity and assigns its current drawing to a pen. Its implementation explicitly leaves multiple-drawing handling as future work. The pen supplies world positions, direction, normal, color, and radius to drawing calls; it offers 3D and projection modes. These are host/input responsibilities, not neutral document rules. [Drawing manager](https://github.com/Hubs-Foundation/hubs/blob/986d07a758e9d1184cb355385c6460391bd238d0/src/components/tools/drawing-manager.js); [pen implementation](https://github.com/Hubs-Foundation/hubs/blob/986d07a758e9d1184cb355385c6460391bd238d0/src/components/tools/pen.js#L189).

The drawing component combines a procedural tube mesh, geometry buffers, network buffers, and per-line geometry/buffer counts. Its defaults are 8 tube segments, radius 0.01, maximum line lifetime **600000 ms**, **50** completed lines, and **250** points per line. The code can end a line after the point cap; exact boundary behavior requires tests. Expiration uses the host's elapsed time and removes old geometry; this is deliberate transient-ink policy, not a universal drawing-document retention rule. [Drawing state/defaults](https://github.com/Hubs-Foundation/hubs/blob/986d07a758e9d1184cb355385c6460391bd238d0/src/components/tools/networked-drawing.js#L27), [expiry](https://github.com/Hubs-Foundation/hubs/blob/986d07a758e9d1184cb355385c6460391bd238d0/src/components/tools/networked-drawing.js#L351), [line history time](https://github.com/Hubs-Foundation/hubs/blob/986d07a758e9d1184cb355385c6460391bd238d0/src/components/tools/networked-drawing.js#L545).

Only the network owner appends point samples and broadcasts the drawing buffer. Non-owners ask the owner for initialization. Current contents can be sent in chunks of 3000 buffer elements; incremental messages are consumed after full initialization. Sequence-count checks detect out-of-order points and skip drawing invalid line segments. This is owner-streamed replication. It is not a CRDT, offline merge contract, exactly-once protocol, or proof of reconnect recovery. Calls named sendDataGuaranteed delegate to the selected transport; the name alone does not establish an end-to-end durability guarantee. [Streaming/receive paths](https://github.com/Hubs-Foundation/hubs/blob/986d07a758e9d1184cb355385c6460391bd238d0/src/components/tools/networked-drawing.js#L129), [buffer send](https://github.com/Hubs-Foundation/hubs/blob/986d07a758e9d1184cb355385c6460391bd238d0/src/components/tools/networked-drawing.js#L371), [owner append](https://github.com/Hubs-Foundation/hubs/blob/986d07a758e9d1184cb355385c6460391bd238d0/src/components/tools/networked-drawing.js#L567), [NAF transport delegation](https://github.com/Hubs-Foundation/networked-aframe/blob/6093c3a0b2867a9e141cd5c19f7d13dfa7c38479/src/NetworkConnection.js#L156).

### Authority is not authorship or conflict-preserving editing

Hubs pins NAF to the exact ref above in [package.json](https://github.com/Hubs-Foundation/hubs/blob/986d07a758e9d1184cb355385c6460391bd238d0/package.json). At that revision, takeOwnership records server time, assigns the local client as owner, and synchronizes. Receiving entity updates compares lastOwnerTime and uses owner-string order on a tie. The owner can synchronize; the creator may synchronize if the owner has left, with object lifetime described as tied to the creator. These are entity authority/lifecycle rules. They do not preserve two simultaneous edits to the same stroke. [NAF ownership](https://github.com/Hubs-Foundation/networked-aframe/blob/6093c3a0b2867a9e141cd5c19f7d13dfa7c38479/src/components/networked.js#L219), [sync and owner comparison](https://github.com/Hubs-Foundation/networked-aframe/blob/6093c3a0b2867a9e141cd5c19f7d13dfa7c38479/src/components/networked.js#L450).

The drawing data channel and NAF entity-update path are distinct. This review did not audit the complete server authorization path or claim the custom drawing receiver inherits every entity-update check. Hubs' network schemas refer to application/server permission handling. [Schema boundary](https://github.com/Hubs-Foundation/hubs/blob/986d07a758e9d1184cb355385c6460391bd238d0/src/network-schemas.js#L21).

### Undo and persistence are separate paths

undoDraw removes the last recorded geometry/buffer portion and enqueues a minus marker. Broadcasting strips these markers from the retained buffer after sending, so a late join gets the resulting current state rather than the past undo operations. No redo path appears in the inspected drawing component. This is not a durable edit log or selective collaborative undo. [Undo](https://github.com/Hubs-Foundation/hubs/blob/986d07a758e9d1184cb355385c6460391bd238d0/src/components/tools/networked-drawing.js#L487), [marker removal](https://github.com/Hubs-Foundation/hubs/blob/986d07a758e9d1184cb355385c6460391bd238d0/src/components/tools/networked-drawing.js#L271).

serializeDrawing exports a trimmed mesh as GLB plus a custom MOZ_hubs_components networked-drawing-buffer extension, then passes the file to the application's media path. A separate deserialize action obtains ownership, recreates editable drawing, and removes the media object; an existing drawing is serialized first. This shows that a visible mesh export and an editable document representation are distinct concerns. It does not prove portable round-trip support in arbitrary glTF viewers or atomic save/reload. [Serialization](https://github.com/Hubs-Foundation/hubs/blob/986d07a758e9d1184cb355385c6460391bd238d0/src/components/tools/networked-drawing.js#L192), [re-edit path](https://github.com/Hubs-Foundation/hubs/blob/986d07a758e9d1184cb355385c6460391bd238d0/src/components/tools/networked-drawing.js#L755).

### Tests and license boundary

The pinned package declares lint/type-check/build and AVA unit-test tooling. The inspected repository tree exposes a component-mappings unit test and browser-stack tests; no drawing-specific test was located in that inventory. This is a limited source inventory, not proof that none exists in any external CI suite. No tests were run.

Hubs declares [MPL-2.0](https://github.com/Hubs-Foundation/hubs/blob/986d07a758e9d1184cb355385c6460391bd238d0/LICENSE); the selected drawing/pen files begin with comments/imports rather than a separate license grant. Its pinned NAF dependency has a separate [MIT license, copyright Hayden Lee](https://github.com/Hubs-Foundation/networked-aframe/blob/6093c3a0b2867a9e141cd5c19f7d13dfa7c38479/LICENSE). The package includes several other forks/dependencies. Root Hubs licensing is not a completed audit of those dependencies or its GLB, textures, sounds, icons, or imported user content. Copy no implementation or assets under this proposal.

## 3. A-Painter: useful historical counterexample, not a maintenance shortcut

The pinned brush system retains samples containing position, orientation, pressure, and timestamp, with brush color/size and an owner value. It supports JSON and binary serialization with version information and a brush table; loading reconstructs strokes by replaying points through brush implementations. Undo searches backward for the last locally owned stroke, removes it, calls brush-specific undo, and emits a scene event. The inspected JSON representation does not serialize the owner field or a stable stroke ID. The add path can fall back to the first registered brush when a brush name is unknown. Consequently, the source does not establish stable identity, fail-closed brush-version resolution, or exact deterministic round trips. [Brush system](https://github.com/aframevr/a-painter/blob/0deba1f3314ee4cd053bf2a2ae2854994014dd65/src/systems/brush.js#L35), [undo](https://github.com/aframevr/a-painter/blob/0deba1f3314ee4cd053bf2a2ae2854994014dd65/src/systems/brush.js#L152), [creation/serialization](https://github.com/aframevr/a-painter/blob/0deba1f3314ee4cd053bf2a2ae2854994014dd65/src/systems/brush.js#L309).

The painter layer separately saves JSON/binary files and provides an upload flow. That is separation of responsibilities within an application, not evidence that the drawing kernel must own remote storage. [Painter](https://github.com/aframevr/a-painter/blob/0deba1f3314ee4cd053bf2a2ae2854994014dd65/src/systems/painter.js#L183).

The [root license](https://github.com/aframevr/a-painter/blob/0deba1f3314ee4cd053bf2a2ae2854994014dd65/LICENSE) is MIT, copyright A-Frame authors. Selected JS files have globals comments rather than independent grants. Vendor code and brush/image/sound assets were not individually audited. The pinned [package scripts](https://github.com/aframevr/a-painter/blob/0deba1f3314ee4cd053bf2a2ae2854994014dd65/package.json) show build and lint tooling, with no test script. No runtime/testing claim follows from the old demo remaining online.

## 4. Original research: constrain the deferred collaboration contract

**Stewen and Kleppmann, PaPoC 2024, “Undo and Redo Support for Replicated Registers,” [arXiv:2404.11308v1](https://arxiv.org/html/2404.11308v1).** The authors distinguish global undo, local undo, and blocking undo after a remote change. Their local-undo definition can also reverse another user's intervening value on the same register; “undo my action” is therefore not synonymous with “never affect your work.” Their proposed register algorithm uses operation identity and causal dependencies, with local undo/redo stacks. It is a research prototype for multi-valued registers, not a validated stroke/tree/scene algorithm. The paper is CC BY 4.0; no algorithm code or figures are reproduced.

**Rasch, Perzl, Weiss, and Müller, CHI 2024, “Just Undo It,” [arXiv:2403.11756v1](https://arxiv.org/html/2403.11756v1).** A controlled study of 32 people in pairs compared individual, selective, and world undo in tower construction. The authors found tradeoffs involving interference and social connection, and warn that the artificial task, two-person scale, and definitions of object ownership limit generalization. This supports explicit product-level undo scope and user evaluation. It does not determine the right drawing undo policy or supply Foundry device evidence. The version carries the arXiv non-exclusive distribution license; no text passages, figures, or study assets are reused.

## 5. Concrete Foundry implications

These are proposed synthesis, not upstream guarantees or admission decisions.

| Boundary | Keep or defer | Evidence-driven consequence |
| --- | --- | --- |
| Stroke/document state | Small candidate Core | Retain ordered samples, explicit brush parameters, coordinates, identity and lifecycle. Keep UI selection, mesh buffers, controller state and transport out. |
| Identifiers | Explicit Core validation proposal | Distinguish document/stroke ID, point index, host target ID, author ID and network owner. Slicer's local IDs and Hubs' owner IDs do not supply a universal identity contract. |
| Input session | Input/interaction adapter | Distinguish in-progress preview, committed stroke, cancellation and tracking interruption. Annotation missing/unresolved state must not silently become a point at zero. |
| Annotation | Optional typed extension/adapter | Attach drawing/markup to a stable host target, keep target resolution and local/world conversion explicit, and separate semantic label/description/measurement from raw ink. Domain ontologies, clinical quantities and host scene IDs stay out of common Core. |
| Undo | Explicit local history seam | Define capture/commit boundaries, eviction and redo invalidation. Source-backed history patterns differ; none of these comparisons alone proves all-or-nothing multi-stroke transactions. |
| Serialization | Codec plus Persistence integration | Editable state and rendered export need separate contracts. Define schema versions, required/optional channels, unknown-brush policy, units and bounds. Storage destinations and authentication remain outside Core. |
| Collaboration | Defer as a separate adapter/extension | Decide owner transfer versus concurrent edits, durable state versus transient previews, expiry, late join, reconnect, duplicate/out-of-order delivery and user-visible undo scope before implementation. |

The smallest useful verification plan should exercise:
1. Two strokes created/deleted/replaced with stable IDs; reject invalid identity before mutation.
2. Commit/cancel and undo/redo around point sampling, including an interrupted input session.
3. History-cap eviction and edit-after-undo redo invalidation, with a documented lifetime policy.
4. Save/reload of explicit coordinate units and frame conversion, including a moved host target and an unresolved target.
5. Renderer rebuild from retained state without importing mesh-buffer or scene references into the kernel.
6. Codec rejection or explicit migration for unsupported schema/brush versions, truncated data, and invalid sample dimensions.
7. If collaborative work is later admitted: simultaneous edit/delete, owner departure, reconnect/late join, undo after remote edits, and expiry must have chosen expected outcomes before tests are written.

Those cases would be original Foundry verification obligations. They require an admitted public implementation task and the repository's exact-consumer/device evidence routes before any corresponding compatibility or headset claim.

