# M9-4A - Optional Review Policy Runtime Semantics

- Task ID: `M9-4A`
- Phase: `M9 Phase 4 - Optional Review Policy Completion`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9 Phase 3 complete`

## Goal

- Turn `optional` into an executable advisory-only review policy.
- Preserve backward-compatible semantics for the existing review-policy set.

## Out Of Scope

- new review-policy families
- governance seed updates
- debt registry closeout

## Read Set

- `packages/contracts/models.py`
- `packages/core_domain/service_lifecycle.py`
- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`

## Write Set

- Allowed:
  - `packages/contracts/models.py`
  - `packages/core_domain/service_lifecycle.py`
  - `packages/core_domain/services.py`
  - `tests/test_execution_loop.py`
- Avoid:
  - seed files
  - governance docs
  - current-state living docs

## Interfaces And Data Changes

- add `ReviewPolicy.optional`
- implement advisory-only runtime behavior:
  - auto review always runs
  - run terminal status follows execution return code
  - review effect is advisory-only
  - no human escalation is required

## Invariants

- existing `auto_only`, `recommended`, `human_required`, and `mandatory` behavior must stay intact
- review-policy logic must remain explicit and operator-readable
- no migration is required for the enum expansion

## Implementation Steps

1. Add `optional` to the review-policy enum/contracts.
2. Extend service helpers to compute effective review state for `optional`.
3. Update lifecycle terminal logic so `optional` records auto review but does not block completion/failure.
4. Add execution-loop tests for optional pass/fail behavior.

## Test Plan

- `python -m pytest tests/test_execution_loop.py -q`
- later `python -m pytest -q`

## Risks And Rollback

- Main risk: `optional` accidentally behaves like `recommended` or `mandatory`.
- Roll back by keeping policy branching explicit in one lifecycle path and validating both pass/fail terminal cases.

## Completion Evidence

- Actual modified files:
  - `packages/contracts/models.py`
  - `packages/core_domain/service_lifecycle.py`
  - `packages/core_domain/services.py`
  - `tests/test_execution_loop.py`
- Validation:
  - targeted lifecycle tests passed
  - later full `python -m pytest -q` passed
- Implementation note:
  - the shipped terminal states became `advisory_passed` and `advisory_failed` for effective review-state projection
