# M6 Phase 6 Review - Compile-Time Memory Brief Injection Baseline

## Scope

`M6 Phase 6` turns retrieval preview into the first explicit, opt-in compile-time memory bridge.

Implemented:

- compile/recompile support for explicit `memory_item_id` selection
- injected memory preview in compile responses, task packets, status-detail, inspection, and snapshots
- artifact-level proof that the memory brief survives into execution

Still deferred:

- automatic memory selection
- default-on memory injection
- semantic ranking or vector retrieval
- simulation runtime

## Verification

- `pytest tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - `155 passed`
- `pytest -q`
  - `196 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

## Result

- Phase gate passed.
- The repository now has an explicit memory-aware compile path that stays opt-in and backward-compatible by default.
