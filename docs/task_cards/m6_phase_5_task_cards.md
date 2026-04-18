# M6 Phase 5 Task Cards

**Phase:** `M6 Phase 5 - Memory Retrieval Preview And Selection Baseline`  
**Goal:** Add the first non-injective retrieval preview over stored `memory_items`, with bounded manual selection and operator-visible surfaces.

## Task Cards

| Task | Size | Goal | Depends On | Primary Files | Verification | Done When |
| --- | --- | --- | --- | --- | --- | --- |
| `P5-T01` | `complex` | Add retrieval-preview contract and selection logic over stored memory items | `Phase 5 entry` | `packages/contracts/*`, `packages/core_domain/services.py`, `tests/test_contracts.py`, `tests/test_execution_loop.py` | contract + service tests | retrieval preview can be generated deterministically |
| `P5-T02` | `medium` | Expose retrieval preview through CLI/API with manual item-id and namespace filters | `P5-T01` | `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_api.py`, `tests/test_cli.py` | CLI/API tests | operators can inspect retrieval preview without mutating runtime |
| `P5-T03` | `medium` | Extend docs and offline validation for the new retrieval-preview baseline | `P5-T01`, `P5-T02` | `infra/scripts/offline_validation.py`, `README.md`, `m6_phase_docs/*` | offline validation + docs review | retrieval preview is documented and validated end-to-end |

## Closeout

- `P5-T01` completed: retrieval-preview contract and deterministic selection logic landed.
- `P5-T02` completed: retrieval preview is exposed through CLI/API with namespace and explicit item-id filters.
- `P5-T03` completed: docs and offline validation now prove the non-injective retrieval baseline end-to-end.
