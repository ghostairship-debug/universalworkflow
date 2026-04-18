# M7 Phase 1 Task Cards

**Phase:** `M7 Phase 1 - Simulation Policy And Deterministic Report Baseline`  
**Goal:** Establish the first local-first `Simulation` slice through seed-backed policy resolution and one deterministic simulation report surface.

## Task Cards

| Task | Size | Goal | Depends On | Primary Files | Verification | Done When |
| --- | --- | --- | --- | --- | --- | --- |
| `P1-T01` | `complex` | Add simulation policy/report contracts plus the deterministic local simulation runner | `Phase 1 entry` | `packages/contracts/models.py`, `packages/core_domain/simulation.py`, `packages/core_domain/services.py`, `tests/test_contracts.py`, `tests/test_execution_loop.py` | contract + service tests | simulation policy resolves and deterministic reports can be produced |
| `P1-T02` | `complex` | Expose simulation report access through CLI/API and summary/audit surfaces | `P1-T01` | `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `packages/core_domain/services.py`, `tests/test_api.py`, `tests/test_cli.py` | CLI/API tests | operators can query simulation results without leaving existing surfaces |
| `P1-T03` | `medium` | Update docs/offline validation and close the phase | `P1-T01`, `P1-T02` | `infra/scripts/offline_validation.py`, `README.md`, `m7_phase_docs/*` | offline validation + docs review | the simulation baseline is documented and validated end-to-end |

## Closeout

- `P1-T01` completed: simulation policy/report contracts and the deterministic local runner now resolve and execute against existing run surfaces.
- `P1-T02` completed: CLI/API surfaces now expose simulation policies and per-run simulation reports, and summary/audit include the simulation digest.
- `P1-T03` completed: README and offline validation now cover the simulation baseline end-to-end.
