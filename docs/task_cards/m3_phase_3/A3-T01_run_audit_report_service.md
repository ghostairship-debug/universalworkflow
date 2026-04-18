# A3-T01 - Run Audit Report Service

## Basic Info

- Task ID: `A3-T01`
- Phase: `M3 Phase 3`
- Status: `completed`
- Depends On: `Phase 3 entry`

## Goal

Create a single structured audit bundle for a run by composing the already-existing operator surfaces instead of inventing a new runtime model.

## Read Set

- `packages/core_domain/services.py`
- `m3_phase_docs/phase_2_governance_projection_and_tech_debt_visibility_baseline.md`

## Write Set

- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`

## Invariants

- audit bundle must be fully derivative of existing persisted state
- summary / event inspection / state inspection remain first-class surfaces on their own

## Implementation Steps

1. Add a service-level `get_run_audit_report`.
2. Package summary, event inspection, state inspection, review packet, and recent timeline tail into one structure.
3. Cover auto-terminal and awaiting-review paths with service tests.

## Test Plan

- service-level audit-report tests

## Outcome

- Added a stable `get_run_audit_report` surface with `review_packet` and `timeline_overview`.
- Audit output now provides a review-ready bundle without replacing raw surfaces.
- Verified through `tests/test_execution_loop.py`.
