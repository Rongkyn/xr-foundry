# Roadmap

XR Foundry grows by proven artifact classes rather than by creating empty engine
folders. Unity is the implemented foundation. Agent guidance and machine-readable
reference selection are part of the product, while model-specific adapters remain
thin.

## Foundry production line

Foundry V1 publishes a dry-run-first package blueprint/scaffolder and an immutable
batch registry. Two incubating batches are released: `unity-first-batch` registers
the nine foundation and Inventory packages, and `unity-next-systems` registers the
six Persistence, Settings, and Interaction packages, so the 15 live Unity packages
are each covered exactly once. A batch is a discovery and install surface, not a
maturity promotion. New systems enter through the public source-gate queue, where
Localization is the current proposal; no package directory or package ID is
created before admission. See [`docs/foundry`](docs/foundry/README.md) and
[`docs/releases`](docs/releases/).

Persistence, Settings/Accessibility, and Semantic Interaction have completed
their first independently validated Core and Unity checkpoints. Their next gates
are public API compatibility review, one release upgrade/rollback exercise, and
any separately scoped live runtime or named-device evidence required by a claim.

## Execution order after Inventory

The library grows one evidence gate at a time, in this order, and an Agent under
an operating mandate works the first unblocked item without waiting to be asked:

1. **Editor evidence for the authored tests.** Every Core and adapter test named in
   the family coverage maps (`docs/standards/*/coverage-map*.json`) runs through
   `scripts/run_unity_gates.py` or the `unity-consumer-tests` workflow, and the
   compatibility profiles move to the current commit. Needs a Unity Editor or a
   Unity license secret; nothing else in this list is credible before it.
2. **Process-decided merges.** The `merge-readiness` verdict runs on every pull
   request; a routine change on a mandated branch merges by GitHub auto-merge once
   the verdict is ready (rule in effect, revertible, objection surface DLB-0002).
   Needs the two owner-only repository settings named in
   `docs/contributing/merge-readiness.md`.
3. **Second checkpoints for Persistence, Settings, and Interaction.** Public API
   compatibility review, one release upgrade/rollback exercise per family, and the
   open dispositions in the lessons register.
