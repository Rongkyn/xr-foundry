# Spatial drawing candidate verification contract

All clauses below are **planned and unexecuted**. No test assembly or package
exists. These are proposed product obligations under existing Foundry gates, not
new governance. Before implementation, publish a coverage matrix binding each
clause to named tests; gaps stay explicit and cannot support promotion.

| Clause | Required future verification |
| --- | --- |
| SD-01 identities/data | Reject duplicate or missing document, stroke and brush identities; nonfinite coordinates; invalid width/opacity; unsupported channels; point/stroke/byte budget overflow. Rejection leaves document and revision unchanged. |
| SD-02 coordinate contract | Declare handedness, axes, units and document-local frame. Golden fixtures cover translation, rotation, uniform scale, parent reassignment and round trip to each adapter. Define zero/negative/nonuniform-scale rejection, precision tolerance, origin rebase and host target loss. Replayed input never rereads live poses. |
| SD-03 sample lifecycle | Begin/sample/end/cancel ordering, tracking loss/recovery and duplicate/out-of-order timestamps have stable outcomes. Cancel leaves no committed partial stroke; sample filtering is deterministic or its output is recorded. Preview is never authoritative state. |
| SD-04 edits/undo | Whole-stroke create/delete/replace/transform are atomic; immutable prior data is owned safely. Undo restores exact data/IDs/parameters; redo restores the accepted edit; a divergent new edit truncates redo. Define history eviction and unavailable undo explicitly. Cancellation and invalid/stale intents create no history entry. |
| SD-05 one write/replay path | UI, agent, import and replay use one typed intent channel with actor attribution and optional expected revision; stale writes return `state.stale`. Equal ordered intents and initial state yield equal canonical document fingerprint. Define numerical encoding, ordering, seed handling and schema version. Geometry/pixel determinism is a separate renderer claim. |
| SD-06 persistence | Versioned document DTO round trip includes units, basis, brush/version references, ordered samples and required seeds. Stage/validate before replacing state; corrupt/truncated/oversize/unknown-version input is rejected without data loss. Migration fixtures preserve IDs and report unsupported brushes/format loss. No external URL fetching on import. Save failure preserves prior committed save through the admitted Persistence seam. History persistence is explicitly unsupported unless separately specified and tested. |
| SD-07 adapters | Fake input/render/storage ports prove dependency inversion, explicit construction, disposal/rebuild and no hidden scene/singleton/reflection discovery. Missing brushes, input bindings and host targets fail explicitly. Renderer cache failure cannot mutate document history. Pin any by-name API and test missing-member failure. |
| SD-08 clean consumers | A repository-owned standalone painting harness and a separate embedded-annotation harness install the exact same admitted kernel without Open Brush or each other's scenes/types/assets. Use the same document fixtures with different brush policies and host adapters. Include compile/tests for exact Unity/renderer/input/provider/dependency tuples and reproducible CI receipts. |
| SD-09 performance/device | Measure point/stroke counts, geometry counts, allocations, memory and frame timing over declared duration on named hardware. Record tracking discontinuities, erasing/undo responsiveness, reach and comfort in Device Lab with artifact/lock digests. No extrapolation across renderer, headset, input or duration. Automated domain tests never prove headset behavior. |
| SD-10 license/import boundary | Audit each selected code file, brush/shader asset and dependency at immutable source ref. Preserve notices when legally required; proprietary MultiBrush assets/code excluded. Test malicious/invalid import fixtures without redistributing unlicensed artwork. |

Source gate also requires maintenance, test inventory and migration review. The
Open Brush random seed caveat is specifically a replay risk to investigate, not
permission to advertise lossless import. InkML and Blender file interchange are
not promised. Networked collaboration is outside this contract.

## Lesson dispositions for this proposal

These entries answer all current lessons; they do not add a live family to the
lessons register or assert implemented compliance.

| Lesson | Proposed disposition and required follow-through |
| --- | --- |
| LESSON-001 | Adopt in design: versioned channel/brush contract separated from open tags and product brush labels; no universal art taxonomy. |
| LESSON-002 | Adopt in design: schema/API breaks need migration notes and fixtures in both clean consumers (SD-06/08). |
| LESSON-003 | Deferred until implementation: repository-owned CI harness and replayable receipts; no workstation-only promotion (SD-08). |
| LESSON-004 | Adopt in design: explicit bindings preferred; any by-name resolution pinned and negatively tested (SD-07). |
| LESSON-005 | Deferred until implementation: every SD clause needs named test coverage; this table is not executed coverage. |
| LESSON-006 | Deferred until installation: every sibling/transitive package at one full SHA with test framework declared in harness (SD-08). |
| LESSON-007 | Deferred for UI adapters: shared design tokens, one injectable skin and canonical default; artwork color is document content, not a UI token. |
| LESSON-008 | Adopt proposal boundary: no versions/catalog claims; future version increments require matching receipts. |
| LESSON-009 | Deferred for live-apply UI/config seams: declare tunables and capability in data together; no per-family tuning code. |
| LESSON-010 | Adopt in design: painting/annotation tools are peer host clients; hosts never depend on this family. |
| LESSON-011 | Adopt in design: one attributed intent path and stale revision refusal for person, agent, replay and import (SD-05); not distributed authority. |
