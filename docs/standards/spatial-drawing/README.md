# Spatial drawing and annotation candidate

Status: **proposal, not admitted** (`NEXT-SPATIAL-DRAWING`). No package IDs,
blueprints, staged implementation, catalog entries or authoritative admission are
created. This is a source-gate worksheet under the existing Foundry process, not
a new standard or governance rule. Capability declared: AI budget and clone only;
no Unity Editor or headset evidence is available from this authoring pass.

## Recommendation

Consider a small spatial stroke-document family, not an Open Brush clone. The
recurring need is retaining and editing marks independently of an application,
input rig and renderer. Standalone immersive painting and embedded annotation of
a host-owned model are materially different consumers. Neither is validated here.

Open Brush is reviewed implementation evidence, not a reusable UPM package to
transplant. Read the [comparative review](comparative-review.md) for the updated
source-gate assessment and [first experiment plan](prototype-plan.md). MultiBrush is a useful collaboration experience reference;
its Tilt Brush ancestry supplies no independent architecture evidence. Blender
provides an independent stroke-document lineage; Slicer provides annotation and
opt-in snapshot-history evidence. Hubs illustrates transient owner-streamed ink.
InkML supplies normative trace/metadata vocabulary. Those sources motivate a candidate, not the complete
proposed API: see [source manifest](source-manifest.json) and
[source-to-capability review](source-to-capability.md).

## Proposed boundary, subject to admission

| Layer | Owns | Does not own |
| --- | --- | --- |
| Engine-light document kernel | document/stroke identity, ordered point data, explicit space/units, brush references and typed parameters, validated edit boundary, snapshots | Unity types, input devices, shaders, file IO, scene discovery |
| Edit/history module, if source gate closes | whole-stroke edits; bounded local undo/redo; replay separately deferred | global editor history, collaborative conflict resolution |
| Input adapter | begin/sample/end/cancel gestures; tracking-validity and coordinate conversion; pressure/filter policies | direct state writes or product-wide input routing |
| Renderer adapter | geometry/cache lifetime, brush definition resolution, mesh/shader policy | authoritative point data, undo history, product art assets |
| Persistence/codec bridge | versioned DTO conversion, existing Persistence orchestration integration, explicit format loss diagnostics | a second storage framework, automatic cloud upload |
| Consumer composition | host-target identity, target lifetime, artwork, allowed brushes, UI and binding configuration | new public kernel rules derived from one product |

A brush reference identifies a declared brush contract/version; it never implies
that its shader or copyrighted asset is bundled. Basic width/color/opacity and
optional time/pressure/orientation channels are candidates, not promises that all
sources use an identical representation. Unsupported channel semantics must be
rejected or explicitly preserved as noninterpreted metadata, never guessed.

Coordinates need an explicit basis, unit scale and document-local frame. Host
placement resolves that frame; this candidate does not create a spatial-placement
or anchor system. Content distribution stays with a content-pack composition;
this candidate owns no pack loader, scene installer or asset marketplace. Do not
duplicate the separate content-pack/spatial-placement source-gate proposals.

Existing Interaction, Settings and Persistence seams are integration context, not
external positive evidence. The XR UI shell remains a proposal, not an installable
verified dependency. A painting toolbar could be a peer shell client after that
composition is admitted; the host must never depend on painting or its tooling.

## Proposed variations and exclusions

Consumer policy controls sample spacing/filtering, pressure mapping, point/stroke
budgets, allowed brushes, brush ranges, retention and save cadence. Defaults need
measurement; no brush count, latency, allocation or frame-rate budget is validated.
Spline smoothing, mesh batching, ribbon/tube generation, shaders, eraser hit-testing,
formats such as .tilt/InkML/glTF, surface projection and import/export fidelity are
adapter-specific. V1 may use whole-stroke edits rather than promise point cutting.

Multiplayer is optional and deferred. Local revision/actor attribution is not a
network protocol. Authority, concurrent undo, late join, ordering, ownership,
conflict resolution, abuse controls and shared-coordinate alignment need their
own evidence and design. No Photon SDK or proprietary MultiBrush material enters
Core. Brushes, artwork, branded UI, trademarked names, tutorial projects and
consumer code are excluded as derivation material.

## Next gate

Close the blockers in [admission.draft.json](admission.draft.json), confirm current
maintenance and immutable source versions, and independently review every
mandatory capability. Narrow or remove unsupported requirements. Only an explicit
admission plus public implementation task permits blueprint/scaffold work under
the existing process. [Verification contract](verification-contract.md) describes
future obligations; every clause is currently unexecuted.

**WI-033** is completed by the [pinned Blender audit](blender-source-audit.md).
**WI-034** records the broader comparison, corrections and prototype plan in
[work-items.json](../../contributing/work-items.json). Neither research completion
is system admission or proof of external contributor participation.
