# P0-T02 - Runtime Escalation And Projection

**Phase:** `M4 Phase 0`
**Status:** Completed

## Goal

Implement the actual execution-time routing for `recommended` and `mandatory`, and keep operator-facing review projections backward-compatible.

## Scope

- `recommended`
  - auto pass => `completed`
  - auto fail => `awaiting_review`
- `mandatory`
  - auto review always runs
  - human sign-off always required
- projection compatibility
  - if the run is still `awaiting_review` and there is no human verdict yet, operator surfaces should show `human_pending`

## Acceptance

- service-level execution tests cover pass and escalation cases
- CLI/API tests cover the new policies
- no existing `auto_only` / `human_required` behavior regresses

## Result

- `recommended` now escalates to human review only when the auto verdict fails.
- `mandatory` now always waits for human sign-off after execution, while still recording the auto verdict.
- `effective_review_state` stays backward-compatible by projecting `human_pending` whenever the run is still awaiting human action.
- Verified with `pytest tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q` (`124 passed`).
