# M7 Phase 2 Task Cards

**Phase:** `M7 Phase 2 - Persistent Simulation Record Baseline`  
**Goal:** Turn on-demand simulation reports into auditable persisted records without yet auto-hooking them into every runtime transition.

## Task Cards

| Task | Size | Goal | Depends On | Primary Files | Verification | Done When |
| --- | --- | --- | --- | --- | --- | --- |
| `P2-T01` | `complex` | Add `SimulationRecord`, migration, repository, and record event lineage | `Phase 2 entry` | `packages/contracts/models.py`, `packages/contracts/events.py`, `packages/core_domain/repositories.py`, `infra/migrations/*`, `tests/test_contracts.py`, `tests/test_repositories.py` | contract + repository tests | simulation records can persist and be listed |
| `P2-T02` | `complex` | Add explicit record/list surfaces through service, CLI, API, and operator projections | `P2-T01` | `packages/core_domain/services.py`, `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_execution_loop.py`, `tests/test_api.py`, `tests/test_cli.py` | service + CLI/API tests | operators can persist and inspect simulation record history |
| `P2-T03` | `medium` | Update docs/offline validation and close the phase | `P2-T01`, `P2-T02` | `infra/scripts/offline_validation.py`, `README.md`, `m7_phase_docs/*` | offline validation + docs review | persistent simulation records are documented and validated |

## Closeout

- `P2-T01` completed: simulation records now persist through a dedicated contract, migration, repository, and timeline event.
- `P2-T02` completed: service, CLI, and API now support recording and listing simulation history, and operator projections expose the latest record.
- `P2-T03` completed: README and offline validation now cover simulation record persistence end-to-end.
