# A3-T02 - Audit Report Surfaces And Regression

## Basic Info

- Task ID: `A3-T02`
- Phase: `M3 Phase 3`
- Status: `completed`
- Depends On: `A3-T01`

## Goal

Expose the run-audit report through CLI and API so review/handoff workflows can query one structured bundle directly.

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

- audit-report surfaces must stay read-only
- output must remain JSON-first and review-friendly

## Implementation Steps

1. Add `workflowctl run audit-report <run_id>`.
2. Add `GET /runs/{run_id}/audit-report`.
3. Add CLI/API regressions for auto and awaiting-review paths.

## Test Plan

- CLI audit-report regression
- API audit-report regression

## Outcome

- Added the audit-report CLI command and API route.
- Regression coverage now checks both completed and awaiting-review audit packets.
- Verified through `tests/test_api.py` and `tests/test_cli.py`.
