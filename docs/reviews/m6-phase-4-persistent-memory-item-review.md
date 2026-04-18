# M6 Phase 4 Review - Persistent Memory Item Baseline

## Scope

`M6 Phase 4` moves the `Memory` line from read-only candidates to the first durable `memory_items` baseline.

Implemented:

- persisted `MemoryItem` contract
- SQLite `memory_items` migration
- repository support for run/namespace query
- explicit candidate-to-item materialization
- CLI/API/offline-validation coverage for stored memory items

Still deferred:

- semantic retrieval or ranking
- cross-run selection heuristics
- automatic memory injection back into compile/resume
- simulation memory

## Verification

- `pytest tests/test_contracts.py tests/test_repositories.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - `183 passed`
- `pytest -q`
  - `192 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

## Result

- Phase gate passed.
- `Memory` now has a durable, operator-visible storage baseline while remaining bounded and non-semantic.
