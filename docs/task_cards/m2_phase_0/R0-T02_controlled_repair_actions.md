# R0-T02 - Controlled Repair Actions

## Basic Info

- Task ID: `R0-T02`
- Phase: `M2 Phase 0`
- Status: `completed`
- Depends On: `R0-T01`

## Goal

Introduce safe repair actions for the current bad-state catalog while leaving unsafe cases manual-only.

## Read Set

- `packages/core_domain/services.py`
- `packages/contracts/events.py`
- `packages/core_domain/errors.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`
- `docs/legacy_project_reference_uplift_plan.md`

## Write Set

- `packages/core_domain/services.py`
- `packages/contracts/events.py`
- `packages/core_domain/errors.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Invariants

- apply is explicit
- every applied repair is auditable
- unsafe cases return a stable error instead of guessing

## Implementation Steps

1. Add a reconcile/apply entry in the service layer.
2. Implement safe repairs for:
   - completed-but-live runtime
   - cancelled-but-live runtime
   - prepared snapshot residue
3. Keep missing-evidence review mismatches manual-only.
4. Add tests for dry-run plan vs apply behavior.

## Test Plan

- service repair tests
- API repair tests
- CLI repair tests

## Outcome

- safe repair actions are available for completed-live runtime, cancelled-live runtime, and prepared snapshot residue
- manual-only problems fail with a stable `repair_action_not_available` error
- every applied repair appends a `repair_applied` timeline event
