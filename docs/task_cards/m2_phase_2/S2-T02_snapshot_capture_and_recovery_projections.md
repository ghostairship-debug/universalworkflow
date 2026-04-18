# S2-T02 - Snapshot Capture And Recovery Projections

## Basic Info

- Task ID: `S2-T02`
- Phase: `M2 Phase 2`
- Status: `completed`
- Depends On: `S2-T01`

## Goal

Capture snapshots at key lifecycle boundaries and use them to improve operator-facing recovery projections.

## Read Set

- `packages/core_domain/services.py`
- `packages/contracts/events.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Write Set

- `packages/core_domain/services.py`
- `packages/contracts/events.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Invariants

- snapshots must only summarize current repository state
- capture hooks must stay explicit and auditable
- recovery projections must remain read-mostly and operator-facing

## Implementation Steps

1. Add a service helper to capture snapshots after compile, resume/review, cancel, and repair.
2. Project latest snapshot through `status-detail` and `inspection`.
3. Append snapshot events to the timeline with lightweight payloads.
4. Add service, API, and CLI tests for snapshot capture and recovery projections.

## Test Plan

- compile snapshot tests
- auto/human terminal snapshot tests
- cancel / repair snapshot tests
- latest-snapshot projection tests

## Completion Note

Completed with explicit snapshot capture on compile, review-handoff, terminal, cancel, and repair paths, plus status / inspection projection coverage.