4. **Inventory renderer and device gates.** Land the UGUI skin seam (#81) without
   an unverified version bump, then the Device Lab plan
   `inventory-world-space-ui-v1` on one named headset.
5. **Localization** through the source-gate queue (`NEXT-LOCALIZATION`): the Core
   implementation, tests, source manifest, verification contract, and admission and
   blueprint drafts are staged in `staging/localization/`; one Unity run plus the
   maintainer's admission signature move it into the package tree. No package
   directory exists before admission.
6. **Whole-composition evidence.** A green reference-system run, a player build, and
   named-device evidence lift `runtime_ready` for the XFCM composition.

7. **Audio events** (`NEXT-AUDIO-EVENTS` in the queue): engine-light audio event
   identity, mix and snapshot state, and spatial attachment intents with a thin
   Unity AudioMixer adapter. Both layers are staged under
   [`staging/audio/`](staging/audio/README.md) with 53 authored, unexecuted tests
   mapped in `docs/standards/audio/coverage-map.json`. It enters the admission
   gate after Localization leaves staging.

Families beyond these enter only through the queue with their own admission
record. The section below ranks the candidates so the queue takes the most-used
systems first; it grants no admission, package id, or directory.

The milestones that turn this order into a qualified repository, then a
community, then an organization are in [`docs/milestones.md`](docs/milestones.md).

## Family priority by consumer frequency

The library builds the systems that almost every XR project needs before the
ones only some projects need. Ranking basis: how often a Unity XR project has to
build the system itself, whether an engine-light Core can be authored and tested
without an Editor, and whether admitted positive public sources exist. A family
moves up only through the source-gate queue (`docs/foundry/queue/next-batch.json`)
with its own admission record.

| Rank | Family | Frequency | State | Why this position |
| --- | --- | --- | --- | --- |
| 1 | Foundations: XR baseline and project initializer | Every project | Live, incubating | Rig, config, diagnostics, and project layout come first; everything else composes on them |
| 2 | Semantic interaction | Every XR project | Live, incubating | Grab, hover, activate, and hand or controller routing are the first thing a user touches |
| 3 | Settings and accessibility | Every XR project | Live, incubating | Comfort options (vignette, turn mode, seated or standing) are a store requirement on every headset |
| 4 | Persistence | Nearly every project | Live, incubating | Save, load, versioned migration, and fail-closed corruption handling |
| 5 | Inventory | Most games, many tools | Live, incubating | The most elaborate family; also the proof of the renderer-adapter and XR-composition pattern |
| 6 | Localization | Every shipped project | Staged (`staging/localization`) | Store listings and comfort text need it before release; engine-light Core is complete on paper |
| 7 | Audio events | Every project | Staged (`staging/audio`) | Mix, snapshot, parameter, and attachment intents; the adapter is thin over the mixer |
| 8 | Locomotion and comfort | Every VR project | Staged (`staging/locomotion`) | Teleport, snap and smooth turn, continuous move, comfort vignette policy; today only Editor setup tools exist in xr-baseline. Sources: XR Interaction Toolkit locomotion, platform comfort guidelines |
| 9 | Scene flow | Nearly every project | Staged (`staging/scene-flow`) | Loading, transitions, fade and hold, additive scene sets, error recovery; every project writes one and most write it badly |
| 10 | XR UI shell | Most XR projects | Staged (`staging/xr-ui-shell`) | World-space panels, wrist and hand menus, pointer and gaze routing, built on the shared design language; the Inventory presentation adapters become one client of it |
| 11 | Live tuning | Most XR projects during development | Staged (`staging/live-tuning`) | In-headset tuning of design-language tokens and skin values (colour, size, corner radius, spacing) with export back to the assets that own them; a developer scaffold that composes on the XR UI shell, the skin seams, Settings, and the design language, so "does it look right on the device" is answered in the headset instead of by a rebuild |
| 12 | Haptics | Every XR project | Staged (`staging/haptics`) | Named haptic events and per-controller profiles behind an engine-light intent seam; every shape in the shipped-game gap matrix needs it in the first minute of play |
| 13 | Platform services | Every shipped project | Candidate, source gate passed | Entitlement, achievements, leaderboards, cloud save, and store sign-in as thin adapters over the vendor SDKs behind one contract; no shipped product avoids it and nothing in the library covered it before the gap matrix |
| 14 | Quality tiers | Every shipped project | Candidate, source gate passed | Refresh rate, render scale, foveation, and per-device presets; store certification requires a stable frame rate on every headset |
| 15 | Content packs | Most projects | Candidate | Data-driven loading of levels, packs, and user content behind one contract (Addressables or equivalent); custom levels and user scenes are how XR products grow after release |
| 16 | Spatial placement | Creation tools, many games | Candidate | Ray placement with ghost preview, sticky aim hand, stick-as-distance, snapping, commit and cancel, and locomotion suppression while aiming; from the creation-tool shape of the gap matrix |
| 17 | Tutorial and onboarding | Most XR projects | Candidate | First-run guidance, gated steps, replay; XR projects need it because controls are not discoverable |
| 18 | Objectives and quests | Most games | Candidate | Goal graphs, progress state, persistence integration |
| 19 | Analytics events | Many projects | Candidate | Consent-gated, typed event intents with no vendor dependency in Core |
| 20 | Dialogue and narrative | Some games | Candidate | Branching lines, localization integration; lower frequency across XR tools |
| 21 | Networking and multiplayer | Some projects | Deferred | High frequency where present, but no engine-light Core is credible without a transport; enters after a source comparison of the maintained public stacks |

Ranks 8 to 11 have passed the source gate and are staged. Ranks 12 to 16 are
ordered by the [shipped-game gap matrix](docs/benchmarks/shipped-game-gap-matrix.md):
systems every shipped product needs and the library lacks come before systems the
library already has on paper. A candidate enters the queue only with a source manifest, a
verification contract, and an admission draft, exactly as Localization and Audio
did.

## Composition

XFCM v0.2 gives every live package a colocated component manifest and resolves the
Unity reference composition to a deterministic 13-component lock with seven
bindings backed by six adapter sources. The current materializer embeds 11
packages. Historical consumer experiments cover only their named assemblies and
recorded revisions; regenerate the current test inventory before running the
[consumer](compositions/unity/reference-system/consumer/README.md). The composition keeps
`runtime_ready: false` until whole-composition Unity evidence, a player build,
and named-device evidence exist; each of those is a separate gate. See
[`docs/architecture/component-composition-model.md`](docs/architecture/component-composition-model.md).

## Continuous Unity evidence

The `unity-consumer-tests` workflow materializes the repository-owned reference
consumer, derives the exact test-case count of every test assembly from source, runs
each assembly in its own Unity process, and accepts a result only when the
repository's verifier proves that exact assembly passed completely. It activates
when a Unity license secret is configured and skips itself on fork pull requests.
Until its first green run on `main`, every `*_tests` and `local_clean_consumer`
gate remains workstation evidence anchored at a recorded commit. A green run is
Editor evidence for one tuple, never a player, controller, or headset claim.

## Candidate gate

- Repository validator and Python contract tests pass.
- Every promoted package resolves and compiles in a fresh consumer matching its
  declared compatibility profile.
- EditMode package tests pass.
- Installation and migration evidence names an immutable commit.

## Stable gate

- Public API/compatibility policy and migration path are proven across a release.
- Documentation and samples match the shipped API.
- XR claims have current real-device evidence where required.

## Inventory package family

Inventory is an incubating system standard with a positive-external-source-only
manifest, package-family architecture, nested presentation composition, and a
verification contract. Core, Unity authoring, Presentation, UGUI, UI Toolkit, XR
UGUI, and XR UI Toolkit form the implemented renderer-neutral graph. Exact
automated profiles exist at their recorded evidence commits. The first-batch
release commit still needs its own immutable Git-consumer evidence before any layer
can advance to later promotion, renderer, Android, or named-device gates; evidence
from an earlier package or dependency tuple is not inherited.

Unity `6000.3.19f1` is the first automated implementation profile, not the
repository's generation limit. Another Unity, UI, XRI, or future engine tuple
begins as raw-material regeneration and earns its own profile only after equivalent
validation.

| Package | Version | Maturity | Earliest unsatisfied gate |
| --- | --- | --- | --- |
| `com.lingkyn.inventory.core` | `0.1.1` | `incubating` | `core_atomic_mutation_tests` |
| `com.lingkyn.inventory.unity` | `0.1.1` | `incubating` | `local_clean_consumer_editmode_tests` |
| `com.lingkyn.inventory.presentation` | `0.1.0` | `incubating` | `presenter_unit_tests` |
| `com.lingkyn.inventory.ugui` | `0.2.0` | `incubating` | `required_visible_state_replay` |
| `com.lingkyn.inventory.uitoolkit` | `0.1.0` | `incubating` | `semantic_state_and_intent_tests` |
| `com.lingkyn.inventory.xr.ugui` | `0.1.0` | `incubating` | `local_clean_consumer` |
| `com.lingkyn.inventory.xr.uitoolkit` | `0.1.0` | `incubating` | `local_clean_consumer` |

## Reference-library evolution

- Add coverage, extension seams, failure cases, and migration evidence to each
  reference entry as packages mature.
- Promote each optional XR renderer composition only after its own Android and
  named-device evidence without weakening the lower-layer boundaries.
- Add reusable tools, templates, and validation contracts when they have a real
  consumer and evidence.
- Consider Unreal Engine and Godot collections only when working implementations,
  maintainers, tests, samples, and engine-specific validation exist.
