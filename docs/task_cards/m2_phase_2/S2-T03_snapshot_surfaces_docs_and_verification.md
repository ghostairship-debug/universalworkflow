# S2-T03 - Snapshot Surfaces, Docs, And Verification

## Basic Info

- Task ID: `S2-T03`
- Phase: `M2 Phase 2`
- Status: `completed`
- Depends On: `S2-T01`, `S2-T02`

## Goal

Close the phase by exposing snapshot visibility through operator surfaces, updating docs, and running full verification.

## Read Set

- `README.md`
- `infra/scripts/offline_validation.py`
- `m2_phase_docs/phase_2_run_snapshot_baseline_and_recovery_projections.md`
- `docs/task_cards/m2_phase_2_task_cards.md`
- `tests/`

## Write Set

- `README.md`
- `infra/scripts/offline_validation.py`
- `m2_phase_docs/phase_2_run_snapshot_baseline_and_recovery_projections.md`
- `docs/task_cards/m2_phase_2_task_cards.md`
- `tests/`

## Invariants

- docs describe snapshot semantics accurately
- verification covers snapshot visibility plus recovery projections

## Implementation Steps

1. Expose snapshot query surfaces in CLI/API.
2. Update README with snapshot-aware status / inspect usage.
3. Extend validation to cover snapshot capture and listing behavior.
4. Backfill phase gate status after full verification.

## Test Plan

- full `pytest`
- offline validation dry run if practical

## Completion Note

Completed with `run snapshots` / `GET /runs/{run_id}/snapshots`, snapshot-aware README and validation coverage, `91 passed`, and `offline_validation --skip-offline-probe` returning `overall_passed=true`.
