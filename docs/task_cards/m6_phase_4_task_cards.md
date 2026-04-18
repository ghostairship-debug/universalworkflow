# M6 Phase 4 Task Cards

**Phase:** `M6 Phase 4 - Persistent Memory Item Baseline`  
**Goal:** Move the `Memory` line from read-only projection to the first bounded persistent memory-item baseline.

## Task Cards

| Task | Size | Goal | Depends On | Primary Files | Verification | Done When |
| --- | --- | --- | --- | --- | --- | --- |
| `P4-T01` | `complex` | Add memory-item contract and SQLite persistence baseline | `Phase 4 entry` | `packages/contracts/*`, `infra/migrations/*`, `packages/core_domain/repositories.py`, `tests/test_contracts.py`, `tests/test_repositories.py` | contract + repository tests | memory items can be stored durably |
| `P4-T02` | `complex` | Materialize selected run memory candidates into stored items | `P4-T01` | `packages/core_domain/services.py`, `tests/test_execution_loop.py` | execution/service tests | at least one bounded materialization path works |
| `P4-T03` | `medium` | Expose memory-item query surfaces through CLI/API/docs/validation | `P4-T01`, `P4-T02` | `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `infra/scripts/offline_validation.py`, `README.md`, `tests/test_api.py`, `tests/test_cli.py` | CLI/API/validation tests | stored memory items are operator-visible |

## Closeout

- `P4-T01` completed: `MemoryItem` contract, migration, and repository baseline landed.
- `P4-T02` completed: selected run memory candidates can now materialize into durable `memory_items`.
- `P4-T03` completed: memory-item surfaces are exposed through CLI/API/docs/offline validation.
