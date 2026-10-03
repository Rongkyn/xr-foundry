# Source-to-capability review

Status: candidate assessment, **reference_only**, reviewed 2026-10-03. No mandatory
Core capability is admitted. Source IDs resolve through [the manifest](source-manifest.json).
Detailed observations, locations, licenses and inspected tests live in the
[Blender audit](blender-source-audit.md), [Open Brush audit](openbrush-source-audit.md),
[independent implementation comparison](independent-implementations.md) and
[standards/research notes](standards-and-research.md).

“Recurring basis” below means the underlying function is independently observed;
it does not transfer the stronger Foundry guarantees in the final column.

| Candidate capability | Independent observed basis | Proposed disposition and remaining question |
| --- | --- | --- |
| Ordered retained spatial samples and attributes | Open Brush stroke data/writer; Blender drawing/curve domains; Slicer Markups state; InkML channels | Retain a small document candidate. Define finite values, channel semantics and budgets; a material index is not a portable brush contract. |
| Durable identity and owned values | Slicer point IDs/serialized associated-node IDs; W3C canonical resource identity; Open Brush brush GUIDs | Retain explicit identity validation as a design obligation. Open Brush stroke GUIDs are regenerated and not in the reviewed save record; Blender indices can change. Neither proves stable external stroke identity or immutable snapshots. |
| Local coordinates and units | Open Brush canvas transforms; Blender layer-local points; Slicer local/world and RAS/LPS conversion; InkML channels/units | Retain explicit local frame and adapter conversion. Do not conflate writing-surface Z, medical RAS/LPS and XR axes. Exact basis, numeric tolerance and invalid-scale behavior still require reviewed fixtures. |
| Brush references and typed parameters | Open Brush brush GUID/size/color; Blender material and point attributes; InkML brush references | Retain a deliberately limited brush contract; shader/assets and pressure mapping remain outside Core. Cross-brush rendering equivalence is excluded. |
| Create/remove/replace and local undo | Open Brush command stacks; Blender structural edits/snapshot undo; Slicer edit capture and scene snapshots | Narrow first prototype to whole-stroke edits and local history. Atomic refusal/rollback and exact value restoration are Foundry tests to prove, not upstream guarantees. |
| History limits and redo invalidation | Blender general step limiting/redo clearing; Slicer opt-in 20-state default/eviction | Retain explicit count-based history policy. A strict byte ceiling is deferred until owned-memory accounting exists. Blender's GP encoder does not establish that accounting; undo enabled by default must not be assumed. |
| Snapshot/save and migration | Open Brush versioned sketch/container/metadata; Blender serialization/migration; Slicer JSON codec/schema | Retain versioned snapshot conversion through Persistence. Save, editable export and persisted history differ. Stage/validate before replace is a Foundry obligation; source load paths do not uniformly provide it. |
| Attributed write seam and stale refusal | Existing LESSON-011; public implementations expose differing entry paths | Retain as an existing Foundry architectural requirement. Do not falsely count local/network APIs or scene setters as equivalent compliance evidence. Apply the same validation to player, agent and import intents. |
| Canonical intent replay/fingerprint | Seed serialization and captured samples are partial inputs; no reviewed source establishes the whole contract | Defer beyond first prototype. Snapshot restore is the initial scope; later replay needs numeric encoding, captured inputs/time/seeds, operation order and explicit tests. Geometry/pixel determinism remains separate. |
| Data versus rendering/input | Open Brush retained data/geometry; Blender runtime caches; Slicer node/display/storage split; Three.js XR painter | Retain explicit ports as Foundry synthesis with fake-port tests. Upstream scene/editor coupling is not code to transplant. |
| Host-bound annotation | Slicer associated-node/status semantics; W3C body/target/state; historical Remote Assist experience | Optional annotation adapter/consumer. Missing target must be explicit; medical measurements, domain ontology, host scenes and anchor acquisition stay outside the stroke kernel. |
| Collaborative creation | Hubs/NAF owner streaming and late join; Yjs selective undo; original undo research | Defer implementation. Authority transfer, ephemeral lifetime, concurrent edits and user-visible undo scope need a separate explicit contract. No CRDT, offline convergence or durable journal is inferred. |

## Corrections and source independence

The earlier seed caveat repeated a stale StrokeData comment. The pinned
`open-brush-sketch-writer` **does serialize seeds** and uses hash-derived legacy
backfill. That corrects the fact without proving cross-runtime deterministic replay.
Its replacement-load path can clear current memory before parsing. Its stroke GUID
is distinct from persisted brush identity. Comments, names and successful build
jobs do not replace behavioral inspection or test receipts.

Open Brush and MultiBrush are **one Tilt Brush lineage**. Blender's many files
count as one implementation. Slicer is independent. Hubs plus its pinned NAF
fork are one architectural example; A-Painter remains historical comparison with
no extra independence credit because shared ecosystem/code genealogy was not
fully audited. W3C recommendations are normative evidence, not claims that these
applications implement either standard. Papers inform interaction choices and
limits, not maintained package or device evidence.

Blender behavior is pinned to 4.3, with later maintenance reported separately;
its inaccessible documentation is not counted as a completed review. Hubs' recent
repository head does not make its 2022 drawing code freshly verified. Open Brush's
pinned ProjectVersion and old README disagree, so neither source review nor the
README supplies Foundry compatibility.

The [comparative review](comparative-review.md) maps the remaining gate and the
[first prototype plan](prototype-plan.md) names future tests. The outcome remains
proposal-only until the precise mandatory kernel and evidence basis are reviewed
under the existing admission process.
