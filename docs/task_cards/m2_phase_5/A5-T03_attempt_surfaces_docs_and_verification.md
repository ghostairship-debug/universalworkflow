# A5-T03 - Attempt Surfaces, Docs, And Verification

## Basic Info

- Task ID: `A5-T03`
- Phase: `M2 Phase 5`
- Status: `completed`
- Depends On: `A5-T01`, `A5-T02`

## Goal

Close the phase by exposing runtime-attempt visibility through operator surfaces, updating docs, and running full verification.

## Read Set

- `README.md`
- `infra/scripts/offline_validation.py`
- `m2_phase_docs/phase_5_runtime_attempt_lifecycle_and_interrupted_recovery.md`
- `docs/task_cards/m2_phase_5_task_cards.md`
- `tests/`

## Write Set

- `README.md`
- `infra/scripts/offline_validation.py`
- `m2_phase_docs/phase_5_runtime_attempt_lifecycle_and_interrupted_recovery.md`
- `docs/task_cards/m2_phase_5_task_cards.md`
- `tests/`

## Invariants

- docs must describe attempt semantics accurately
- verification must cover attempt visibility plus interruption diagnostics

## Implementation Steps

1. Expose runtime-attempt query surfaces in CLI/API.
2. Update README with attempt-aware status / inspect usage.
3. Extend validation to cover attempt capture and interrupted diagnostics.
4. Backfill phase gate status after full verification.

## Test Plan

- full `pytest`
- offline validation dry run if practical

## Outcome

- Added dedicated runtime-attempt surfaces through `workflowctl run attempts` and `GET /runs/{run_id}/attempts`.
- Updated README, smoke, and offline validation so attempt visibility is part of normal operator acceptance.
- Verified with full `pytest -q` (`126 passed`) and `python -m infra.scripts.offline_validation --skip-offline-probe` (`overall_passed=true`).
