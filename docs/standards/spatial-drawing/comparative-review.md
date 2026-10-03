# Comparative source review and remaining gate

Status: proposal, reference only. Reviewed 2026-10-03 against PR114's baseline
`b83db66b6cd6cf47d1902f73494f83fc04227a82`. Capability: `ai_tokens_only`.

## What the comparison changes

Retained artwork, target-bound annotation and transient shared ink overlap in
ordered spatial marks, but have different ownership, lifetime, history and save
semantics. The first candidate should test a small retained document, with local
edits and snapshots; it should not make a full drawing application or network
protocol its kernel. This is a design recommendation from the evidence, not an
admission decision.

The original proposal relied on Blender search excerpts and repeated Open Brush
comments without following the serializer. The full source review now replaces
those shortcuts. The corrected records must distinguish source facts, historical
behavior, repository activity, actual test assertions and Foundry obligations.

## Read the evidence by question

- Retained stroke data, edits and historical migration: [Blender audit](blender-source-audit.md)
- Seeds, IDs, save/load, tests and build tuple: [Open Brush audit](openbrush-source-audit.md)
- Annotation state and transient network ownership: [independent implementations](independent-implementations.md)
- Normative vocabulary and interaction/undo choices: [standards and research](standards-and-research.md)
- Per-capability retain/narrow/defer decision: [source matrix](source-to-capability.md)
- Proposed first experiment and named cases: [prototype plan](prototype-plan.md)

| Implementation family | Retained object | History model | Consequence for Foundry |
| --- | --- | --- | --- |
| Open Brush / Tilt Brush | Brush-driven artwork strokes and application save format | Application commands; redo invalidation | Learn sample/brush/save separation; do not inherit scene singletons or presume durable stroke IDs. |
| Blender Grease Pencil | Curves/attributes in drawings, layers and frames | Editor snapshots and general history limits | Learn typed attributes and cache separation; do not expose unstable indices or assume hard memory accounting. |
| Slicer Markups | Identified points, target references and explicit position states | Opt-in bounded scene snapshots | Keep annotation binding/state explicit, with domain measurements outside Core. |
| Hubs / NAF | Owner-streamed line buffers and mesh state | Last-line undo, current-state late join, expiry | Separate transient collaboration from retained artwork and durable history. |

The narrow first prototype prefers whole-stroke editing and a single local
writer over partial cutting and shared concurrent editing. This reduces the
number of unsupported semantics tested at once. It deliberately preserves an
extension boundary rather than promising a universal paint, CAD, medical-markup
or multiplayer model.

## Prescribed workflow and present evidence

The authoritative sequence is [Foundry README](../../foundry/README.md),
[system admission](../../foundry/system-admission.md), positive-source review,
all [lessons](../lessons/README.md), admitted blueprint and public implementation
task, staged implementation, repository and exact-consumer validation, independent
review, then any supported promotion/release. Named-device evidence is separate.

| Existing requirement | Evidence or remaining action |
| --- | --- |
| Two materially different consumer contexts | Standalone retained painting and a host-model annotation client are specified. These are planned harnesses, not validated consumers. |
| Official/standard source plus independent implementation | Dated W3C recommendations and pinned implementation audits are recorded. Forks and multiple files do not inflate the independent source count. |
| Every mandatory Core capability has multiple independent positive sources | Source-to-capability matrix separates recurring functions from stronger transactional/replay guarantees. Final Core requirements and their exact semantics remain a gate decision. |
| Variation and product exclusion | Brush appearance, input projection, target attachment, transient lifetime, networking and medical measurement remain adapters or consumer policy. |
| Provenance before implementation | Selected files, licenses and excluded assets are documented. No imported code/assets are selected; any future selection requires its own exact dependency and notice audit. |
| Clean-consumer proof plan | Named future tests and two separate consumers are planned. No install, compile or runtime receipt exists for this family. |
| All current lessons answered | Verification contract records LESSON-001 through LESSON-011. The new comparison preserves the one-intent path, explicit bindings, migration and evidence boundaries. |

Do not turn an unexecuted clean-consumer plan into a reason to claim that admission
requires already-built consumers: the current admission gate asks for the plan;
actual consumer execution belongs later. Likewise, do not demand an exhaustive
license audit of unselected third-party artwork to cite an architectural fact.
The actual remaining blocker is a reviewed, precise mandatory kernel whose source
basis meets the existing gate, followed by the authoritative record and public
implementation task. No new approval framework is introduced here.

## Validation record

Independent advisory review checked pinned Blender undo, Open Brush serialization,
Slicer history/codec, Hubs ownership/lifetime and integration boundaries. It found
no blocking unsupported claim after correcting an InkML section citation and
per-record license descriptions. Final repository validation is recorded below.
Repository checks verify integration and structure, not the truth of external
source claims. Required human GitHub review and upstream write rights remain
separate from an advisory agent review.


Validation on 2026-10-03 for research tree committed as `4ef81a9`:

| Command | Observed result |
| --- | --- |
| `python scripts/validate_repository.py --json` | PASS after replacing a prose phrase that collided with the existing text-safety marker; no validator or allowlist changed. |
| `python -m unittest discover -s tests -p "test_*.py"` | PASS, 368 tests in 65.823 seconds on the corrected tree. The earlier run correctly failed the same text marker. |
| `python scripts/merge_readiness.py --base origin/main --head HEAD --markdown` | All seven technical checks PASS; overall BLOCKED/exit 1 because independent review cannot be evaluated without PR metadata. No human approval is claimed. |

The closeout updates this validation record and WI-034 status/proof only; final
committed-head checks and remote CI bind the published revision in the pull
request. Upstream source tests, Unity compilation, consumer execution and device
checks were not run. WI-033 and WI-034 completion means the bounded research
artifacts exist and their repository checks ran, not that milestone 2b or system
admission is complete.
