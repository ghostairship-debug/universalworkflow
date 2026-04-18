# C1-T02 - Service Claim Lifecycle And Stale Repair

## Basic Info

- Task ID: `C1-T02`
- Phase: `M2 Phase 1`
- Status: `completed`
- Depends On: `C1-T01`

## Goal

Enforce local claim acquisition and release in the service layer, and make stale or wrongly-live claims diagnosable and repairable.

## Read Set

- `packages/core_domain/services.py`
- `packages/core_domain/errors.py`
- `packages/contracts/events.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Write Set

- `packages/core_domain/services.py`
- `packages/core_domain/errors.py`
- `packages/contracts/events.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Invariants

- `resume` must never execute without a claim
- terminal or review-waiting states must not keep live claims
- stale claim repair must stay explicit and audited

## Implementation Steps

1. Acquire a claim before runtime execution begins.
2. Release claims on terminal, cancel, and review-handoff paths.
3. Add stale / wrongly-live claim inspection problems and repair actions.
4. Add service, API, and CLI tests for conflict and stale repair.

## Test Plan

- duplicate resume conflict tests
- auto path release tests
- human-review release tests
- stale-claim repair tests

## Completion Note

Completed with claim acquisition during `resume`, explicit release / expire handling, claim-aware inspection and reconcile actions, plus service/API/CLI regression coverage.
