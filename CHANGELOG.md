# Changelog

All notable repository-level changes are documented here. Package-level API changes
live in each package's `CHANGELOG.md`.

## Unreleased

- Cross-check every package reference’s maturity and path against its explicit
  package-catalog identity, extending Inventory-only maturity checks to all live
  families and rejecting unknown package IDs. Added mutation regressions for all
  15 package references; this checks agreement, not promotion evidence.

- Passed the source gate for Platform services (`docs/standards/platform-services/`,
  WI-027: 12 sources across Meta, PICO, Steamworks, Apple Game Center and StoreKit,
  Unity Gaming Services, store policy, and two maintained open-source layers;
  Core gate 13 clauses, Unity adapter gate 8) and Quality tiers
  (`docs/standards/quality-tiers/`, WI-028: 11 sources across Unity XR display,
  render scale and foveation, OpenXR foveation, Meta, PICO, and Apple performance
  guidance, Unity Quality Settings and Adaptive Performance; Core gate 12,
  Unity adapter gate 9); queue candidates `NEXT-PLATFORM-SERVICES` and
  `NEXT-QUALITY-TIERS`. Every source URL is marked for a person to confirm.
- Staged the Haptics family (`staging/haptics`, WI-026): `com.lingkyn.haptics.core`
  (event and profile identity, the closed kind set transient / continuous /
  envelope with guard rails, an explicit registry, per-target profiles, an
  immutable state with play, stop, stop_all, and set_profile intents, last-one-wins
  per target, deterministic replay, the binding table from interaction intents
  and audio events, and the one intent channel with actor and revision) and
  `com.lingkyn.haptics.unity` (XRI impulse and OpenXR action routes behind an
  injectable output sink with a recording test double, profile assets with
  explicit references, envelope degrading to transient with a diagnostic). 86
  tests; coverage map 24 of 24 clauses. Authored, unexecuted.
- Resolved DLB-0003 (routine lane) by lazy consensus: the governance_policy
  window closed on 2026-09-23T14:00Z with no risk or counterexample delta, so
  the record carries OPT-ROUTINE-LANE with
  `decided_by: process:mandate.weekly-steward.v1`; milestone batch 2a records
  two resolved public deliberations.
- Recorded LESSON-011 (a family's typed intent seam is the one channel through
  which a person's UI, an agent adapter, a replay, and an import all change
  state, with a closed `IntentActor` set for attribution/replay only and an
  optional expected revision gated with a stable `state.stale` code) and gave
  every live family an explicit disposition (WI-024). Applied it to the staged
  Live Tuning and XR UI shell families: every `TuningIntent`/`ShellIntent`
  (`set`/`reset`/`reset_all`/`snapshot`/`apply_snapshot`/`export` and
  `open`/`close`/`focus`/`dock`/`follow`/`fold`/`unfold`) now carries an
  `IntentActor` (`player`, `agent`, `replay`, `import`; `player` by default)
  and an optional expected revision; `TuningState`/`ShellState` carry a
  monotonically increasing `Revision`, excluded from `Fingerprint`, that a
  stale expected revision is checked against before an intent's own rule ever
  runs; `TuningImport` tags every applied override `IntentActor.Import`; and
  `TuningIntentOutcome`/`ShellIntentOutcome` (the replay log) now carry the
  issuing actor and the revision after each outcome. Added source-rule tests
  proving the Live Tuning panel host/shell client/import path and both XR UI
  shell renderer adapters write state only through the one Core intent entry
  point, and tests proving a player-issued and an agent-issued copy of the
  same intent (including a dock verb resolved through the same `FocusSubject`
  and affordance) take the same path and settle on an equal state. Coverage
  maps: live-tuning 34 clauses (32 covered, 2 partial unchanged; 108 tests
  total), xr-ui-shell 33 of 33 clauses (112 tests total).
- Extended the staged XR UI shell Core (WI-023) with six new clauses (XUC-10..
  XUC-15): the ornament (one shell-owned fixed surface, never folded); a closed
  verb registry partitioning registered ids into wired and unwired, with one
  constant id and display word per verb; a single-valued `FocusSubject` claimed
  only by an explicit `Claim`, never a per-frame mirror; verb resolution that
  reads only that one value with no precedence chain; a queryable pre-press
  affordance that is never available for a target a press would refuse; and fold
  retaining a panel's full open/docked/following state, since fold and unfold
  change only visibility. Inverted the shell/live-tuning dependency this same
  item found: deleted `Runtime/LiveTuning/` from
  `com.lingkyn.xr-ui-shell.ugui` and its asmdef references, added the one generic
  `IShellPanelContent<TSlot>` panel-content seam to Core, and moved the join
  point into `staging/live-tuning/com.lingkyn.live-tuning.unity/Runtime/Shell/ShellTuningClient.cs`,
  where Live Tuning registers its own `tune` verb and reads the shell's
  `FocusSubject` like any peer client. Added a source-rule test proving no asmdef
  under `staging/xr-ui-shell` references any assembly outside `Lingkyn.XrUiShell.*`
  and no shell `Runtime` source mentions another family's namespace, and recorded
  LESSON-010 (a developer or tooling system is a peer client, never a dependency,
  of the systems it operates on). Coverage maps: xr-ui-shell 27 of 27 clauses (100
  tests), live-tuning unchanged at 24 of 26 clauses plus 5 new peer-client tests
  outside the numbered clauses (92 tests total). Authored, unexecuted: no Unity
  compiler has run over the code.
- Added `docs/benchmarks/shipped-game-gap-matrix.md`: the systems three shipped
  product shapes (rhythm action, object interaction, spatial creation) need,
  marked against what the library supplies today (5 verified, 6 staged, 9
  candidate, 3 missing, 1 deferred). `ROADMAP.md` ranks 12 to 21 are reordered
  from it: Haptics first, then four new candidates (Platform services, Quality
  tiers, Content packs, Spatial placement), then Tutorial, Objectives, Analytics,
  Dialogue, and Networking.
