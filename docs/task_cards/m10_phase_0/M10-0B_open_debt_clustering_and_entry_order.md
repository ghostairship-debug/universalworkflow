# M10-0B - Open Debt Clustering And Entry Order

- Task ID: `M10-0B`
- Phase: `M10 Phase 0 - Post-M9 Rebaseline And Scope Freeze`
- Status: `completed`
- Depends On: `M10-0A`

## Goal

- Cluster `TD-001` and `TD-009` into concrete `M10` implementation slices.
- Rank those slices by dependency order, blast radius, and validation readiness.

## Out Of Scope

- retiring debt items
- writing future `M10` task-card packs
- implementing the chosen slices

## Read Set

- `docs/tech-debt-registry.md`
- `docs/governance/tech_debt_registry.json`
- `docs/task_cards/m2_phase_1_task_cards.md`
- `docs/task_cards/m2_phase_4_task_cards.md`
- `docs/task_cards/m2_phase_5_task_cards.md`
- `packages/core_domain/governance.py`
- `tests/test_governance.py`
- `docs/adrs/ADR-005.md`

## Write Set

- Allowed:
  - `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`
  - `docs/task_cards/m10_phase_0_task_cards.md`
- Avoid:
  - code changes
  - future phase files
  - debt-retirement wording

## Interfaces And Data Changes

- documentation only
- add an explicit candidate-theme matrix and recommended entry order for `M10`

## Invariants

- preserve `TD-001` and `TD-009` as the source debts entering `M10`
- do not silently treat hosted multi-node scheduling as the default meaning of debt repayment
- keep the ranking anchored in current repository architecture and validation costs

## Implementation Steps

1. Re-read the open debt set against the `M10-0A` baseline.
2. Split the debt into a small number of implementation slices.
3. Rank slices by dependency order and blast radius.
4. Record the ordered result in the phase doc and index.

## Test Plan

- documentation audit
- consistency check between the debt registry, governance wording, and the phase doc

## Risks And Rollback

- Main risk: the ranking collapses into one oversized `M10` bucket.
- Roll back by enforcing a small number of distinct slices with explicit dependency statements.

## Completion Evidence

- Actual modified files:
  - `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`
  - `docs/task_cards/m10_phase_0_task_cards.md`
  - `docs/reviews/m10-phase-0-post-m9-rebaseline-and-scope-freeze-review.md`
- Final candidate ordering:
  1. Theme A - ownership topology and coordination semantics
  2. Theme B - barrier and parallel execution semantics
  3. Theme C - true external worker pools or multi-node scheduling
- Disagreements found between debt wording and current code reality:
  - none material
  - the debt registry, governance release-readiness wording, and current code all agree that `TD-001` and `TD-009` remain open and belong in `M10`
