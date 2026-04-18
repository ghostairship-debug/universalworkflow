# M6 Phase 3 Task Cards

**Phase:** `M6 Phase 3 - Memory Namespace Baseline And Run Memory Candidates`  
**Goal:** Start the `Memory` line with namespace definitions and read-only candidate projection, without introducing full retrieval or persistence complexity.

## Task Cards

| Task | Size | Goal | Depends On | Primary Files | Verification | Done When |
| --- | --- | --- | --- | --- | --- | --- |
| `P3-T01` | `complex` | Add memory namespace contracts, seed catalog, and load path | `Phase 3 entry` | `packages/contracts/*`, `packages/core_domain/memory.py`, `infra/seeds/memory_namespaces.json`, `tests/test_contracts.py` | contract tests | memory namespace catalog is loadable and explicit |
| `P3-T02` | `complex` | Build read-only run memory candidates from summary/evidence/audit data | `P3-T01` | `packages/core_domain/services.py`, `tests/test_execution_loop.py` | execution/service tests | runs can project structured memory candidates |
| `P3-T03` | `medium` | Expose namespaces/candidates through CLI/API/docs/offline validation | `P3-T01`, `P3-T02` | `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `infra/scripts/offline_validation.py`, `README.md`, `tests/test_api.py`, `tests/test_cli.py` | CLI/API/validation tests | the new memory baseline is operator-visible and documented |

## Closeout

- `P3-T01` completed: memory namespace contracts and seed catalog landed.
- `P3-T02` completed: runs can now project read-only memory candidates from existing run surfaces.
- `P3-T03` completed: memory namespace/candidate surfaces are exposed through CLI/API/docs/offline validation.
