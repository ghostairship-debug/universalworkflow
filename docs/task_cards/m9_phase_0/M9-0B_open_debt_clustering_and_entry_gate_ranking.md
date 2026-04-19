# M9-0B - Open Debt Clustering And Entry Gate Ranking

- Task ID: `M9-0B`
- Phase: `M9 Phase 0 - Post-M8 Rebaseline And Scope Freeze`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9-0A`

## Goal

- Cluster the open debt set into candidate `M9` themes.
- Rank those themes by dependency order, blast radius, and validation readiness.

## Out Of Scope

- retiring debt items
- implementing the ranked themes
- rewriting the debt registry itself

## Read Set

- `docs/tech-debt-registry.md`
- `docs/governance/tech_debt_registry.json`
- `docs/governance/review_policy_cases.json`
- `packages/core_domain/governance.py`
- `tests/test_governance.py`
- relevant `M8` review documents

## Write Set

- Allowed:
  - `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`
  - `docs/task_cards/m9_phase_0_task_cards.md`
- Avoid:
  - debt retirement claims
  - code changes
  - future phase implementation details

## Interfaces And Data Changes

- documentation only
- add an explicit candidate-theme matrix and frozen ordering rationale

## Invariants

- preserve the six-item carry-over debt set as the input
- do not silently demote `TD-001` or `TD-009` just because they are higher blast radius
- keep ranking criteria anchored in repository reality rather than ambition

## Implementation Steps

1. Re-read the open debt set against the `M9-0A` baseline.
2. Group debts into a small number of candidate themes.
3. Rank themes by safety, sequencing, and validation readiness.
4. Record the ordered result in the phase doc and index.

## Test Plan

- documentation audit
- consistency check between `docs/tech-debt-registry.md`, governance JSON, and the phase doc

## Risks And Rollback

- Main risk: turning the ranking into an implicit milestone closeout.
- Roll back by restoring the phase doc to candidate-only language until `M9-0C` freezes scope.

## Completion Evidence

- Actual modified files:
  - `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`
  - `docs/task_cards/m9_phase_0_task_cards.md`
- Validation:
  - documentation audit completed
- Implementation note:
  - Theme A (`TD-007` + `TD-008` + `TD-010`) was ranked first, Theme B (`TD-006`) second, and Theme C (`TD-001` + `TD-009`) deferred
