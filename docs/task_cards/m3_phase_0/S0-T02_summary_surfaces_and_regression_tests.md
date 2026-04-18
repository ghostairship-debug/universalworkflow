# S0-T02 - Summary Surfaces And Regression Tests

## Basic Info

- Task ID: `S0-T02`
- Phase: `M3 Phase 0`
- Status: `completed`
- Depends On: `S0-T01`

## Goal

Expose the structured run summary through CLI and API, then verify the surface stays aligned with current lifecycle behavior.

## Read Set

- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Write Set

- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Invariants

- summary output should remain concise and stable
- raw detail surfaces must stay available

## Implementation Steps

1. Add dedicated summary routes / commands.
2. Wire them to the service summary surface.
3. Add CLI/API regression tests for auto and human-review paths.

## Test Plan

- API summary tests
- CLI summary tests

## Outcome

- Added `workflowctl run summary <run_id>` and `GET /runs/{run_id}/summary`.
- Summary regression now covers success and review-pending paths through CLI and API.
- Verified with `pytest tests/test_api.py tests/test_cli.py -q` (`59 passed`).
