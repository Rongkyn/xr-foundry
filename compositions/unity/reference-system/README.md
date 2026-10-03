# Unity reference system composition

This directory contains the first XFCM composition root:

- `foundry.project.json` declares fixed components, variant choices, required
  capabilities, and source-bound cross-family adapters.
- `foundry.lock.json` pins the deterministic structural resolution, including
  component manifest hashes, adapter source hashes, and dependency order.
- `consumer/` contains the typed binding implementations and their bounded Unity
  integration harness.

The reference selects the Inventory UGUI renderer and XR UGUI surface. UI Toolkit
and XR UI Toolkit remain first-class alternatives in `component-catalog.json`; they
are not cumulative dependencies.

Check the lock with:

```bash
python scripts/compose_system.py --check --json
```

The current v0.2 lock structurally resolves 13 components and seven bindings
through six distinct consumer-owned adapter sources. The UGUI surface adapter
implements two binding edges. The materializer embeds 11 packages; the two
foundation components are outside this bounded harness.

Follow the [consumer instructions](consumer/README.md) to materialize a separate
project and derive every test assembly/count from its source. This operation
copies source; it does not execute Unity or establish compatibility.

`runtime_ready` remains false. The historical
[double-loop result receipt](../../../docs/validation/experiments/2026-09-04-xag-xfcm-01-double-loop-result.md)
records three earlier adapter paths, eight packages and its own exact test
inventory/tuple. The later experiment published with [PR #88](https://github.com/Lingkyn/xr-foundry/pull/88)
records an 11-package consumer and 146 EditMode plus 4 PlayMode cases across seven
named assemblies. Both receipts remain bound to their recorded inputs; later
source additions do not inherit those executions. Temporary-file backup recovery
is bounded evidence, not general filesystem durability. Neither those receipts
nor the current structural lock proves the complete 13-component runtime, a player build, controller or headset.

If you only need save/load, start with the
[Persistence quickstart](../../../docs/standards/persistence/quickstart.md)
instead of installing this multi-family reference harness.
