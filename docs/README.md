# XR Foundry documentation index

For a first working package consumer, follow the [Persistence quickstart](standards/persistence/quickstart.md):
install two pinned packages, configure a local store, and save/reload one DTO.

This directory holds the standards, architecture, validation evidence,
production-line, contribution, device-lab, governance, RFC, and release records
that back the root catalogs. Machine-readable JSON files remain the authority for
selection and validation; the Markdown pages explain the boundaries around them.
When a Markdown page and its JSON counterpart disagree, the JSON contract is the
one repository validation enforces, and the page is the one to fix.

## Directory map

| Directory | Holds | Start with |
| --- | --- | --- |
| [`architecture/`](architecture/) | Repository layout, the XFCM composition model, the version-adaptive reference model, and the JSON schemas for component manifests, catalogs, compositions, and locks | [`component-composition-model.md`](architecture/component-composition-model.md) |
| [`standards/`](standards/) | One package-family standard per reusable system (including the minimal [foundations](standards/foundations/README.md) contract), the shared UI design language, and the cross-family [consumer lessons register](standards/lessons/README.md): positive-source manifests, architecture contracts, coverage matrices, verification contracts, and per-family lesson dispositions | [`inventory/README.md`](standards/inventory/README.md) |
| [`benchmarks/`](benchmarks/) | The shipped-game gap matrix: the systems three shipped product shapes need, what the library supplies today, and the queue order that follows | [`shipped-game-gap-matrix.md`](benchmarks/shipped-game-gap-matrix.md) |
| [`validation/`](validation/) | Exact Unity consumer evidence per compatibility profile, bounded integration experiments, independent review receipts, the schemas that validate them, and the one-command Unity gate runner guide | [`run-unity-gates.md`](validation/run-unity-gates.md) |
| [`governance/mandates/`](governance/mandates/) | Written operating mandates under which Agents act without asking, with allowed and forbidden actions, scope, expiry, and revocation | [`README.md`](governance/mandates/README.md) |
| [`foundry/`](foundry/) | The Foundry V1 production line: manifest, system admissions, blueprints, batches, next source-gate queue, and release policy | [`README.md`](foundry/README.md) |
| [`device-lab/`](device-lab/) | Device profiles, capability test plans, the receipt template and schema, and the execution-receipt surface | [`README.md`](device-lab/README.md) |
| [`contributing/`](contributing/) | The ten-minute [start-here path](contributing/start-here.md) for routine changes, Task Hall, task registry, deliberation protocol, recognition policy, continuation receipts, the label contract, and the [merge-readiness contract](contributing/merge-readiness.md) that computes the merge verdict from the repository's rules | [`start-here.md`](contributing/start-here.md) |
| [`governance/`](governance/) | The progressive governance maturity model, the Agent membership model, their source manifests, and live [deliberation records](governance/deliberations/) for governance changes | [`README.md`](governance/README.md) |
| [`rfcs/`](rfcs/) | Numbered decision records for Agent Commons, the public workbench, the production line, progressive governance, XFCM, the Agent-native DAO proposal, process-decided merge readiness, and scheduled steward execution inside the repository | [`0005-xr-foundry-component-composition-model.md`](rfcs/0005-xr-foundry-component-composition-model.md) |
| [`releases/`](releases/) | Immutable batch release notes with pinned install selectors, verified claims, and non-claims | [`unity-next-systems-v0.1.0.md`](releases/unity-next-systems-v0.1.0.md) |
| [`for-agents.md`](for-agents.md) | Provider-neutral workflow for coding agents that select, install, extend, or adapt artifacts | |
| [`milestones.md`](milestones.md) | The batches that make this a qualified repository (M1), a community (M2), and an organization (M3), each with a checkable done criterion and current status; the work is cut into tool-neutral [items](contributing/work-items.md) | |

## Reading order by task

**Evaluate one package.** Read the root `package-catalog.json` entry, then the
package `README.md` and `Documentation~/index.md`, then its tuple in the root
`compatibility-profiles.json`, then the matching `validation/evidence/<profile>/`
directory.

**Compose several packages.** Read
[`architecture/component-composition-model.md`](architecture/component-composition-model.md),
then the root `component-catalog.json` and `capability-registry.json`, then the
[Unity reference composition](../compositions/unity/reference-system/README.md),
and run `python scripts/compose_system.py --check --json`.

**Propose a new system.** Read [`foundry/README.md`](foundry/README.md), then
[`foundry/system-admission.md`](foundry/system-admission.md), then
[`foundry/queue/next-batch.json`](foundry/queue/next-batch.json), and model the
new family on an existing `standards/<family>/` source manifest and contract set.
Author the family under `../staging/<family>/` while its Unity evidence does not
yet exist; it moves into `packages/` only after admission and a verified
compatibility profile. The current staged example is
[`../staging/localization/README.md`](../staging/localization/README.md).

**Make a routine change.** Read [`contributing/start-here.md`](contributing/start-here.md):
branch, change, run `python scripts/merge_readiness.py`, push, five-line pull
request. No claim, lease, anchor, or governance window applies. The
[merge-readiness verdict](contributing/merge-readiness.md) answers whether the
change may merge: a routine change on a branch named by a live operating mandate
merges by GitHub auto-merge once the verdict is `ready`, and a non-routine change
waits for a maintainer who reads the same verdict.

**Contribute bounded work.** Read
[`contributing/task-hall.md`](contributing/task-hall.md), select one Ready
checkpoint, and publish a receipt that validates against
[`contributing/work-continuation.schema.json`](contributing/work-continuation.schema.json)
before pausing or handing off.

**Submit device evidence.** Read [`device-lab/README.md`](device-lab/README.md),
select a plan under [`device-lab/test-plans/`](device-lab/test-plans/), start from
[`device-lab/device-receipt.template.json`](device-lab/device-receipt.template.json),
and validate the completed receipt with
`python scripts/validate_repository.py --device-lab-receipt <path> --json`.

## Evidence rules that apply everywhere

- Evidence binds to one exact commit, resolved dependency lock, build target,
  renderer, input source, and device tuple. It does not transfer to a sibling
  tuple, a later commit, or a different renderer composition.
- A manifest, a passing scaffold, a batch release, or a `not_tested` entry is
  never a maturity, runtime, or device claim.
- Every JSON contract under this directory is validated by
  `scripts/validate_repository.py`; run it before and after editing any of them.