- Added the tunable surface protocol (WI-022): `docs/standards/live-tuning/tunable-surface.md`
  and `tunable-surface.schema.json` (`xr-foundry.tunable_surface.v1`) let a package with
  an explicit injectable seam — a skin/theme asset or any other design-time
  configuration asset with a live-apply entry point — declare, as data beside its
  `foundry.component.json`, exactly what a developer scaffold may tune: canonical
  id, closed kind (`float`/`int`/`bool`/`enum`/`colour`/`vector2`/`vector3`), default,
  guard rail (range/step or value set), seam-relative target, and an optional
  design-language token reference, so the scaffold's binding index, editors, and panel
  host stay package-agnostic. Added `validate_tunable_surfaces` (schema validity,
  cross-manifest canonical id uniqueness, default-in-range/value-set, target/seam
  membership, token resolution, and the two-way bind to the new
  `xr-foundry.tuning.surface` 1.0.0 capability in `capability-registry.json`) with
  14 tests in `tests/test_tunable_surfaces.py`. Shipped the first manifests for the
  Inventory UGUI and UI Toolkit renderer adapters, mapping their nine surface/text/
  slot-state colour skin members to the canonical design-language token values, and
  recorded LESSON-009 in the lessons register.
- Staged the XR UI shell family (`staging/xr-ui-shell`, WI-020):
  `com.lingkyn.xr-ui-shell.core` (panel, wrist-menu, and hand-menu identity; world,
  head-locked, wrist, and hand anchors; open, close, focus, dock, and follow
  intents on an immutable shell state with deterministic replay; typed pointer
  and gaze routing that resolves to exactly one panel; the skin contract mapping
  the shared design-language tokens to a closed slot set) and the sibling
  `com.lingkyn.xr-ui-shell.ugui` and `com.lingkyn.xr-ui-shell.ui-toolkit`
  adapters, each with one injectable skin seam and a default skin, sharing
  nothing but Core; the UGUI adapter is the first client of the live-tuning
  `ITuningPanelSurface` seam. 80 NUnit tests and a coverage map at 21 of 21
  clauses. Authored, unexecuted: no Unity compiler has run over the code.
- Resolved DLB-0001 (prototype-stage operating mandates) by lazy consensus:
  the governance_policy window closed on 2026-09-22T09:00Z with no risk or
  counterexample delta, so the record carries OPT-KEEP-MANDATES with
  `decided_by: process:mandate.weekly-steward.v1`, the first process-decided
  deliberation; milestone batch 2a marks that row done.
- Staged the Live tuning family (`staging/live-tuning`, WI-019):
  `com.lingkyn.live-tuning.core` (tunable identity, the closed kind set, an
  explicit registry, binding records, editor-kind resolution, an immutable
  tuning state with set, reset, snapshot, apply, and export intents, deterministic
  replay, and the design-language token bridge) and
  `com.lingkyn.live-tuning.unity` (skin binders, live apply with diagnostics, an
  injectable export sink with device JSON and Editor asset writers, and a panel
  host with one slot per binding behind an `ITuningPanelSurface` seam with a UGUI
  fallback), 74 NUnit tests and a coverage map at 21 of 23 clauses covered, 2
  partial. Authored, unexecuted: no Unity compiler has run over the code.
- Added the Live tuning family to the source-gate queue (`NEXT-LIVE-TUNING`) with
  its source manifest, verification contract, README, and admission draft under
  `docs/standards/live-tuning/`: in-headset tuning of design-language tokens and
  skin values (colour, size, corner radius, spacing) with export back to the
  assets that own them. `ROADMAP.md` ranks it 11, after the XR UI shell it
  composes on, and shifts the later ranks by one. Work items WI-018 (source gate,
  done) and WI-019 (staged Core and Unity adapter, open, needs no Editor) carry it.
- Refreshed the `docs/milestones.md` status cells against what merged this week:
  batch 1a records the capability declaration, batch 1f's cold-start receipt moves
  from open to partial (the schema, template, and rule exist; no receipt is filled
  and only a contributor who is not the maintainer can fill one), and batch 2c
  records that all three queued families passed the source gate while Locomotion
  and Scene flow are staged with coverage maps at 18 of 19 clauses each.
- Added `validate_api_surface_inventories` (WI-007), registered next to
  `validate_inventory_api_baseline` in `scripts/validate_repository.py`, so the
  Interaction, Persistence, and Settings `docs/standards/<family>/api-surface.md`
  inventories are derived from `Runtime/**/*.cs` instead of hand-typed: for each
  live package it re-derives the public `class`/`struct`/`enum`/`interface`/
  `record`/`delegate` declarations (excluding `Tests`, `Editor`, `Samples~`) with
  the same regex approach as the Inventory rule, reports any type the inventory
  omits or invents (naming family, file, and type), and checks the section's
  stated `N public types.` count against the derived count. Re-deriving all six
  packages found the three inventories already correct — Persistence Core 29,
  Persistence Unity 10, Settings Core 35, Settings Unity 17, Interaction Core 46,
  and Interaction Unity 19 public types all match their `Runtime/` sources with
  no missing, extra, or miscounted types — so no inventory text changed. New
  tests in `tests/test_api_surfaces.py` cover a matching inventory, a missing
  type, an extra type, a disagreeing stated count, a family with no inventory
  file, fix hints for each new error shape, and the real repository returning no
  errors.
