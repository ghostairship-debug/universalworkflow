# B3-T03 - Budget Surfaces, Docs, And Verification

## Basic Info

- Task ID: `B3-T03`
- Phase: `M2 Phase 3`
- Status: `completed`
- Depends On: `B3-T01`, `B3-T02`

## Goal

Close the phase by exposing budget visibility through operator surfaces, updating docs, and running full verification.

## Read Set

- `README.md`
- `infra/scripts/offline_validation.py`
- `m2_phase_docs/phase_3_budget_ledger_baseline_and_enforcement_projections.md`
- `docs/task_cards/m2_phase_3_task_cards.md`
- `tests/`

## Write Set

- `README.md`
- `infra/scripts/offline_validation.py`
- `m2_phase_docs/phase_3_budget_ledger_baseline_and_enforcement_projections.md`
- `docs/task_cards/m2_phase_3_task_cards.md`
- `tests/`

## Invariants

- docs describe budget semantics accurately
- verification covers budget visibility plus enforcement behavior

## Implementation Steps

1. Expose budget query surfaces in CLI/API.
2. Update README with budget-aware status / inspect usage.
3. Extend validation to cover budget capture and enforcement behavior.
4. Backfill phase gate status after full verification.

## Test Plan

- full `pytest`
- offline validation dry run if practical

## Completion Note

Completed with `run budget` / `GET /runs/{run_id}/budget`, budget-aware README and validation coverage, `102 passed`, and `offline_validation --skip-offline-probe` returning `overall_passed=true`.
