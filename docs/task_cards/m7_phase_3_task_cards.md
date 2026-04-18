# M7 Phase 3 Task Cards

**Phase:** `M7 Phase 3 - Simulation Lifecycle Hook Baseline`  
**Goal:** Turn simulation persistence into selected lifecycle lineage without spreading simulation across every runtime transition.

## Task Cards

| Task | Size | Goal | Depends On | Primary Files | Verification | Done When |
| --- | --- | --- | --- | --- | --- | --- |
| `P3-T01` | `medium` | Add explicit lifecycle sources for simulation records and event payloads | `Phase 3 entry` | `packages/contracts/models.py`, `packages/contracts/events.py`, `tests/test_contracts.py` | contract tests | simulation records can distinguish manual vs lifecycle origin |
| `P3-T02` | `complex` | Hook simulation recording into selected lifecycle control points and update CLI/API assertions | `P3-T01` | `packages/core_domain/services.py`, `apps/operator_cli/main.py`, `tests/test_execution_loop.py`, `tests/test_api.py`, `tests/test_cli.py` | service + CLI/API tests | selected lifecycle transitions automatically persist the right simulation lineage |
| `P3-T03` | `medium` | Update offline validation/docs and close the phase | `P3-T01`, `P3-T02` | `infra/scripts/offline_validation.py`, `README.md`, `m7_phase_docs/*` | offline validation + docs review | lifecycle-hook simulation behavior is documented and validated end-to-end |

## Closeout

- `P3-T01` completed: simulation records and events now carry explicit lifecycle-vs-manual provenance.
- `P3-T02` completed: selected lifecycle transitions now auto-record simulation and existing CLI/API surfaces expose the latest lifecycle source cleanly.
- `P3-T03` completed: README and offline validation now verify lifecycle-hook simulation behavior end-to-end.
