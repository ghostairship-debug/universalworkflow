# Pre-M8 Phase C Task Cards

**Phase:** `Pre-M8 Phase C - Service Decomposition`  
**Goal:** Break `OrchestratorService` into bounded modules while keeping current workflow behavior stable.

## Task Cards

| Task | Size | Goal | Depends On | Primary Files | Verification | Done When |
| --- | --- | --- | --- | --- | --- | --- |
| `PM8-C1` | `medium` | Define the service-map and move shared service dataclasses/types out of `services.py` | `PM8-B complete` | `packages/core_domain/service_types.py`, `packages/core_domain/services.py`, `pm8_phase_docs/phase_c_service_decomposition.md` | targeted execution/governance tests | service bundle/context dataclasses no longer live inside `services.py` |
| `PM8-C2` | `complex` | Extract projection/reporting logic into a dedicated module without changing public behavior | `PM8-C1` | `packages/core_domain/service_projection.py`, `packages/core_domain/services.py`, `tests/test_execution_loop.py`, `tests/test_cli.py`, `tests/test_api.py` | execution-loop + CLI/API tests | summary/status/inspection/audit/reporting logic no longer lives directly in `services.py` |
| `PM8-C3` | `complex` | Extract memory and simulation logic into a dedicated module and keep operator surfaces stable | `PM8-C1`, `PM8-C2` | `packages/core_domain/service_memory_simulation.py`, `packages/core_domain/services.py`, `tests/test_execution_loop.py`, `tests/test_cli.py`, `tests/test_api.py` | execution-loop + CLI/API tests | memory/simulation service logic no longer lives directly in `services.py` |
| `PM8-C4` | `complex` | Extract lifecycle/review entry points into a dedicated module and reduce `OrchestratorService` to a thinner facade | `PM8-C1`, `PM8-C2`, `PM8-C3` | `packages/core_domain/service_lifecycle.py`, `packages/core_domain/services.py`, `README.md`, `docs/current_development_workflow.md`, `docs/reviews/pm8-phase-c-service-decomposition-review.md`, `tests/` | targeted + full validation | `OrchestratorService` remains the compatibility shell while bounded modules own the moved logic |

## Closeout

- `PM8-C1` completed: shared run bundle/context dataclasses now live in `packages/core_domain/service_types.py`.
- `PM8-C2` completed: projection/reporting/status/audit/dashboard logic moved into `packages/core_domain/service_projection.py`.
- `PM8-C3` completed: memory/simulation/domain-pack operator logic moved into `packages/core_domain/service_memory_simulation.py`.
- `PM8-C4` completed: compile/recompile/review/resume/cancel lifecycle entry points moved into `packages/core_domain/service_lifecycle.py`, and `OrchestratorService` now acts as a thinner compatibility facade.
