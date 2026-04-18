# S0-T01 - Failure Taxonomy And Summary Service

## Basic Info

- Task ID: `S0-T01`
- Phase: `M3 Phase 0`
- Status: `completed`
- Depends On: `Phase 0 entry`

## Goal

Define a stable operator-facing failure taxonomy and expose a structured run summary directly from the service layer.

## Read Set

- `packages/core_domain/services.py`
- `docs/legacy_project_reference_uplift_plan.md`
- `tests/test_execution_loop.py`

## Write Set

- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`

## Invariants

- summary must be derivative of existing stored state
- taxonomy must not introduce legacy workflow concepts

## Implementation Steps

1. Add failure taxonomy helpers based on current run / review / inspection semantics.
2. Add a service-level `get_run_summary` surface.
3. Cover success, human review, failure, and cancelled cases with tests.

## Test Plan

- summary service tests
- failure taxonomy tests

## Outcome

- Added service-level failure taxonomy helpers plus `get_run_summary`.
- Summary now condenses review state, inspection state, ownership projections, and timeline digest without replacing raw detail surfaces.
- Verified with `pytest tests/test_execution_loop.py -q` (`45 passed`).
