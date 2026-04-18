# G2-T01 - Tech-Debt Report Parser

## Basic Info

- Task ID: `G2-T01`
- Phase: `M3 Phase 2`
- Status: `completed`
- Depends On: `Phase 2 entry`

## Goal

Turn the canonical markdown registry into a structured governance report that later surfaces can reuse without inventing a second debt source of truth.

## Read Set

- `docs/tech-debt-registry.md`
- `docs/legacy_project_reference_uplift_plan.md`

## Write Set

- `packages/core_domain/governance.py`
- `tests/test_governance.py`

## Invariants

- markdown remains the canonical editable source
- parser output must normalize debt data without rewriting its meaning
- governance report must stay lightweight and read-only

## Implementation Steps

1. Parse the repaid and open-debt markdown tables.
2. Normalize rows into structured governance items.
3. Add useful rollups such as open count, status counts, planned-phase counts, and M3-focus items.
4. Cover the parser with a focused unit test using a synthetic registry file.

## Test Plan

- governance parser unit test

## Outcome

- Added a reusable governance report builder with normalized debt items and rollup counts.
- The report now includes `m3_focus_items` and freeze-review questions for later reassessment work.
- Verified through `tests/test_governance.py`.
