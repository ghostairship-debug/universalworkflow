# S1-T01 - Event Digest And Closure Audit

## Basic Info

- Task ID: `S1-T01`
- Phase: `M3 Phase 1`
- Status: `completed`
- Depends On: `Phase 1 entry`

## Goal

Turn the raw run timeline into a richer event-inspection surface with review digest and closure-audit semantics.

## Read Set

- `packages/core_domain/services.py`
- `packages/contracts/events.py`
- `docs/legacy_ai_agent_reference_plan.md`
- `tests/test_execution_loop.py`

## Write Set

- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`

## Invariants

- event inspection must stay derivative of persisted run state and persisted events
- closure audit must describe current run-centric semantics only
- raw timeline access must remain available

## Implementation Steps

1. Add event-digest helpers over the current run timeline.
2. Add review-digest and closure-audit helpers based on current summary / inspection state.
3. Expose a service-level `get_event_inspection` surface and extend summary projection.
4. Cover clean terminal, awaiting-review, and missing-terminal-event cases with tests.

## Test Plan

- service-level event inspection tests
- closure-audit regression tests

## Outcome

- Added service-level `event_digest`, `review_digest`, and `closure_audit` helpers plus `get_event_inspection`.
- `get_run_summary` now includes `closure_summary` and richer review counts / timestamps.
- Verified with `pytest tests/test_execution_loop.py -q` as part of the phase service regression set.
