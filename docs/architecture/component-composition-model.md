# XR Foundry Component and Composition Model v0.2

Status: implemented structural and source-bound adapter contract; full-composition
runtime and device evidence are pending.

The XR Foundry Component and Composition Model (XFCM) makes independently
installable packages behave as one governed product line. It gives every package a
machine-readable identity, names the capability contracts between packages, makes
variant selection explicit, and resolves a consumer-owned system definition into a
deterministic lock.

XFCM v0.2 proves **structural closure** and can bind an implemented
consumer-owned adapter to its exact source bytes. It does not infer that the
complete composition compiled, ran as a player, reached an XR runtime, or passed
on a device. Those stronger claims require their own exact evidence.

## The system boundary

XR Foundry is one system at the product-line level, not one mandatory binary and
not a collection of unrelated packages. The boundary has three planes:

1. **Runtime data plane.** Packages communicate through versioned, strongly typed
   interfaces, values, commands, semantic intents, and domain events. Per-frame or
   latency-sensitive traffic stays in process. An untyped global event bus, JSON
   serialization, reflection discovery, and a network protocol are not the default.
2. **Composition and control plane.** JSON manifests describe components,
   capabilities, variant slots, selected versions, lifecycle order, and the
   consumer-owned bindings between domains. A deterministic resolver produces the
   committed lock. A future MCP adapter may expose this plane to editors or Agents;
   MCP is not the runtime data plane.
3. **Assurance and distribution plane.** Repository checks, contract tests, exact
   consumer builds, compatibility profiles, and Device Lab receipts establish
   progressively stronger evidence. Distribution may later add registry or OCI
   projections without changing runtime contracts.

This split preserves package autonomy while giving the repository one technical
constitution. A package can be installed, versioned, tested, and replaced on its
own; a composition can still reject missing, incompatible, ambiguous, or cyclic
systems before integration work begins.

## Authority surfaces

The model has five machine-readable surfaces:

| Surface | Owns | Does not own |
| --- | --- | --- |
| `package-catalog.json` | package path, package version, maturity and package evidence state | capability semantics |
| `component-catalog.json` | one component manifest per package, lifecycle policy and variant slots | package release status |
| `capability-registry.json` | stable capability IDs, contract versions, provider set and contract references | concrete composition choice |
| `foundry.component.json` | one package's provided and required capabilities | another package's implementation |
| `foundry.project.json` / `foundry.lock.json` | requested system and exact deterministic resolution | compile, runtime or device proof |

The catalogs must agree. Every live `com.lingkyn.*` package has exactly one
colocated `foundry.component.json`; its ID, version and maturity must match both
`package.json` and `package-catalog.json`. Every provided or required capability
must exist at an exact version in the registry.

## Capability contracts

A capability ID names behavior, not a class name or implementation package. IDs
use the `xr-foundry.<domain>.<role>` namespace and carry an independent SemVer
contract version. Package versions and capability versions deliberately differ:
a package may ship implementation fixes without breaking its public capability.

XFCM uses exact capability versions. A breaking semantic change introduces a
new capability major version and a migration path. The resolver fails closed when:

- no selected component provides a required `id@version`;
- more than one selected component provides an exactly-one capability;
- a component declares a capability that the registry does not know;
- the registry's provider list differs from the component manifests; or
- component requirements differ from the package's internal Unity dependencies.

The last rule prevents a decorative manifest from describing a graph the actual
package manager cannot install.

All XFCM authority JSON is decoded with duplicate-key rejection at every object
depth. V0.2 composition and lock versions use SemVer 2.0 syntax, including the
numeric-prerelease no-leading-zero rule; v0.1 retains its original compatibility
contract.

## Variant slots

Some packages are peers, not cumulative dependencies. The component catalog
currently defines two slots:

- `inventory.renderer`: UGUI or UI Toolkit;
- `inventory.xr-surface`: XR UGUI or XR UI Toolkit.

A composition selects exactly one candidate for every slot. A mismatched pair,
such as the UGUI renderer with the UI Toolkit XR surface, cannot resolve because
the XR component requires its renderer-specific capability. This lets every
package remain part of the overall product line without pretending mutually
exclusive adapters should all run together.

## Composition algorithm

Resolution is intentionally static and deterministic:

1. load the component catalog, capability registry and requested composition;
2. add fixed components and exactly one component from each declared slot;
3. verify exact component versions;
4. resolve every component and root capability to exactly one selected provider;
5. resolve the declared cross-family binding endpoints;
6. reject dependency cycles;
7. sort providers before consumers, with lexical ordering as the stable tie-break;
8. for each v0.2 implemented binding, reject unsafe, linked, escaping, missing, or
   non-regular adapter source paths; require that the source belongs to the nearest
   unique regular Unity `.asmdef` and that its name equals the declared assembly;
   and bind the repository-relative path, assembly, and source SHA-256; and
9. lock component versions, manifest paths, manifest SHA-256 values, capability
   providers, slot choices, bindings, input digests and dependency order.

No timestamp, machine path, account, branch name, or mutable remote reference is
written to the lock. Re-running the resolver over identical inputs produces the
same JSON object.

Use:

```bash
python scripts/compose_system.py --check --json
python scripts/validate_repository.py --json --run-contract-tests
```

Maintainers may deliberately refresh a changed composition lock with:

```bash
python scripts/compose_system.py --write-lock --json
```

The full repository contract must still pass. A generated lock is not self-
approving evidence.

The original v0.1 manifest and lock schemas remain accepted for existing pending
bindings. V0.2 adds a structured `pending` or `implemented` binding state and
source binding; it does not silently promote or reinterpret a v0.1 lock.

