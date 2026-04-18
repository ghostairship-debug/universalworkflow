# P4-T01 - Review Policy Catalog And Semantics Report

## Basic Info

- Task ID: `P4-T01`
- Phase: `M3 Phase 4`
- Status: `completed`
- Depends On: `Phase 4 entry`

## Goal

Create a governance-facing report that explains the currently supported review policies, their preset mappings, their operator-visible state matrix, and future reference-only candidates.

## Read Set

- `packages/core_domain/governance.py`
- `docs/reviews/m1_review_semantics_decision_table.md`
- `docs/tech-debt-registry.md`

## Write Set

- `packages/core_domain/governance.py`
- `tests/test_governance.py`

## Invariants

- runtime behavior must stay unchanged
- the report must describe current semantics and future candidates without promoting them to implemented runtime policies

## Implementation Steps

1. Parse the review semantics decision table.
2. Combine preset catalog, operator states, and debt linkage into a structured report.
3. Make future `optional / recommended / mandatory` candidates explicit as reference-only entries.
4. Add focused governance tests.

## Test Plan

- governance report tests

## Outcome

- Added a review-policy governance report that combines presets, current effective states, and future reference-only candidates.
- Linked the report back to `TD-006` so later phase reassessment can reason about remaining policy debt directly.
- Verified through `tests/test_governance.py`.
