# A5-T02 - Attempt Lifecycle And Interrupted Diagnostics

## Basic Info

- Task ID: `A5-T02`
- Phase: `M2 Phase 5`
- Status: `completed`
- Depends On: `A5-T01`

## Goal

Make compile / recompile / resume update attempt lineage explicitly, then project interrupted or superseded attempt mismatches through inspection and bounded repair.

## Read Set

- `packages/core_domain/services.py`
- `packages/contracts/events.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`
- `docs/legacy_project_reference_uplift_plan.md`

## Write Set

- `packages/core_domain/services.py`
- `packages/contracts/events.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Invariants

- interrupted diagnostics must stay operator-facing and bounded
- supersede semantics must reflect the current repository, not legacy workflow kernels

## Implementation Steps

1. Create and supersede attempts on compile / recompile / resume boundaries.
2. Add interrupted / superseded attempt diagnostics and repairability metadata where appropriate.
3. Project attempt state through status / inspection.
4. Add service, API, and CLI tests for attempt lineage and interruption cases.

## Test Plan

- attempt creation / supersede tests
- interrupted diagnostic tests
- operator projection tests
- API / CLI regression tests

## Outcome

- Compile / recompile / resume now maintain explicit runtime-attempt lineage, including supersede and terminal close semantics.
- `status-detail`, `inspection`, `reconcile`, and snapshot payloads now project attempt state and bounded interrupted-attempt repairs.
- Verified with `pytest tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q` (`97 passed`).
