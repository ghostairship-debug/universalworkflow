# A5-T01 - Runtime Attempt Contract, Migration, And Repository

## Basic Info

- Task ID: `A5-T01`
- Phase: `M2 Phase 5`
- Status: `completed`
- Depends On: `Phase 5 entry`

## Goal

Create the persisted runtime-attempt baseline that later supersede and interrupted-run diagnostics can rely on.

## Read Set

- `packages/contracts/runtime.py`
- `packages/core_domain/repositories.py`
- `infra/migrations/`
- `tests/test_contracts.py`
- `tests/test_repositories.py`
- `docs/legacy_project_reference_uplift_plan.md`

## Write Set

- `packages/contracts/runtime.py`
- `packages/contracts/__init__.py`
- `packages/core_domain/repositories.py`
- `infra/migrations/`
- `tests/test_contracts.py`
- `tests/test_repositories.py`

## Invariants

- attempt data must stay run-centric and local-only
- no legacy project or phase/task-card ownership model may re-enter the repository

## Implementation Steps

1. Define the runtime-attempt contract and lifecycle states.
2. Add the migration and repository query/update methods.
3. Cover round-trip persistence and lifecycle validation with tests.

## Test Plan

- contract lifecycle tests
- repository round-trip tests
- latest / current / superseded query tests

## Outcome

- Added `RuntimeAttempt`, `RuntimeAttemptStatus`, and `RuntimeAttemptTrigger` to the contracts package.
- Added SQLite migration `007_m2_runtime_attempts.sql` plus repository methods for latest/current/superseded lineage.
- Verified with `pytest tests/test_contracts.py tests/test_repositories.py -q` (`25 passed`).
