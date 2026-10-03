# Reference-system binding consumer

This directory is the source template for the consumer-owned runtime bindings in
`../foundry.project.json`. It is deliberately not opened by Unity in place.
Materialize it into a clean temporary project before compiling or running tests so
generated `Library`, `Logs`, and `ProjectSettings` state cannot contaminate the
repository validator.

```bash
python scripts/materialize_reference_consumer.py --output ../xr-foundry-reference-consumer
python scripts/audit_unity_test_inventory.py ../xr-foundry-reference-consumer
```

Run these commands from the repository root. Choose a new output directory
outside the checkout; the materializer refuses an existing output. It embeds 11
packages for seven binding edges implemented by six adapter sources. The template
pins Unity `6000.3.19f1`; it does not prove the complete 13-component composition.
Historical macOS Editor/Null-graphics results belong to their recorded revisions,
not automatically to this template revision. No Unity run is performed by either
command above.

The harness contains six production adapter paths:

- Unity Input System observations to semantic interaction routing;
- semantic interaction events to Inventory selection intents;
- Inventory snapshots to the persistence contract and codec; and
- scoped Settings changes to interaction policy;
- Inventory presentation to the selected UGUI world-space XR surface; and
- Settings snapshots through the persistence contract and back into the
  Settings coordinator.

Its tests use deterministic raw Input System observations, synthetic semantic
input, recording views, and the shipped UGUI/XR world-space prefab. Unless a test
explicitly selects `LocalFileSaveStore`, storage is in memory. A passing suite
includes one real temporary-filesystem backup-recovery path and a real selected
renderer surface, but does not imply general filesystem durability, controller,
player, headset, or device proof.
The composition root must load a Settings snapshot before initializing the policy
adapter; automatic load-after-initialize resynchronization is not implemented.

Unity Test Framework can return success when no tests ran. Every EditMode and
PlayMode result must therefore pass `scripts/verify_unity_test_results.py` in
addition to the Unity process exit code. The caller must use a result path that did
not exist before the run, record the Unix epoch immediately before launching
Unity, and supply that boundary together with the source-audited exact test count
and assembly name. Each assembly is verified separately. Derive the complete
inventory from the materialized project using the command above, or emit one mode
for a CI matrix:

```bash
python scripts/audit_unity_test_inventory.py ../xr-foundry-reference-consumer --mode EditMode --github-matrix
python scripts/audit_unity_test_inventory.py ../xr-foundry-reference-consumer --mode PlayMode --github-matrix
```

The audit includes both the reference consumer's tests and all embedded package
test assemblies. A list containing only selected binding-related assemblies is
not the whole project inventory. Do not reuse a historical total or learn the
expected count from the XML being checked. Source-audited counts are planned
cases, not passed tests.

To execute the assemblies with a licensed pinned Editor, use the existing
[Unity gate runner](../../../../docs/validation/run-unity-gates.md), which
materializes its own disposable consumer and verifies fresh per-assembly results.
This does not establish a player, physical-controller or headset claim.

For a smaller first consumer that only saves and loads one DTO, use the
[Persistence quickstart](../../../../docs/standards/persistence/quickstart.md).
