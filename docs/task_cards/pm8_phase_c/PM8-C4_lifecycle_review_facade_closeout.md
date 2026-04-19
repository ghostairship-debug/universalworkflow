# PM8-C4 - Lifecycle, Review, And Facade Closeout

## Goal

Extract lifecycle/review entry points into a dedicated bounded module and leave `OrchestratorService` as a thinner compatibility facade.

## Write Set

- `packages/core_domain/service_lifecycle.py`
- `packages/core_domain/services.py`
- `README.md`
- `docs/current_development_workflow.md`
- `docs/reviews/pm8-phase-c-service-decomposition-review.md`
- `tests/test_execution_loop.py`
- `tests/test_cli.py`
- `tests/test_api.py`

## Verification

- targeted lifecycle/review tests
- full `pytest -q`
- `python -m infra.scripts.offline_validation --skip-offline-probe`

## Done When

- lifecycle/review entry points no longer live directly in `services.py`
- `OrchestratorService` remains the public entry point used by CLI/API/TUI
- phase review and living docs describe the decomposed service map and next approved phase
