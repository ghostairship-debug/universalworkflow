# R0-T03 - Surfaces, Docs, And Verification

## Basic Info

- Task ID: `R0-T03`
- Phase: `M2 Phase 0`
- Status: `completed`
- Depends On: `R0-T01`, `R0-T02`

## Goal

Expose reconcile planning and repair application through operator surfaces, then close the phase with docs and verification.

## Read Set

- `README.md`
- `m2_phase_docs/phase_0_runtime_reconcile_and_controlled_repair.md`
- `docs/task_cards/m2_phase_0_task_cards.md`
- `infra/scripts/offline_validation.py`
- `tests/`

## Write Set

- `README.md`
- `m2_phase_docs/phase_0_runtime_reconcile_and_controlled_repair.md`
- `docs/task_cards/m2_phase_0_task_cards.md`
- `infra/scripts/offline_validation.py`
- `tests/`

## Invariants

- docs reflect only implemented repair scope
- verification covers both dry-run and apply surfaces

## Implementation Steps

1. Add CLI and API reconcile surfaces.
2. Update README with repair planning/apply examples.
3. Extend verification to cover repair flows.
4. Backfill phase gate results after tests pass.

## Test Plan

- full `pytest`
- offline validation dry run if practical in the current environment

## Outcome

- CLI and API both expose reconcile planning and apply flows
- README documents operator repair usage
- full `pytest` passed with `67 passed`
- `offline_validation --skip-offline-probe` passed and now covers reconcile / repair
