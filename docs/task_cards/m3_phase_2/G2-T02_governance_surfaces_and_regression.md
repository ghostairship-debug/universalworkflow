# G2-T02 - Governance Surfaces And Regression

## Basic Info

- Task ID: `G2-T02`
- Phase: `M3 Phase 2`
- Status: `completed`
- Depends On: `G2-T01`

## Goal

Expose the governance report through normal operator surfaces so debt visibility is queryable instead of hidden inside the docs tree.

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

- governance surfaces must stay read-only
- output must reflect the registry directly
- CLI/API shape should stay simple and JSON-first

## Implementation Steps

1. Add `workflowctl governance tech-debt`.
2. Add `GET /governance/tech-debt`.
3. Add CLI/API regression tests against the real registry-backed report.

## Test Plan

- CLI governance regression
- API governance regression

## Outcome

- Added the governance CLI command and API route.
- Regression coverage now checks that `TD-010` and M3 focus items are visible through both surfaces.
- Verified through `tests/test_api.py` and `tests/test_cli.py`.
