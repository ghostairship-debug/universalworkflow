# P4-T02 - Review Policy Governance Surfaces

## Basic Info

- Task ID: `P4-T02`
- Phase: `M3 Phase 4`
- Status: `completed`
- Depends On: `P4-T01`

## Goal

Expose the review-policy governance report through CLI/API so policy visibility becomes part of normal operator/governance workflows.

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

- governance report remains read-only
- surfaces should stay JSON-first and predictable

## Implementation Steps

1. Add `workflowctl governance review-policy`.
2. Add `GET /governance/review-policy`.
3. Add CLI/API regression tests for the policy-governance surface.

## Test Plan

- CLI governance regression
- API governance regression

## Outcome

- Added the review-policy governance CLI command and API route.
- Regression coverage now checks supported policies, reference-only candidates, and `TD-006` linkage.
- Verified through `tests/test_api.py` and `tests/test_cli.py`.
