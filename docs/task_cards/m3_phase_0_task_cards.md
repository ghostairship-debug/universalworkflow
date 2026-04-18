# M3 Phase 0 Task Cards

## Reassessment

- `M2 Phase 5` completed runtime-attempt lineage and attempt-aware repair surfaces.
- The next gap is not more raw runtime state; it is the lack of a concise operator summary and explicit failure taxonomy.
- This phase therefore establishes a structured summary layer before any deeper governance automation or dashboard work.

## Phase Outcome

- `S0-T01` completed the failure taxonomy and service-level run summary baseline.
- `S0-T02` exposed the summary through CLI and API with regression coverage.
- `S0-T03` updated docs / validation and closed the phase with full verification.

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `S0-T01` | `complex` | Add failure taxonomy helpers and a structured run-summary service surface | `Phase 0 entry` | `packages/core_domain/services.py`, `docs/legacy_project_reference_uplift_plan.md`, `tests/test_execution_loop.py` | `packages/core_domain/services.py`, `tests/test_execution_loop.py` | service tests | run-summary baseline |
| `S0-T02` | `complex` | Expose the summary via CLI/API and add regression coverage | `S0-T01` | `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_api.py`, `tests/test_cli.py` | `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_api.py`, `tests/test_cli.py` | CLI/API tests | operator summary surfaces |
| `S0-T03` | `complex` | Update README / validation / review docs and run full verification | `S0-T01`, `S0-T02` | `README.md`, `infra/scripts/offline_validation.py`, `m3_phase_docs/phase_0_failure_taxonomy_and_run_summary_baseline.md`, `tests/` | docs + validation + closeout | full `pytest` | phase closeout |

## Gate Checklist

- summary surface condenses closure and failure state without hiding raw detail
- failure taxonomy is explicit and tested
- CLI and API expose the summary cleanly
- docs and validation cover the new summary surface
- full `pytest` passes

## Gate Result

- `pytest -q` passed with `131 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe` returned `overall_passed=true`
- `M3 Phase 0` is ready for the next reassessment
