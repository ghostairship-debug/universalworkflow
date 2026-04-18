# M3 Phase 1 Task Cards

## Reassessment

- `M3 Phase 0` completed failure taxonomy and run-summary surfaces.
- The next gap is richer event inspection and stronger review / closure discipline across operator outputs and review materials.

## Phase Outcome

- `S1-T01` completed the event-digest, review-digest, and closure-audit baseline in the service layer.
- `S1-T02` exposed richer closure surfaces through CLI/API and expanded regression coverage.
- `S1-T03` updated docs, validation, review materials, and closed the phase with full verification.

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `S1-T01` | `complex` | Add richer event-digest / inspection helpers over existing timeline data | `Phase 1 entry` | `packages/core_domain/services.py`, `packages/contracts/events.py`, `tests/test_execution_loop.py` | `packages/core_domain/services.py`, `tests/test_execution_loop.py` | service tests | event inspection baseline |
| `S1-T02` | `complex` | Harden review / closure summaries through CLI/API surfaces | `S1-T01` | `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_api.py`, `tests/test_cli.py` | `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_api.py`, `tests/test_cli.py` | CLI/API tests | closure discipline surfaces |
| `S1-T03` | `complex` | Update review materials / validation and close the phase | `S1-T01`, `S1-T02` | `README.md`, `docs/reviews/`, `infra/scripts/offline_validation.py` | docs + validation + closeout | full `pytest` | phase closeout |

## Gate Checklist

- event inspection provides a richer digest than raw timeline without replacing raw events
- summary surfaces project closure / review discipline instead of only raw counts
- CLI and API expose the new event-inspection surface cleanly
- docs, review notes, and offline validation cover the new closure-audit baseline
- full `pytest` and offline validation pass

## Gate Result

- `pytest tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q` passed with `109 passed`
- `pytest -q` passed with `136 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe` returned `overall_passed=true`
- `M3 Phase 1` is ready for the next reassessment
