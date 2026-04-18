# S1-T02 - Event Inspection Surfaces And Regression Tests

## Basic Info

- Task ID: `S1-T02`
- Phase: `M3 Phase 1`
- Status: `completed`
- Depends On: `S1-T01`

## Goal

Expose the richer event-inspection and closure-summary surfaces through CLI and API, then lock them down with regression tests.

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

- CLI/API outputs must remain JSON-first and operator-friendly
- summary and event inspection should complement each other rather than duplicate raw timeline output

## Implementation Steps

1. Add `workflowctl run event-inspection <run_id>`.
2. Add `GET /runs/{run_id}/event-inspection`.
3. Expand summary regression tests to check closure / review counts.
4. Add CLI/API event-inspection regression tests for auto and human-review paths.

## Test Plan

- API event-inspection tests
- CLI event-inspection tests

## Outcome

- Added the `run event-inspection` CLI command and `/runs/{run_id}/event-inspection` API route.
- CLI/API regressions now cover closure state and review-request / review-submission counts.
- Verified with `pytest tests/test_api.py tests/test_cli.py -q` as part of the phase surface regression set.
