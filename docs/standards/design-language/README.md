# XR Foundry UI Design Language

One shared UI design language for every XR Foundry system. The goal is that a
multi-contributor, multi-agent library reads as a single product — not one visual
style for the inventory, another for settings, another for the next system. When a
new project composes several Foundry packages, the result should already look and
behave like one coherent interface.

This is a reusable visual and interaction **vocabulary and neutral token set**, not
a complete UI framework, component library, or headset integration. It sets design
intent; it never substitutes for real-device verification.

## Reference hierarchy

| Concern | Primary reference | Why |
| --- | --- | --- |
| **Visual** (surfaces, depth, layout, typography) | **Apple visionOS** | Its spatial glass / depth / 2D-first typography language is the clearest public spatial visual system. |
| **Interaction** (pointer, selection, sizing, states) | **PICO + Meta Horizon OS** | visionOS interaction is system-mediated gaze-and-pinch with no app-drawn pointer, which does not transfer to controller/ray headsets. The target headset class uses a controller ray, so interaction facts come from PICO and Meta. |

Vision Pro is the **primary** reference; PICO and Meta Horizon OS are **secondary**
overall but **primary for interaction**.

## What the language defines

- **Tokens** — canonical default values for surfaces (translucent spatial glass),
  accent, text, per-state slot colors, corner-radius scale, elevation, spacing, and
  hit-target minimums. An un-themed install already matches the shared look.
- **State model** — `normal / hover / selected / disabled`, multi-channel feedback
  (visual + audio + haptic), and the rule that a selected visual must clear when the
  action it started stops.
- **Content principles** — no persistent instructional microcopy on repeated
  elements; icon-conveys-type instead of redundant category text; short, specific
  labels; one primary action per view.
- **Interaction principles** — controller-ray world-space UI, trigger to select,
  ray/direct separation, `48 dp` minimum / `60 dp` primary hit targets with
  hit-slop, and no head-ray-as-primary-pointer.
- **Renderer adapter contract** — the renderer-neutral presentation contract holds
  no visual vocabulary; each renderer adapter exposes one injectable skin/theme seam
  that maps these tokens and ships a default skin with the canonical values.

The machine-readable standard is
[`ui-design-language-standard.json`](ui-design-language-standard.json). Its design
inputs are restricted to admitted positive external public sources listed in the
[positive-source manifest](source-manifest.json); consumer project code is not a
derivation source.

## How a package adopts it

1. Keep all visual vocabulary in the renderer adapter, never in the renderer-neutral
   presentation contract.
2. Expose a single injectable skin/theme seam (for UGUI, a `ScriptableObject`) that
   maps the tokens above and can be injected by a consumer to restyle without forking
   prefabs or code.
3. Ship a default skin populated with the canonical token values so the package looks
   correct with no consumer setup.
4. Follow the state model for interaction visuals and the content principles for what
   appears on screen.

## Reference implementation

The current Inventory renderer adapters contain injectable skin seams:

- UGUI [`InventorySkin`](../../../packages/unity/systems/inventory/com.lingkyn.inventory.ugui/Runtime/InventorySkin.cs)
  is a `ScriptableObject` with canonical default colors and optional font/9-slice
  sprites. `InventoryShellView.ApplySkin` propagates it through the panel views.
- UI Toolkit [`InventoryUiToolkitSkin`](../../../packages/unity/systems/inventory/com.lingkyn.inventory.uitoolkit/README.md#injecting-a-skin)
  provides the peer renderer seam and canonical default values.

These implementations are present in the tree; the former unmerged-proposal
wording no longer describes them. Optional artwork and visual evidence remain
separate: a source-level seam does not prove rounded-sprite rendering, State
Gallery appearance, accessibility outcomes, or any headset tuple. Evaluate the
exact renderer/package revision in a consumer before making those claims.

## Status and non-claims

`incubating` / proposed pending independent review. This standard:

- does **not** mandate rebuilding any existing package UI — adoption is per family
  through its own gate;
- copies **no** platform HIG asset, shader, component, font, or numeric spec —
  platform sources inform neutral roles and intent only;
- carries **no** device usability, comfort, or accessibility claim — those require a
  recorded device receipt for the exact composition.