## Lifecycle

V0.2 retains one declared lifecycle policy:

```text
configure -> start -> stop
```

The consumer composition root owns the lifecycle. Configure and start follow the
locked dependency order; stop follows reverse dependency order. Packages must not
discover one another by scanning loaded assemblies, hidden singletons, or scene
objects. A package may expose its own typed lifecycle API, but XFCM v0.2 does not
pretend that all current packages already implement one shared runtime interface.

## Cross-family bindings

Package dependencies express implemented compile-time edges inside a family.
Cross-family behavior belongs in a named binding or, once reusable, a dedicated
adapter component. It must not be hidden inside a renderer, global service locator,
or concrete domain dependency.

The Unity reference composition declares seven binding edges implemented by six
consumer-owned adapter sources:

- semantic interaction to Inventory intents;
- Inventory state to the persistence contract;
- Settings policy to semantic interaction;
- Unity Input System observations to semantic interaction;
- Inventory presentation to UGUI rendering and from that renderer to the XR
  surface (two edges implemented by one adapter); and
- Settings snapshots to persistence and rehydration.

Each implementation is a small, explicit C# adapter under the composition's
consumer root. The v0.2 resolver confines that source to the same composition,
rejects symbolic links and non-canonical paths, verifies the nearest effective
`.asmdef`, and records its exact source hash. `.asmref`-based adapter ownership is
not yet modeled and therefore fails closed rather than falling through to a parent
assembly.
`bindings_implemented: true` therefore means that all declared binding records have
source-and-assembly-bound implementations. It does **not** mean that C# semantics
were statically proved or that all selected packages or runtime paths were
executed. The lock still records `runtime_ready: false`. These filesystem checks
assume one serialized writer and no hostile same-privilege actor mutating the
worktree during a resolver run; cross-writer locking and descriptor-based TOCTOU
hardening remain future work.

## Evidence ladder

XFCM keeps these claims separate:

1. **Declared:** a component manifest is schema-valid.
2. **Structurally resolved:** all exact capabilities, variants and lifecycle edges
   close and the lock is current.
3. **Consumer compiled:** the exact locked set compiles in a clean Unity consumer.
4. **Runtime integrated:** binding tests pass in the exact consumer composition.
5. **Device verified:** named runtime, input, renderer and device evidence passes.

The committed 13-component reference system remains at level 2. The current
materializer embeds 11 packages, excluding the two foundation components. The
[consumer guide](../../compositions/unity/reference-system/consumer/README.md)
derives its complete test inventory from source; copied source and planned cases
are not execution evidence.

Historical bounded level-3/4 evidence includes the
[earlier double-loop receipt](../validation/experiments/2026-09-04-xag-xfcm-01-double-loop-result.md)
and the subsequent experiment published with
[PR #88](https://github.com/Lingkyn/xr-foundry/pull/88). The latter records an
11-package consumer and 146 EditMode plus 4 PlayMode cases across seven named
assemblies on its exact Unity `6000.3.19f1` macOS/Null-graphics tuple. Those are
historical executed cases, not the current source inventory or all embedded
package tests. Neither record promotes later package changes, unexecuted
components or the whole composition. Individual package evidence likewise does
not automatically promote a composition.

## MCP boundary

MCP is useful later as an optional adapter for questions and actions such as:

- list available components and capabilities;
- explain why a composition does not resolve;
- propose a slot substitution;
- generate a candidate composition or lock diff; and
- invoke bounded validation in an editor or automation host.

Such a server would call the same resolver and validation contract. It must not
become a required dependency of Unity builds, carry per-frame state, replace typed
domain interfaces, or gain release and repository authority.

## Reference influences

XFCM adopts patterns, not source code, from primary public projects:

- [ROS 2 design](https://github.com/ros2/design),
  [REP-149 package manifests](https://github.com/ros-infrastructure/rep/blob/master/rep-0149.rst),
  and [ROS 2 launch](https://github.com/ros2/launch): named interfaces, package
  metadata and explicit system launch/composition;
- [WebAssembly Component Model](https://github.com/WebAssembly/component-model)
  and [WIT](https://github.com/WebAssembly/component-model/blob/main/design/mvp/WIT.md):
  versioned imports/exports and future language-neutral boundaries;
- [Model Context Protocol architecture](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/architecture/index.mdx):
  capability negotiation and composable external control-plane servers;
- [O3DE project Gems](https://github.com/o3de/o3de-samples-project-gems):
  separately reusable engine modules assembled by a project;
- [OpenXR CTS](https://github.com/KhronosGroup/OpenXR-CTS): conformance is a
  separate evidence layer, not an architectural promise; and
- [glTF extension governance](https://github.com/KhronosGroup/glTF/blob/main/extensions/README.md):
  registered, versioned extensions rather than uncoordinated private conventions.

ROS-style dynamic discovery and serialization, a universal cross-engine ABI, an
MCP runtime bus, and a new package registry are deliberately deferred. They add
cost before the current Unity graph has proved its typed integration seams.

## Evolution gates

The next safe slices are:

1. expand the clean consumer from its current 11 embedded packages to the exact
   13-component lock and bind its generated Unity package lock;
2. make lifecycle configuration, start, failure rollback, and reverse stop an
   executable composition contract;
3. add composition-level player/runtime evidence without inheriting package-only
   or subset claims;
4. expose the resolver through an optional read-mostly MCP control adapter; and
5. generalize the manifest only after a real second engine implementation exists.

Every slice preserves the current fail-closed resolver and evidence ladder.
