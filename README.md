# XR Foundry

Reusable XR development packages and reference material for people and coding
agents. The repository starts with Unity packages, while its catalog and quality
contracts are designed to support tools, templates, samples, validation, and future
engine-specific collections without pretending those implementations exist today.

XR Foundry is both:

- an installable source of versioned packages; and
- a reference source that agents can inspect, compare, adapt, and validate instead
  of reconstructing common systems from scratch.

The second use does not make generated changes automatically correct. Package
maturity, compatibility, license, tests, independent-consumer evidence, and device
evidence remain explicit gates.

## Start here

| Need | Entry point |
| --- | --- |
| Save and reload a small Unity DTO with two packages | [Persistence quickstart](docs/standards/persistence/quickstart.md) |
| Choose an available system or package | [`package-catalog.json`](package-catalog.json) |
| Compose packages as one system | [`XFCM v0.2`](docs/architecture/component-composition-model.md), [`component-catalog.json`](component-catalog.json), and the [Unity reference composition](compositions/unity/reference-system/) |
| Find reusable reference material | [`reference-catalog.json`](reference-catalog.json) |
| Work with a coding agent | [`AGENTS.md`](AGENTS.md) and [`docs/for-agents.md`](docs/for-agents.md) |
| Install a Unity package | [Install for evaluation](#install-for-evaluation) |
| Make a routine change (documentation, tests, tooling, non-breaking package change) | [`docs/contributing/start-here.md`](docs/contributing/start-here.md) and the [merge-readiness verdict](docs/contributing/merge-readiness.md) |
| Propose a reusable system | [`CONTRIBUTING.md`](CONTRIBUTING.md); a new family is authored under [`staging/`](staging/localization/README.md) before its Unity evidence exists |
| Find or claim bounded public work | [`Public Task Hall V1`](docs/contributing/task-hall.md) and the [live Project](https://github.com/users/Lingkyn/projects/2) |
| Build the next reusable package family | [`Foundry V1 production line`](docs/foundry/README.md), [first batch](docs/foundry/batches/unity-first-batch.v1.json), and [next source-gate queue](docs/foundry/queue/next-batch.json) |
| Discuss a public RFC | [Discussion #22](https://github.com/Lingkyn/xr-foundry/discussions/22) and the Ideas RFC form |
| Contribute hardware evidence | [`Public Device Lab V1`](docs/device-lab/README.md) |
| See how contributions are recognized | [`Recognition policy`](docs/contributing/recognition-policy.md) and [`CONTRIBUTORS.md`](CONTRIBUTORS.md) |
| Understand governance and its maturity path | [`GOVERNANCE.md`](GOVERNANCE.md), [`governance model`](docs/governance/README.md), [`RFC 0004`](docs/rfcs/0004-progressive-governance.md), and proposed [`RFC 0006`](docs/rfcs/0006-agent-native-xr-dao.md) |
| Understand repository workflow | [`PROJECT_GITHUB_PLAYBOOK.md`](PROJECT_GITHUB_PLAYBOOK.md) |
| Check evidence and maturity | [`docs/validation`](docs/validation/) and [`ROADMAP.md`](ROADMAP.md) |
| Test the packages with your own Unity Editor in one command | [`docs/validation/run-unity-gates.md`](docs/validation/run-unity-gates.md) |
| Install a released batch by tag | [`docs/releases`](docs/releases/) and the [batch registry](docs/foundry/batches/batch-registry.v1.json) |
| Navigate the documentation tree | [`docs/README.md`](docs/README.md) |

Thin adapters are included for tools that discover repository instructions in
different ways: `CLAUDE.md`, `.cursor/rules/`, and `SKILL.md`. They all point back
to the same public catalog and quality contract rather than maintaining different
answers for different models.

## Unity package catalog

| Package | Maturity | Purpose |
| --- | --- | --- |
| [`com.lingkyn.project-initializer`](packages/unity/foundations/com.lingkyn.project-initializer/) | Incubating | Configurable folder/scene scaffold, baseline prefabs, validation, and editor tools |
| [`com.lingkyn.xr-baseline`](packages/unity/foundations/com.lingkyn.xr-baseline/) | Incubating | Vendor-neutral XR Sandbox assets, rig helpers, configuration, and smoke-build tools |
| [`Inventory Package Family`](docs/standards/inventory/README.md) | Incubating | One reusable Inventory system with optional Core, Unity authoring, renderer-neutral Presentation, UGUI, UI Toolkit, and renderer-specific XR modules |
| [`Persistence Package Family`](docs/standards/persistence/README.md) | Incubating | Engine-light save/recovery contracts plus an optional Unity local-file, ScriptableObject, and JsonUtility adapter |
| [`Settings Package Family`](docs/standards/settings/README.md) | Incubating | Engine-light typed settings, profiles, transactional apply/rollback, accessibility discoverability metadata, and optional Unity authoring |
| [`Interaction Package Family`](docs/standards/interaction/README.md) | Incubating | Engine-light semantic intents, contexts, routes, explicit state, deterministic policy evaluation, and optional Unity Input System authoring |

The human-facing landing page groups a reusable system into one row to reduce
cognitive load. Its family page explains recommended compositions and lets a
person or Agent progressively disclose the installable modules. The machine-readable
[`package-catalog.json`](package-catalog.json) continues to record every package
separately because dependency, version, maturity, and evidence gates remain
module-specific.

## One composable system

Every current Unity package also has a colocated `foundry.component.json`. The
[`component catalog`](component-catalog.json) and
[`capability registry`](capability-registry.json) turn those independent modules
into one versioned product-line graph. A consumer composition selects fixed
components plus exactly one renderer and XR-surface variant, then resolves the graph
into a deterministic lock.

The [Unity reference composition](compositions/unity/reference-system/) selects
the UGUI route and structurally resolves 13 components. Its seven bindings use
six consumer-owned typed adapter sources; one adapter serves both renderer and
XR-surface bindings. The v0.2 lock binds source paths, assemblies and SHA-256
values. UI Toolkit remains a peer option, not a cumulative dependency.

The current [consumer template](compositions/unity/reference-system/consumer/)
materializes 11 packages for those paths. Generate its test inventory from source
before running it; historical experiment counts are not the current inventory.
Recorded experiments prove only their named inputs, assemblies and tuples,
including bounded temporary-filesystem backup recovery. The full composition
still has `runtime_ready: false`; structural resolution and a materialized project
do not prove all 13 components, current-revision Unity execution or a device.

XFCM keeps runtime communication strongly typed and in process. JSON manifests are
the composition/control plane. MCP may later expose that control plane to editors
or coding Agents, but it is not a global runtime event bus.

## Incubating system standards

The first reusable game-system candidate is the
[`Inventory Package Family Standard`](docs/standards/inventory/README.md). Its
design inputs are restricted to admitted positive external sources. It deliberately
excludes consumer and screened-out code from derivation. Core and Unity authoring
retain their public version/API history, while current-revision execution evidence
is pending. The canonical renderer-neutral architecture contains
Core `0.1.1`, Unity authoring `0.1.1`, Presentation `0.1.0`, UGUI `0.2.0`, UI
Toolkit `0.1.0`, XR UGUI `0.1.0`, and XR UI Toolkit `0.1.0` as incubating packages.
Each current package graph needs its own
consumer evidence, and each XR renderer/device tuple needs its own real-device
receipt. No old package path or renderer-ambiguous XR compatibility layer is part
of the active repository surface.

The [batch registry](docs/foundry/batches/batch-registry.v1.json) records both the
[`Unity first batch`](docs/foundry/batches/unity-first-batch.v1.json) and
[`Unity next systems`](docs/foundry/batches/unity-next-systems.v1.json), which
contains Persistence, Settings and Interaction. A batch release is an immutable discovery/install surface; it does not promote package
maturity or inherit device claims. The
[`Foundry V1 production line`](docs/foundry/README.md) governs how later package
families move from positive-source proposal to independently reviewed release.
A new family is authored under `staging/` before its Unity evidence exists and
moves into `packages/` only after admission and a verified compatibility profile;
the current staged example is
[`staging/localization`](staging/localization/README.md), which is in no catalog,
batch, profile, or release. The exact named-device handoff uses the generic
[`Public Device Lab V1`](docs/device-lab/README.md), its
[`Inventory world-space UI plan`](docs/device-lab/test-plans/inventory-world-space-ui-v1.json),
and the machine-validatable
[`execution receipt`](docs/device-lab/device-receipt.template.json). This admits a
PICO tracked-controller profile without adding a vendor dependency to the package,
while keeping the same route available for other reviewed device profiles.

A cross-cutting standard,
[`XR Foundry UI Design Language`](docs/standards/design-language/README.md), gives
every UI-bearing system one shared visual and interaction vocabulary so the library
reads as a single product rather than one look per package. Vision Pro is the primary
visual reference; PICO and Meta Horizon OS are the primary interaction references. Any
package with UI defaults to it: keep visual vocabulary in the renderer adapter, expose
one injectable skin/theme seam that maps the shared tokens, and ship a default skin
with the canonical values. The current Inventory adapters include the UGUI
[`InventorySkin`](packages/unity/systems/inventory/com.lingkyn.inventory.ugui/Runtime/InventorySkin.cs)
and [UI Toolkit skin seam](packages/unity/systems/inventory/com.lingkyn.inventory.uitoolkit/README.md#injecting-a-skin).
These are implemented extension points; their presence does not supply current
visual, device or accessibility-outcome evidence.

`incubating` means a package is available for evaluation but does not yet promise
API compatibility. Candidate promotion requires repository validation, tests, and
a clean independent Unity consumer compile. XR behavior additionally needs real
device evidence before a stable claim.

## Install for evaluation

For a first install, use the [two-package Persistence walkthrough](docs/standards/persistence/quickstart.md):
it supplies a concrete immutable pin, working configuration and consumer-owned
save/load code. The complete selector reference below lists available modules;
choose only the packages your consumer needs and their dependencies. It is not a
minimal project manifest.

Pin a reviewed commit SHA rather than `main`:

```json
{
  "dependencies": {
    "com.lingkyn.project-initializer": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/foundations/com.lingkyn.project-initializer#<full-40-character-commit-sha>",
    "com.lingkyn.xr-baseline": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/foundations/com.lingkyn.xr-baseline#<same-full-40-character-commit-sha>",
    "com.lingkyn.inventory.core": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/inventory/com.lingkyn.inventory.core#<same-full-40-character-commit-sha>",
    "com.lingkyn.inventory.unity": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/inventory/com.lingkyn.inventory.unity#<same-full-40-character-commit-sha>",
    "com.lingkyn.inventory.presentation": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/inventory/com.lingkyn.inventory.presentation#<same-full-40-character-commit-sha>",
    "com.lingkyn.inventory.ugui": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/inventory/com.lingkyn.inventory.ugui#<same-full-40-character-commit-sha>",
    "com.lingkyn.inventory.uitoolkit": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/inventory/com.lingkyn.inventory.uitoolkit#<same-full-40-character-commit-sha>",
    "com.lingkyn.inventory.xr.ugui": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/inventory/com.lingkyn.inventory.xr.ugui#<same-full-40-character-commit-sha>",
    "com.lingkyn.inventory.xr.uitoolkit": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/inventory/com.lingkyn.inventory.xr.uitoolkit#<same-full-40-character-commit-sha>",
    "com.lingkyn.persistence.core": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/persistence/com.lingkyn.persistence.core#<same-full-40-character-commit-sha>",
    "com.lingkyn.persistence.unity": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/persistence/com.lingkyn.persistence.unity#<same-full-40-character-commit-sha>",
    "com.lingkyn.settings.core": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/settings/com.lingkyn.settings.core#<same-full-40-character-commit-sha>",
    "com.lingkyn.settings.unity": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/settings/com.lingkyn.settings.unity#<same-full-40-character-commit-sha>",
    "com.lingkyn.interaction.core": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/interaction/com.lingkyn.interaction.core#<same-full-40-character-commit-sha>",
    "com.lingkyn.interaction.unity": "https://github.com/Lingkyn/xr-foundry.git?path=/packages/unity/systems/interaction/com.lingkyn.interaction.unity#<same-full-40-character-commit-sha>"
  }
}
```

During package development, use `file:` dependencies from a separate Unity smoke
project. Do not create a release tag until the compatibility evidence for that
revision is recorded.

Use the full 40-character commit SHA for Git package pins. The Inventory clean
consumer gate confirmed that Unity Package Manager rejects a short SHA in this URL.
Pin every `com.lingkyn.inventory.*` package used by a Git consumer to the same
reviewed revision: custom transitive semver dependencies are not a public registry.

## Use as reference material

A coding agent should not copy the whole repository or infer a production claim
from a folder name. It should:

1. read `reference-catalog.json` and the selected package manifest;
2. inspect its README, documentation, tests, samples, changelog, and evidence;
3. decide whether to install the package, extend a public seam, or use it only as
   raw material for a consumer-owned adapter;
4. keep product-specific code in the consuming project; and
5. run the repository checks plus the consumer's own compile/tests.

See [`docs/for-agents.md`](docs/for-agents.md) for the provider-neutral workflow.

## Version-adaptive references and current implementation profile

The repository's standards, tests, and samples are version-adaptive raw material;
they are not limited to the Editor version used for the current implementation.
An Agent may generate a target-specific candidate for another Unity, UI Toolkit,
XRI, or future engine version. Each installable package revision still declares a
concrete manifest and may claim only its own verified profile. See the
[`Version-Adaptive Reference Model`](docs/architecture/version-adaptive-reference-model.md)
and [`compatibility-profiles.json`](compatibility-profiles.json).

The first immutable automated validation target is one concrete profile: Unity
`6000.3.19f1`, URP `17.3.0`, Input System `1.19.0`, UGUI `2.0.0`, XRI `3.5.1`,
XR Plug-in Management `4.5.3`, and OpenXR `1.16.0`. Machine-readable receipts now
verify the named automated profiles at their exact evidence commit. Later package
or release commits do not inherit those results; `compatibility-profiles.json` is
authoritative for the exact state, tuple, revision, and evidence.

That tuple is a reproducibility boundary, not a minimum-version declaration or a
claim that other versions cannot be generated. Unlisted tuples begin as adaptation
candidates and become installable compatibility claims only after their own
validation. Unity is the only implemented engine collection in this foundation.
Unreal Engine and Godot are roadmap directions, not current support claims.

## Quality contract

Every live package must provide:

- a stable identity and matching assembly/namespace boundary;
- README, changelog, license, documentation, tests, and samples;
- no compile-time dependency on a consuming product or its assemblies;
- deterministic repository validation and CI;
- explicit maturity, compatibility, migration, deprecation, and security guidance;
- an independent consumer compile before candidate promotion; and
- device evidence before XR/controller/headset behavior is called stable.

Run the local checks from a project-local virtual environment so the exactly
pinned contract dependencies never collide with a distribution-managed Python:

```bash
python -m venv .venv
. .venv/bin/activate            # PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r scripts/contract-requirements.txt
python scripts/compose_system.py --check --json
python scripts/validate_repository.py --json --fast-structure
python scripts/validate_repository.py --json --run-contract-tests
```

`.venv/` is ignored by Git. The repository contract supports Python `3.11`, `3.12`, and `3.13`. Pull requests,
pushes to `main`, and manual workflow runs execute the full contract across that
matrix. GitHub Actions and the exactly pinned Python contract dependencies are both
checked monthly by Dependabot; changes remain reviewable pull requests and do not
gain merge authority from automation. Whether any pull request may merge is
answered by the [merge-readiness verdict](docs/contributing/merge-readiness.md):
a routine change on a branch named by a live operating mandate merges by GitHub
auto-merge once the verdict is `ready` and the required checks pass, and a
non-routine change waits for a maintainer who reads the same verdict.

The fast structure command is iteration feedback and cannot support promotion or
release. The full command runs repository validation first and skips the test
suite if that first stage fails.

Unity package tests run from a Unity consumer through the Test Framework. The
`unity-consumer-tests` workflow runs them in CI from the repository-owned reference
consumer, one assembly per Unity process, and accepts each result only through
`scripts/verify_unity_test_results.py` against a case count audited from source by
`scripts/audit_unity_test_inventory.py`. It needs a Unity license stored as a
repository secret (`UNITY_LICENSE`, or `UNITY_EMAIL` and `UNITY_PASSWORD`) and skips
itself on fork pull requests, where secrets are unavailable.

## Contributing and license

Start with [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SUPPORT.md`](SUPPORT.md), and
[`SECURITY.md`](SECURITY.md). Package proposals begin as `incubating`; mature game
systems require a positive-source and coverage bake-off before code is admitted.

The [Task Hall](docs/contributing/task-hall.md) publishes bounded research, build,
review, and integration work. The [Device Lab](docs/device-lab/README.md) lets
contributors submit revision-bound headset evidence without code or repository
write access. Claiming work coordinates a lease only; it never grants GitHub
permissions or merge authority. A routine change needs no claim, lease, anchor, or
governance window: it follows
[`docs/contributing/start-here.md`](docs/contributing/start-here.md).

The repository is MIT licensed. See [`LICENSE`](LICENSE). Third-party dependencies
keep their own licenses.

## DAO-ready Open Commons

XR Foundry is being prepared as public infrastructure that can support progressively
broader stewardship without pretending a DAO already exists. The current observed
stage is maintainer-led `G0`; the progressive model and RFC 0004 are proposed and
inactive until public deliberation and an explicit maintainer decision adopt them.
Participation, recognition, payment, tokens, and repository permission remain
separate. This phase creates no wallet, treasury, multisig, token governance,
smart contract, on-chain action, organization transfer, or remote settings change.

See [`GOVERNANCE.md`](GOVERNANCE.md) for the human-readable boundary and
[`governance-model.v1.json`](docs/governance/governance-model.v1.json) for the
machine-enforced contract.

RFC 0006 adds a proposed Agent maturity axis without activating Agent membership.
The observed state remains `G0 x A0`; `G0 x A1` is a review target with accountable
principals, declared lineage, evidence-bound capabilities, revocable mandates, and
human maintainer authority.

## Public workbench for people and Agents

XR Foundry treats GitHub as durable shared state, not merely a place to upload the
final code. Umbrella Issues keep a system understandable as one outcome; child
Issues and named checkpoints expose independently valuable work. Each checkpoint
states its dependencies, allowed paths, non-goals, acceptance, verification,
evidence, device/review gates, and exact next safe action.

This lets a contributor finish one unit without pretending the whole system is
done. If a person, Cursor, Codex, Claude Code, or another tool stops midstream, a
continuation receipt preserves completed checkpoints, the current revision,
evidence, remaining work, blockers, and handoff boundary for the next contributor.
If a process stops too abruptly to publish that receipt, work resumes from the last
public checkpoint boundary; local-only output is never assumed complete.

Contribution is not limited to code. Research, documentation, design, review,
tests, device/user testing, and infrastructure can all be acknowledged through
accepted evidence. They remain separate categories rather than a total points
ranking, and no activity score grants repository permission. For bounded
coordinated work, start with the [Task Hall](docs/contributing/task-hall.md),
choose one certified checkpoint, and use a fork pull request unless you already
hold an appropriate repository role; for a routine change, start with
[`docs/contributing/start-here.md`](docs/contributing/start-here.md) instead.

Where the project stands and what comes next is written down, not remembered:
[`docs/milestones.md`](docs/milestones.md) sets the batches that make this a
qualified repository, then a community, then an organization, with the status
of every cell; [`docs/contributing/work-items.json`](docs/contributing/work-items.json)
cuts that plan into self-contained items any person or coding Agent can take
without session context; and `python scripts/open_work.py --markdown` generates
the open-work board from the tree. The merge verdict from
`python scripts/merge_readiness.py` decides whether a routine change merges;
[`docs/validation/checked-claims.md`](docs/validation/checked-claims.md) says
which claims a machine checks and which are still self-declared.
