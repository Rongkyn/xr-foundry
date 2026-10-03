# Proposed first experiment and decision gates

This is a verification plan, not an admitted blueprint, implementation task or
executed result. Follow the existing Foundry lifecycle before writing staged code.

The smallest useful experiment is a local retained polyline document exercised by
two consumers: a standalone drawing canvas and annotation attached to a host-owned
object. Start with one simple renderer brush and whole-stroke edits. Fancy brush
assets, arbitrary curve topology, partial erasing, surface reconstruction, live
network replication and import of third-party artwork add independent uncertainties
and should not determine this first kernel.

## Decisions that the evidence must settle before admission

1. Separate long-lived document content from transient pointer previews and
   expiring collaborative marks. A lifetime policy may choose persistence, but a
   network message is not automatically a durable document edit.
2. Choose explicit identity and ownership semantics. Array indices in one source
   are not stable IDs; material slots are not globally portable brush contracts.
3. Name coordinates, axes, units and conversion responsibilities. Store accepted
   document-local samples; host placement and surface constraints belong to ports.
4. Choose whole-stroke create/remove/replace as the proposed edit boundary.
   Transactional validation and refusal without mutation are Foundry obligations
   to demonstrate, not guarantees inferred from Blender or Open Brush.
5. Keep local undo bounded by a declared operation-count policy for the first
   experiment. A hard owned-byte limit is deferred; do not infer one from the
   other. Collaboration
   later needs a separate decision about authority and selective undo.
6. Keep snapshot persistence distinct from operation-history persistence and
   canonical replay. The latter is deferred until encoding, order, numeric and
   seed semantics have their own evidence and tests.

## Concrete proposed choices for the first experiment

These choices are reviewable Foundry synthesis. They are not claims that every
source has the same representation, and they create no public API identity.

| Question exposed by the audits | Proposed first-experiment choice | Tradeoff / falsification |
| --- | --- | --- |
| Stable identity versus changing indices | Assign a document ID and stroke ID independently of array positions; preserve them in snapshots; reject duplicate imported IDs before commit; deliberate clone gets a new ID. | More metadata than an indexed curve array; test reorder, clone and load explicitly. |
| Snapshot ownership | Copy accepted sample/parameter values into document-owned storage; return read-only snapshots that cannot mutate the live document. | Copy cost must be measured later; shared mutable upstream storage is not assumed safe. |
| Coordinates | Require named axes/handedness and units in the document; the first fixture uses metres and a declared right-handed basis. Input/host adapters perform explicit conversion and preserve that declaration. | One fixture is not arbitrary-frame compatibility; unsupported bases/transforms must fail. |
| Edit failure | Prepare and validate a whole replacement stroke before committing state/revision; refused edits create no history entry. | Does not promise recovery from process termination or out-of-memory failure. |
| Local history | Bound the number of accepted whole-stroke edits using consumer configuration; eviction reports unavailable history. | A count cap is not a hard retained-byte cap; strict byte accounting is deferred. |
| Persistence | Versioned retained-state snapshot with explicit brush references and supported channels; stage parse/validate before replacement. | No persistent undo journal, canonical fingerprint or third-party interchange in this experiment. |
| Target lifetime | Annotation consumer holds the target reference and revision separately; target disappearance yields unresolved binding and keeps retained marks recoverable. | Reattachment must be explicit; no automatic scene search or shared-anchor inference. |

Before admission, review these choices against the source matrix and existing
lessons, and resolve any objection by narrowing the candidate. If accepted, the
public implementation task should bind its scope to these cases and the exact
consumer tuple. It should not quietly restore deferred features during coding.

## Named future verification cases

| Planned case | Required observation | Evidence level |
| --- | --- | --- |
| `RejectInvalidStrokeWithoutMutation` | Nonfinite samples, invalid parameters, duplicates and exceeded budgets leave state and revision unchanged. | Domain test, unimplemented |
| `CancelPreviewLeavesDocumentUnchanged` | Tracking loss/cancel disposes preview without committing a stroke. | Domain/fake input, unimplemented |
| `UndoRedoWholeStrokeRoundTrip` | Create/remove/replace undo restores owned samples and IDs; divergent edit truncates redo; eviction is explicit. | Domain test, unimplemented |
| `HostLocalFrameRoundTrip` | The same document survives host translation/rotation/uniform scale through explicit conversions; invalid transforms fail. | Domain plus adapter test, unimplemented |
| `MissingTargetDoesNotRebind` | Deleted or changed host target yields unresolved annotation instead of attaching to another object. | Annotation consumer, unimplemented |
| `SnapshotLoadIsStaged` | Invalid/version-unknown/oversized input cannot replace a valid document; supported round trip retains declared channels and brush references. | Domain and persistence adapter, unimplemented |
| `RendererRebuildPreservesDocument` | Cache disposal, missing brush and rebuild cannot rewrite retained content or history. | Fake renderer then Unity adapter, unimplemented |
| `BothConsumersUseSameKernel` | Two separate harnesses install the same immutable kernel revision without each other's scenes or source-app assets. | Exact-consumer receipt, unexecuted |

Human, agent and import writes must follow the existing LESSON-011 attributed
intent seam and expected-revision refusal. Its local stale-write protection is
not a synchronization protocol. UI theme and live-tuning seams follow lessons
007/009 when an actual UI adapter exists; no UI dependency is introduced now.

After admission and a public implementation task, the domain/fake-port cases can
be authored first. Unity compile/EditMode and both consumer receipts must run on
the exact supported tuple before compatibility claims. Controller input, spatial
comfort and performance require separately recorded named-device tests. A failed
or unavailable Editor run is a remaining gate, never a reason to relabel a source
review as runtime validation.