- `scripts/merge_readiness.py` now discovers the deliberation record that
  authorises a governance change from the candidate's own changed files (WI-008):
  when `--deliberation-record` is not passed, `discover_deliberation_records`
  looks for any file added or modified under `docs/governance/deliberations/`,
  and `check_governance_boundary` evaluates the governance boundary against it —
  one candidate exactly as the explicit option would, several by requiring at
  least one that authorises the change (stated in the check's own detail text).
  An explicit `--deliberation-record` still wins, a change that adds only a new
  `Status: **Proposed**` RFC is still a proposal, and `--no-lazy-consensus` is
  unchanged. No CI workflow change was needed: the `merge-readiness` job already
  passes no `--deliberation-record`, so discovery now closes the first known gap
  in `docs/validation/checked-claims.md` without a new flag. Six new cases in
  `tests/test_merge_readiness.py` cover a governance change with no candidate
  record, a discovered open record inside its window, a discovered resolved
  record whose window closed, an explicit record winning over a losing
  discovered candidate, several candidates where only one authorises the
  change, and a non-governance change staying unaffected.
- `scripts/run_unity_gates.py` now reads each run boundary from the filesystem
  that will hold the results (a marker file's own mtime) instead of
  `time.time()`. Linux stamps a file from a coarse clock updated once per timer
  tick, so a result written microseconds after a fine-grained wall-clock reading
  could carry an earlier mtime and a perfectly fresh run was reported as stale;
  the contract suite failed that way on one CI runner while passing on the
  others. Both sides of the staleness check now share one clock, the check itself
  is unchanged and no test was weakened, and a repeated-pair regression test in
  `tests/test_run_unity_gates.py` covers it.
- The four family source manifests that carried no review note (Interaction,
  Persistence, Settings, Design language) now state that their URLs were not
  fetched from the authoring environment and that a person must confirm every URL,
  page path, and version pin, so `validate_family_source_manifests` suppresses
  nothing about them. Two findings remain allowlisted and are now work item
  WI-017: the design-language standard has a source manifest and no
  verification contract, and the foundations standard has a contract and no source
  manifest.
- Closed both allowlisted `FAMILY_SOURCE_MANIFEST_UNVERIFIED_CLAIMS` findings
  (WI-017): `docs/standards/design-language/verification-contract.md` now names a
  Source gate, a Reference hierarchy gate (exactly one primary visual and one
  primary interaction reference, cross-checked against `source-manifest.json`), a
  Token inventory gate (a bijection between the tokens `README.md` names and the
  keys under `design_tokens` in `ui-design-language-standard.json`), a Renderer
  adapter seam gate (one injectable skin/theme seam per adapter with a default
  carrying the canonical values, and no component, prefab, or scene defined by
  this standard), and a claim ceiling routing legibility, contrast, comfort, and
  any other perceived-quality claim to a Device Lab receipt, stating plainly that
  the family ships no package or test assembly so these clauses are checked by
  repository validation and human review, never a Unity test.
  `docs/standards/foundations/source-manifest.json` now names five admitted public
  sources in the same field set as `locomotion/source-manifest.json` (schema
  `xr-foundry.foundations_source_manifest.v1`): Unity's special-folder-name and
  custom-package-layout manual pages for `com.lingkyn.project-initializer`, the
  XR Interaction Toolkit `NearFarInteractor`/caster manual page and the OpenXR
  plug-in provider-setup manual page (both at the versions the `xr-baseline`
  compatibility profile resolves) for `com.lingkyn.xr-baseline`'s rig repair and
  provider dependency, and PICO's locomotion design guidance as platform evidence
  for a comfort-conservative default rig; every source is marked not fetched from
  the authoring environment with the same review-note wording the other family
  manifests use. `FAMILY_SOURCE_MANIFEST_UNVERIFIED_CLAIMS` in
  `scripts/validate_repository.py` is now an empty `frozenset()`, and
  `tests/test_source_manifests.py`'s real-repository test now asserts the
  allowlist is empty and the rule reports zero errors, rather than asserting the
  two suppressed messages are still produced.
- Generalised the Inventory-only source-manifest rule to every family (WI-006):
  `scripts/validate_repository.py` gains `validate_family_source_manifests`,
  registered next to `validate_consumer_lessons_register`, which checks every
  `docs/standards/<family>/source-manifest.json` other than Inventory's (which
  keeps its own stricter, unchanged rule) for a `schema` string matching
  `xr-foundry.<family>_source_manifest.v<N>`, a per-source `id`/`url`/`authority`/
  `admitted_role`/`admitted_claims`/`excluded_uses`/`license_or_terms`/
  `maintenance_evidence` field set, no source naming a private or consumer
  marker, a `verification-contract.md` and `source-manifest.json` existing
  together or neither, and a `review_note` (top-level or per-source) recording
  that source URLs were not fetched. `tests/test_source_manifests.py` covers
  every new error shape and pins the repository to zero errors. Design
  Language's missing verification contract, Foundations' missing source
  manifest, and the missing review note in Interaction, Persistence, Settings,
  and Design Language are allowlisted in `FAMILY_SOURCE_MANIFEST_UNVERIFIED_CLAIMS`
  until those files are fixed. `docs/validation/checked-claims.md` moves the
  "Source manifests of every other family" row from self-declared to
  machine-checked.
- Added the cold-start receipt (WI-009): `docs/contributing/cold-start-receipt.schema.json`
  and `docs/contributing/cold-start-receipt.template.json` are what an outside
  contributor fills after following `start-here.md` from a fork and landing one
  routine change — tool, starting commit, minutes per step, the pull request URL,
  the verdict, what was confusing, and at least one non-claim; `not_tested` is
  forbidden anywhere in a committed receipt. `scripts/validate_repository.py`
  gains `validate_cold_start_receipts`, which checks every
  `docs/validation/cold-start/*.json` against the schema, its filename against
  its own `id`, its `contributor` against the repository owner, its `capability`
  against `capability-profiles.json`, its `started_from_commit` against a
  fetched public origin ref, its `pull_request` URL, and unique step names.
  `start-here.md` points to it as milestone batch 1f's proof.
- Staged the Scene flow family under `staging/scene-flow/` (WI-004):
  `com.lingkyn.scene-flow.core` (scene set and scene identity, an immutable
  scene graph with one active scene per set, typed transition durations, the
  fade-out, loading, holding, fade-in machine advanced only by elapsed-time,
  load-completed, and load-failed intents, recovery to a declared fallback set,
  deterministic replay with a fingerprint; 32 authored tests) and
  `com.lingkyn.scene-flow.unity` (a scene binding asset, binding validation with
  stable codes and field paths, an injectable loader surface so EditMode loads no
  scene, and a runtime that reports every by-name resolution as a diagnostic; 21
  authored tests). `docs/standards/scene-flow/coverage-map.json` maps the
  contract to those tests: 18 of 19 clauses covered, CU-01 partial because the
  real loader surface needs a build-list scene. Nothing here has compiled or run.
- Staged the Locomotion and comfort family under `staging/locomotion/` (WI-002):
  `com.lingkyn.locomotion.core` (mode identity closed to teleport, snap turn,
  smooth turn, and continuous move; an anchor registry; a closed typed comfort
  policy over vignette, turn mode, turn increment, movement speed, and posture
  with fail-closed option codes; teleport, turn, move, and set-option intents on
  an immutable state with deterministic replay and a fingerprint; 32 authored
  tests) and `com.lingkyn.locomotion.unity` (a provider binding asset, binding
  validation with stable codes and field paths, an injectable provider surface,
  and a runtime that reports every by-name or optional resolution as a
  diagnostic; 22 authored tests). `docs/standards/locomotion/coverage-map.json`
  maps the contract to those tests: 18 of 19 clauses covered, AU-01 partial
  because an XR Interaction Toolkit provider cannot be constructed in EditMode
  without a rig. Nothing here has compiled or run.
- The repository now asks one question before any work is taken: what do you
  bring? `docs/contributing/capability-profiles.json` declares four capabilities
  (`ai_tokens_only`, `unity_editor`, `xr_headset`, `maintainer`), each with the
  question it answers, the work it reaches, and the claims it may never make;
  `docs/contributing/capabilities.md` is the page, and `AGENTS.md`, start-here,
  and the work-item protocol route through it. `scripts/open_work.py` gains
  `--list-capabilities` and `--capability <id>`, which narrows the board to the
  work that declaration can finish and says how many items need a different one;
  the board also surfaces the curated work items themselves (kind `work_item`,
  with `outside_contributor` as a blocker), so a token-only contributor sees real
  work instead of an almost empty board. `validate_capability_profiles` checks the
  schema, unique ids, that every profile reaches the `nothing` blocker, that
  `start_at` and `first_command` resolve, that the profiles' blocker vocabulary
  equals the board's with none unreachable, and that every capability a work item
  needs is declared by some profile; `tests/test_capability_profiles.py` covers
  the rule and the filtering.
- XR UI shell source gate (WI-005): `docs/standards/xr-ui-shell/` gains a
  source manifest (thirteen public sources, URLs not fetched and marked for a
  person to confirm), a verification contract (renderer-neutral Core gate with
  panel, wrist-menu, and hand-menu identity, anchor kinds, placement intents,
  pointer and gaze routing, and the design-language skin contract; UGUI and UI
  Toolkit sibling adapter gates each with one injectable skin seam; claim
  ceiling), a README with a disposition for every lesson and the rule that the
  Inventory presentation adapters become one client of the shell, and an
  admission draft; `NEXT-XR-UI-SHELL` joins the source-gate queue as a proposal
  with no package ids.
- Scene flow source gate (WI-003): `docs/standards/scene-flow/` gains a source
  manifest (seventeen public sources, URLs not fetched and marked for a person to
  confirm), a verification contract (Core gate with the transition state machine
  and fallback recovery, Unity adapter gate with the `scene.unregistered`
  diagnostic, claim ceiling), a README with a disposition for every lesson, and an
  admission draft; `NEXT-SCENE-FLOW` joins the source-gate queue as a proposal
  with no package ids.
- Locomotion and comfort source gate (WI-001): `docs/standards/locomotion/`
  gains a source manifest (twelve public sources, URLs not fetched and marked for
  a person to confirm), a verification contract (Core gate, Unity adapter gate,
  claim ceiling), a README with a disposition for every lesson, and an admission
  draft; `NEXT-LOCOMOTION-COMFORT` joins the source-gate queue as a proposal with
  no package ids.
- Proposed RFC 0008, scheduled steward execution inside the repository: one
  mandate-listed workflow on a `schedule` trigger with a read-only
  `GITHUB_TOKEN` and one scoped write secret, so the repository keeps moving when
  a person supplies only tokens instead of depending on one vendor's hosted
  session. Nothing takes effect until deliberation record DLB-0004 resolves
  (window closes 2026-10-01T19:00:00Z); the workflow file lands only after that
  with a person confirming the pinned action SHA.
- Added tool-neutral work items: `docs/contributing/work-items.json` cuts the
  milestone plan in `docs/milestones.md` into self-contained units (what to read,
  allowed paths, steps, acceptance commands, proof path) that any person or coding
  Agent can pick up without session context; `docs/contributing/work-items.md`
  is the protocol; `validate_work_items` in `scripts/validate_repository.py`
  checks the schema, unique ids, batch headings, dependency graph, `read_first`
  paths, accepted acceptance scripts, and that `done` carries an existing proof
  path, with fix hints and `tests/test_work_items.py`.
- Staged the Audio events family under `staging/audio/`: `com.lingkyn.audio.core`
  (event, bus, snapshot, anchor, and parameter identities; closed parameter
  contracts; immutable mix graph; intents applied to an immutable state with
  stable failure codes; 35 authored tests) and `com.lingkyn.audio.unity` (mixer
  binding asset, binding validation, an injectable mixer surface, and a runtime
  that reports every by-name mixer failure as a diagnostic; 18 authored tests).
  `docs/standards/audio/coverage-map.json` maps the verification contract to those
  tests (16 of 17 clauses covered, AU-02 partial). Nothing here has compiled or
  run; the staging README states the promotion steps.
- Live deliberation records are now machine-checked: `validate_live_deliberation_records`
  in `scripts/validate_repository.py` (registered right after
  `validate_operating_mandates`) proves, for every
  `docs/governance/deliberations/*.json`, that the record matches
  `docs/contributing/deliberation-record.schema.json` and
  `validate_governance_deliberation_metadata`, that its `id` equals the uppercased
  filename stem and is unique, that it names a `decision_class` whose minimum
  review window is derived from `docs/governance/governance-model.v1.json` (a
  record without a class is a finding, never a guess), that `review_opened_at`,
  `review_not_before`, and `decided_at` are RFC 3339 UTC and ordered with the
  window at least the class minimum, that a `process:<mandate_id>` decision names a
  mandate under `docs/governance/mandates/` that was in force, unexpired, and
  unrevoked at `decided_at` and that the record carries no `risk` or
  `counterexample` delta, and that every
  `https://github.com/Lingkyn/xr-foundry/blob/main/<path>` evidence link exists in
  the tree. An open record past its window is a pending process step and is not
  reported. Each error shape has a fix hint; DLB-0001, DLB-0002, and DLB-0003 pass
  with no allowlist. `tests/test_deliberation_records.py` covers the rule.
- Coverage maps are now machine-checked: `validate_coverage_map_claims` in
  `scripts/validate_repository.py` (full validation pass) proves, for every
  `docs/standards/*/coverage-map*.json`, that each gate's `test_assembly` is
  exactly one real `.asmdef` owned by the declared `package_id`, that every
  `tests[]` and `additional_tests_outside_clauses[]` entry names a real
  `[Test]`/`[TestCase]`/`[UnityTest]` method under that assembly (or a real
  `validator:` function / Python test), that coverage states agree with their
  `tests`/`missing` lists, that `summary` counts equal a recount, that clause ids
  are unique, and that no attributed test method is left unlisted; each error
  shape has a fix hint. The inventory map's three prose gate assemblies and its
  summary miscount (13 covered / 10 partial, declared 14 / 9) are carried in the
  labelled temporary allowlist `COVERAGE_MAP_UNVERIFIED_CLAIMS`, which itself
  fails the validator once an entry is no longer produced.
  `tests/test_coverage_claims.py` covers the rule.
- `docs/standards/inventory/coverage-map.json` now passes `validate_coverage_map_claims`
  with nothing suppressed: the prose `presentation` and `xr` gates are split into
  one gate per real test assembly (`presentation`, `presentation_ugui_editor`,
  `presentation_ugui_playmode`, `presentation_uitoolkit_editor`,
  `presentation_uitoolkit_playmode`, `xr_ugui_editor`, `xr_ugui_playmode`,
  `xr_uitoolkit_editor`, `xr_uitoolkit_playmode`) with exact `test_assembly` and
  owning `package_id` values, the receipt-only `package_and_consumer` and new
  `xr_device_lab` gates declare `test_assembly: null`, every clause keeps its id,
  text, coverage state, and `missing` list (a clause whose tests span assemblies
  stays in the gate holding most of them and names the rest in a `note`), the two
  UI Toolkit skin tests added after the audited commit are listed, and `summary`
  is recounted to 13 covered / 10 partial / 10 evidence gaps.
  `COVERAGE_MAP_UNVERIFIED_CLAIMS` is now empty and
  `test_real_repository_maps_pass_or_are_exactly_allowlisted` asserts the
  Inventory map produces no raw-rule message.
- Added the open-work board: `scripts/open_work.py` derives open items
  (`test_gap`, `evidence_gap`, `lesson_gap`, `family_proposal`,
  `staging_promotion`, `deliberation_open`, `roadmap_step`) from the coverage
  maps, lessons register, source-gate queue, staging READMEs, open deliberation
  records, and the roadmap execution order, classifies what each waits on and
  whether it is routine, and prints JSON or Markdown; `tests/test_open_work.py`
  covers it and `docs/contributing/open-work.md` explains that the board is
  generated, assigns nothing, and is never authoritative over its sources.
- `tests/test_repository_contract.py` now removes each `docs/validation/evidence/device-receipt-test-*` fixture directory when its test finishes (via `addCleanup`), keeps an `atexit` fallback for helpers used outside a `TestCase`, and sweeps stale fixture directories older than one hour at module setup so interrupted or concurrent runs no longer leave untracked evidence directories behind.
- Added public API surface inventories for the Persistence (39 public types),
  Settings (52), and Interaction (65) families under
  `docs/standards/<family>/api-surface.md`, derived from the Runtime sources, as
  the input to each family's next gate, the public API compatibility review.
  Each names the seams a consumer extends, the types recommended to stay
  binary-compatible, candidates for internal or sealed before a first release,
  and open questions (mixed throw-versus-result failure model, public seams
  nothing consumes, de facto wire formats without a bump policy).
- Inventory UI Toolkit: added the injectable `InventoryUiToolkitSkin` seam
  (LESSON-007) mapping the shared design-language tokens to inline styles on the
  document view, with a default skin carrying the canonical values, back-compat
  when no skin is injected, propagation to later-created slots, and two EditMode
  tests. No version, maturity, or evidence change; the LESSON-007 inventory
  disposition stays a gap until PR #81's UGUI seam lands.
- Foundations: closed three of the four open verification clauses with
  non-breaking refactors and tests. Project Initializer gained root-parameterized
  scaffold and validation entry points with a disposable-root test helper and
  tests for scaffold idempotence and the stable `INIT_*` issue codes; XR Baseline
  exposes the hover visual's resolution path to its test assembly and proves the
  once-per-component warning. XB-06 (Initialize Sandbox unresolved warning) stays
  partial because the menu hard-codes the real Sandbox scene path. Coverage map:
  11 of 13 clauses covered; four new tests unexecuted.
- Documentation consistency sweep: the root README, docs index, Agent guide,
  Foundry production line (new staging step between blueprint preview and
  `--write`), governance README, Agent contribution protocol, deliberation
  protocol (lazy consensus), GitHub playbook, and CONTRIBUTING now describe the
  merge-readiness verdict, the routine lane, and `staging/` for new families
  instead of the older maintainer-merge wording. Maturity, release, device,
  setting, and permission authority statements are unchanged.
- Localization staging: added the optional, fail-closed bridge to the Unity
  Localization package (presence via a `versionDefines` guard, string-table data
  through a consumer-filled delegate seam, stable `bridge.*` codes) with four
  EditMode tests that assert the opposite expectation in each configuration, and
  a domain-only `MessageCatalog` sample. The Localization coverage map is now 21
  of 21 clauses covered across 39 authored, unexecuted tests.
- Drafted the Audio family standard under `docs/standards/audio/`: README with
  capability and evidence boundaries and lessons dispositions, source manifest
  (eight sources, URLs marked for human confirmation because the authoring
  environment cannot fetch them), verification contract with stable failure
  codes for the Core and Unity AudioMixer adapter gates, and an admission draft
  valid against the admission schema. No package id is reserved and no code
  exists yet.
- Queued the family after Localization: `NEXT-AUDIO-EVENTS` in
  `docs/foundry/queue/next-batch.json` (audio event identity, mix and snapshot
  state, spatial attachment intents, thin Unity AudioMixer adapter) with its
  source requirements and next action; no package id is reserved.
- Lowered the contribution barrier for routine changes. Added
  `docs/contributing/start-here.md` (clone, one install command, one verdict
  command, push, five-line pull request), a five-line routine section at the top
  of the pull-request template with the long checklist kept for non-routine work,
  a "Routine lane" in the Task Hall stating that routine changes need no claim,
  lease, anchor, continuation receipt, or governance window (deliberation record
  DLB-0003 holds that rule open to objection until 2026-09-23), pointers from
  `CONTRIBUTING.md`, `AGENTS.md`, and the docs index, and a `hints` array in the
  validator's JSON output that attaches a fix hint to every error.
- Started the next system family. `staging/localization/` holds the first
  Localization Core (`LocaleId` with BCP 47 subtags and RFC 4647 lookup fallback,
  `MessageId`, an ICU MessageFormat subset with plural, select, exact selectors
  and quoting, CLDR cardinal rules for a declared language set, immutable tables,
  catalog resolution that reports the fallback chain, and a validator with stable
  codes) with 28 EditMode tests, the Unity adapter (ScriptableObject tables and
  catalogs with fail-closed authoring validation and stable codes, an explicit
  `SystemLanguage` map, a plain runtime with a `LocaleChanged` event) with 7
  EditMode tests, and `docs/standards/localization/` holds the standard README,
  source manifest, verification contract, coverage map (21 clauses, 20 covered),
  and the admission and blueprint drafts. The code has not compiled; it stays in staging,
  outside the catalog and every batch, until one Unity run produces its first
  compatibility profile, because the production line requires that profile to
  register a package. The source URLs could not be fetched from the authoring
  environment and are marked for confirmation by a person.
- Governance rule iteration by maintainer direction (2026-09-15, "act, keep the
  undo"), in one revertible commit: `GOVERNANCE.md` gains "Process-decided merges
  and lazy consensus". A routine change on a branch named by a live operating
  mandate merges by GitHub auto-merge once the merge-readiness verdict is ready
  and the required checks pass; governance deliberations whose window closes
  without an objection delta resolve by lazy consensus with
  `decided_by: process:<mandate>`; non-routine changes, overrides, maturity,
  releases, device claims, settings, and permissions stay with people. The Task
  Hall merge sentence, the mandate README, and the deliberation schema's
  `process:` identity changed with it, and deliberation record DLB-0002 holds the
  rule open to objection until 2026-09-29. The weekly steward mandate's matching
  extension (open pull requests and enable auto-merge on ready routine changes,
  record lazy-consensus resolutions, stage new families under `staging/`, extend
  tests and docs in live packages without version or evidence changes) landed in
  the next commit after the maintainer adjusted the Agent's harness permissions.
  Undo: revert those commits, or set the mandate's `revocation.status` to
  `revoked`. No workflow holds a write token; the one-time
  repository settings (allow auto-merge, required checks on `main`) remain the
  owner's act.
- Extended `scripts/merge_readiness.py` with the `mandated_branch` check,
  `decision_class`, `process_merge_eligible`, and lazy consensus (on by default,
  `--no-lazy-consensus` to disable), and made the `merge-readiness` CI job fail
  when a mandated branch is not process-merge eligible.
- Added the merge-readiness process: `scripts/merge_readiness.py` computes a
  `ready` or `blocked` verdict for a candidate branch from the repository's own
  rules (clean merge, repository contract on the merged tree, LESSON-008 version
  evidence, changelog discipline, maturity boundary, governance review windows,
  draft state, independent review), with contract tests, the advisory
  `merge-readiness` CI job on pull requests, `docs/contributing/merge-readiness.md`,
  and Proposed RFC 0007 describing the review path from advisory verdict to
  binding check. The verdict grants no permission; merge decisions stay with a
  maintainer at G0 x A0.
- Opened deliberation record DLB-0001 for the prototype-stage operating-mandates
  section added to `GOVERNANCE.md` on 2026-09-13, because the merge-readiness
  verdict correctly reports that governance-policy change as owing its 7-day
  public review. Added an "Execution order after Inventory" section to the
  roadmap.
- Weekly steward intake: recorded LESSON-008 (a package version bump is a
  verification claim) from the PR #81 block, with a disposition for every live
  family. No code change.
- Added the foundations family standard (`docs/standards/foundations/`): a
  minimal verification contract for `com.lingkyn.project-initializer` and
  `com.lingkyn.xr-baseline`, a coverage map binding its thirteen clauses to the
  six existing EditMode tests and naming the four still missing, the
  `RequiredFoldersAreUnderProjectRootAndUnique` test, and the
  `validate_foundation_assembly_references` repository rule that limits every
  foundation asmdef reference to Lingkyn or Unity-owned assemblies. LESSON-005 is now adopted
  for every live family.
- Closed every open test gap in the Inventory coverage maps: added the
  zero-quantity request test to Inventory Core and the invalid-limit diagnostic
  test to Inventory Unity, and added the `validate_inventory_isolation_rules`
  repository rule that pins the Presentation assembly to `Lingkyn.Inventory.Core`
  only and rejects `Resources.Load` and scene lookups in the authoring runtime.
  The nine remaining partial clauses are evidence gates.
- Audited every silent by-name resolution in the XR Baseline Editor tools and
  routed them through a new once-per-key `XrBaselineDiagnostics` warning, so
  `Initialize Sandbox` reports unresolved XRI, Input System, shader, or asset
  members instead of logging a clean success. LESSON-004 and LESSON-005 are now
  adopted for their remaining families, pending Editor execution.
- Authored the three Persistence Core and five Interaction Core tests their
  coverage maps had named, marking both maps fully covered pending Editor
  execution, and mapped the Inventory Unity authoring, Presentation,
  package-and-consumer, and XR gates in `coverage-map.json`, separating missing
  tests from evidence gates.
- Added clause-to-test coverage maps for the Persistence, Settings, and Interaction
  Core and Unity adapter gates, authored the six Inventory Core tests the Core map
  had named, stated in the Settings standard that accessibility category and
  feature id are open metadata, and made the XR Baseline hover visual warn once
  instead of silently idling when XRI members cannot be resolved.
- Added `scripts/run_unity_gates.py`: one command that finds a Unity Editor,
  generates a disposable host (the reference consumer, every live package, or one
  package plus its Foundry dependencies), audits exact test counts from source,
  runs each assembly in its own batchmode process, verifies every result, and
  writes a run receipt binding commit, host manifest, resolved lock, editor, and
  per-assembly verification. Covered by contract tests with a fake editor. Added
  `docs/validation/run-unity-gates.md` (what to test, how, what it proves) and the
  manual-dispatch `unity-self-hosted-gates` workflow for a maintainer-controlled
  machine registered as a self-hosted runner.
- Iterated the governance rules by maintainer direction: added prototype-stage
  operating mandates (`docs/governance/mandates/`, schema-validated) under the
  active `A0` path, recorded the weekly steward mandate, let `AGENTS.md` state that
  a mandated Agent acts within scope without asking, and marked bounded background
  automation as activated in the project profile. RFC 0006 membership, review
  windows for constitutional changes, and all GitHub permissions are unchanged.
- Added the `unity-consumer-tests` workflow: materializes the reference consumer,
  audits the exact test-case count of every test assembly from source with the new
  `scripts/audit_unity_test_inventory.py`, runs each assembly in its own pinned
  game-ci Unity process, verifies every result with
  `scripts/verify_unity_test_results.py`, and uploads the NUnit XML. It requires a
  Unity license secret and skips on fork pull requests. The audit reproduces every
  previously recorded Editor count and is covered by its own contract tests.
- Added Inventory decision material: proposal 0001 for a closed Item Kind beside
  open Tags (#85), the migration note from the single-renderer layout to the
  presentation-split graph, and a clause-to-test coverage map for the Core behavior
  gate that names six missing tests.
- Fixed the XR Baseline far-cast-distance repair (#21) to resolve the referenced
  `ICurveInteractionCaster`, return diagnostics, and fail visibly; Editor execution
  of its three new tests is pending.
- Added the consumer lessons register (`docs/standards/lessons/`): seven lessons
  drawn from Inventory's real consumer use and validation records, each with an
  explicit adopted, gap, deferred, or not-applicable disposition for every live
  package family. Repository validation now fails when a live family has not
  responded to a lesson, a gap or deferral lacks a follow-up, an evidence path is
  missing, or the register drifts from its schema or policy.
- Added a `docs/README.md` navigation index with a directory map, task-based
  reading orders, and the evidence rules shared by every documentation surface.
- Expanded the XR Baseline README and the Settings Core, Settings Unity, and
  Persistence Core package documentation with lifecycle, outcome, recovery,
  migration, factory-wiring, and non-goal detail derived from the shipped source.
  No package API, version, maturity, or evidence claim changed.
- Updated the roadmap to reflect both released Foundry batches, the 15 live Unity
  packages, the Localization queue proposal, and the XFCM composition gates.
- Documented a project-local virtual environment as the supported route for the
  pinned contract dependencies and ignored `.venv/`, `venv/`, and
  `.pytest_cache/`.
- Added proposed RFC 0006 and an inactive Agent-native membership foundation:
  `G0 x A0` current truth, `G0 x A1` phase-one target, AgentMember identity and
  mandate schemas, principal-and-lineage independence, evidence ancestry controls,
  a pinned Research-Lite manifest, and fail-closed authority boundaries. No Agent
  registry, account, GitHub App, wallet, token, chain, MCP service, or remote setting
  was activated.
- Added XFCM v0.1: RFC 0005, component/capability/composition schemas, colocated
  manifests for all 15 Unity packages, explicit renderer/XR variant slots, a
  deterministic 13-component Unity reference lock, consumer-owned lifecycle rules,
  visible pending cross-family adapters, and fail-closed composition validation.
- Kept the runtime data plane strongly typed and in process; MCP is reserved for a
  future optional external control-plane adapter. No whole-composition Unity,
  runtime, headset, or named-device evidence is claimed by structural resolution.
- Added the proposed DAO-ready XR Open Commons foundation: RFC 0004, a G0-G4
  governance maturity model, 7-day policy and 14-day constitutional review windows,
  emergency review bounds, a governance proposal form, source manifest, and
  machine checks that keep activation, automatic promotion, tokens, wallets,
  treasury, on-chain execution, organization transfer, and remote settings off.
- Hardened the repository foundation with a manually runnable Python 3.11-3.13
  validation matrix, dependency-aware pip caching, one canonical full contract
  command, a stable branch-protection aggregate check, monthly Python dependency
  updates, and validator tests that reject CI or Dependabot drift.
- Added the renderer-neutral Settings family: typed definitions and values,
  profiles, scoped transactions, whole-snapshot constraints, deterministic
  apply/reverse rollback, persistence seams, accessibility discoverability
  metadata, and a ScriptableObject Unity authoring adapter.
- Verified Settings Core (25 tests) and the combined Core/Unity graph (31 tests)
  from immutable Git UPM pins in clean Unity 6000.3.19f1 Windows Editor consumers.
- Added Foundry V1: a public lifecycle, official-source manifest, machine-readable
  first Unity batch, next source-gate queue, release policy, and deterministic
  dry-run-first Unity package scaffolder.
- Added fast structure feedback separately from the full repository contract and
  preserved exact-consumer and named-device evidence as stronger independent gates.
- Registered all nine implemented Unity packages in the first incubating batch
  without promoting maturity or inventing device claims.
- Established the canonical renderer-neutral Inventory package graph:
  `com.lingkyn.inventory.presentation`, peer UGUI and UI Toolkit renderers, and
  renderer-explicit XR compositions without a speculative shared XR-core package.
- Finalized the initialization layout under `packages/unity/foundations` and
  `packages/unity/systems/inventory`. Catalogs, install URLs, reference paths, and
  validation use that single layout; no old-path compatibility surface is kept.
- Added a version-adaptive reference contract: standards and tests may generate a
  target-specific candidate, while each installable manifest and support claim
  remains bound to an exact machine-validated compatibility profile.
- Bound the finalized package tree to nine exact Unity 6000.3.19f1 Editor
  compatibility profiles with immutable manifests, resolved locks, compile
  receipts, and applicable EditMode/PlayMode NUnit results. Evidence does not
  transfer across version, dependency, renderer, build, input, runtime, or device
  tuples.
- Added current official Unity world-space UI Toolkit, XRI UI Toolkit, PICO
  multimodal direction, and Apple spatial-design sources with bounded roles and
  explicit non-claim limits.
- Added a provider-neutral, machine-checkable Device Lab route with an Inventory
  world-space UI plan, PICO tracked-controller profile, and fail-closed promotion
  rules for install/open, world anchoring, targeting, interaction states,
  readability, reach, occlusion, and comfort.
- Added a provider-neutral, machine-checkable Inventory XR device receipt with a
  PICO tracked-controller acceptance profile, official PICO evidence boundaries,
  and fail-closed promotion rules for install/open, world anchoring, targeting,
  interaction states, readability, reach, occlusion, and comfort.
- Added the optional `com.lingkyn.inventory.xr` incubating package with a
  provider-neutral world-space prefab, ScriptableObject profile, fail-closed scene
  validation, tracked-ray and real XRI poke tests, and an imported setup sample;
  this earlier single-renderer route was subsequently replaced by the canonical
  renderer-explicit XR graph above, while Android and PICO evidence remain separate
  promotion gates.
- Added Agent Commons V1: a public, lease-based Task Hall and revision-bound Device
  Lab with machine-readable task/profile/receipt/label contracts, safe public forms,
  explicit permission boundaries, and provider-neutral agent guidance.
- Hardened validation CI with least-privilege permissions, fork-safe checkout,
  action pins at reviewed full commit SHAs, concurrency cancellation, and a bounded
  timeout; comment commands remain non-executable coordination text.
- Added parsed YAML workflow policy enforcement, runtime Draft 2020-12 task/device
  Schema validation, lifecycle/lease/gate invariants, enumerable Device Lab claims,
  deterministic result derivation, and extension-neutral public leakage scanning.
- Established UGUI `0.2.0` directly as the incubating renderer projection with
  functional nested prefabs, stable-address intents, bounded scrolling, semantic
  state samples, prefab-backed raycast tests, and cross-layer projection gates.
- Reopened the UGUI candidate after a structure-only false positive; `0.1.1`
  now ships functional nested prefabs, stable-address intents, bounded scrolling,
  semantic state samples, prefab-backed raycast tests, and cross-layer projection gates.
- Promoted UGUI `0.1.1` to candidate after immutable Git install, Input System-only
  sample setup, full package tests, and consumer-owned prefab-variant upgrade,
  rollback, and final-upgrade evidence passed; retained `0.1.0` as superseded history.
- Reconciled Inventory implementation, roadmap, package/reference catalogs, and
  promotion evidence; added a fail-closed projection-coherence validator and
  explicit earliest-unsatisfied gates for every Inventory package layer.
- Added the first Inventory Package Family standard with a positive-external-source
  whitelist, engine-light core and optional Unity UI/XR package boundaries, nested
  prefab composition, persistence and transaction contracts, and promotion gates.
- Added repository checks that reject consumer material, screened-out candidates,
  and non-positive sources from Inventory derivation inputs.
- Added the independently authored `com.lingkyn.inventory.core` incubating package,
  including atomic mutations, immutable snapshots, structured failures, policies,
  events, persistence envelopes, and deterministic/stateful invariant tests.
- Established the clean-history XR Foundry public foundation.
- Added consumer-neutral `com.lingkyn.*` Unity package identities.
- Added package and reference catalogs, coding-agent discovery adapters, maturity,
  validation, tests, samples, CI, community guidance, and security reporting.
- Root-anchored Unity build-output ignores so nested package build source remains
  tracked, with Git URL consumer and namespace-link regression validation.
