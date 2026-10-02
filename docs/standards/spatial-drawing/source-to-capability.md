# Source-to-capability review

Status: candidate assessment; no mandatory Core capability is admitted. Source IDs
resolve through [the manifest](source-manifest.json). A fetched page is not a
reviewed immutable implementation. Indexed excerpts do not close a source gate.

| Candidate capability | Observed positive basis | Foundry synthesis / unresolved gate |
| --- | --- | --- |
| Ordered point samples and document/stroke identity | `open-brush-stroke-data`; `blender-architecture`; `inkml` traces | Stable value IDs, ownership and lifecycle rules are proposed. Pin independent implementations and test invalid identities/duplicate references. |
| Brush reference with width/color and optional channels | `open-brush-stroke-data`; `inkml` brush references; `blender-architecture` point attributes | Typed parameter/version contract is proposed. Different pressure/radius conventions and brush semantics must not be conflated. |
| Coordinate context and units | `open-brush-stroke` canvas transforms; `inkml` channel units/canvas transforms | An XR document basis and host-local frame are proposed, not prescribed by InkML. Confirm 3D conversion and scale rules independently. |
| Atomic create/delete/replace/transform | `open-brush-stroke` transforms; Blender migration documents mutable data hazards | Transaction validation, rollback and structured results are Foundry synthesis. Full independent edit implementation review is open. |
| Bounded undo/redo | `blender-undo` documents history behavior; Open Brush stroke code references undone geometry | `open-brush-command-tree` and `open-brush-brush-command` now provide pinned undo ordering and geometry lifecycle evidence. Full bounded-history, atomic rollback and independent implementation review remain open. |
| Snapshot/save and deterministic replay | Open Brush save copy and nonserialized random seed; Blender time attribute; InkML archival traces | Durable schema, canonical ordering, seeded rendering and replay fingerprint guarantees are proposed verification obligations, not established source behavior. Storage orchestration belongs to Persistence. |
| Input/render split | Open Brush data/geometry distinction; `unity-xri-input` component index | Engine-light separation is proposed; neither Unity index nor Open Brush's coupled scene implementation proves the new seam. |
| Multiplayer | `multibrush-launch` product behavior | Deferred adapter/extension; no independent architecture, licensed implementation, convergence or network evidence. |

Open Brush and MultiBrush count as **one Tilt Brush lineage**. Blender's several
pages count as **one independent implementation**, not several. W3C is a normative
source, not proof that Open Brush implements InkML. No such conformance is claimed.
Unity input documentation is adapter navigation, not a second stroke-document
implementation. Public popularity, an available tutorial or two proposed consumers
do not replace independent source evidence.

`remote-assist-annotations` provides an independent shipped-product example of
embedded spatial ink, color and erase/undo behavior, not an open implementation.
Its page references a deprecation notice, so it supplies historical recurrence,
not a current maintenance/support claim. `multibrush-privacy` confirms the
proprietary boundary. The old Three.js VR paint path failed. Directory inspection found the current `webxr_xr_paint.html`; `threejs-xr-paint` was fetched at an immutable ref and counts only as an independent engine-maintained input/render example, never undo/document/persistence evidence.

Pinned Three.js paints with elapsed-time-derived color, while Open Brush command
constructors read application/network time. Foundry deterministic replay is a
proposed stronger contract, requiring captured values; it is not a copied upstream
guarantee. Selected Open Brush source and Three.js are pinned; Blender excerpts
and other mutable documentation still require complete source-gate review.
