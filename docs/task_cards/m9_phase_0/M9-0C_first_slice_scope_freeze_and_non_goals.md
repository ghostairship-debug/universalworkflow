# M9-0C - First Slice Scope Freeze And Non-Goals

- Task ID: `M9-0C`
- Phase: `M9 Phase 0 - Post-M8 Rebaseline And Scope Freeze`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9-0A`, `M9-0B`

## Goal

- Freeze the first approved `M9` slice.
- Record explicit non-goals and pilot-promotion guardrails.
- Freeze the follow-on phase sequence used to execute `M9`.

## Out Of Scope

- implementing Theme A or Theme B
- promoting borrowed-agent, MCP, external trace, durable pilot, or skill export to defaults
- reopening distributed concurrency work

## Read Set

- `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`
- `docs/reviews/m8-freeze-review.md`
- `README.md`
- `m8_phase_docs/*`
- `packages/core_domain/m8_flags.py`
- `packages/core_domain/observability.py`
- `packages/runtime_langgraph/durable_pilot.py`

## Write Set

- Allowed:
  - `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`
  - `m9_phase_docs/phase_1_replay_linkage_and_metrics_baseline.md`
  - `m9_phase_docs/phase_2_durable_recovery_lineage_and_reconciliation.md`
  - `m9_phase_docs/phase_3_governance_metrics_and_alerting.md`
  - `m9_phase_docs/phase_4_optional_review_policy_completion.md`
  - `m9_phase_docs/phase_5_freeze_review_and_scope_closure.md`
  - `docs/task_cards/m9_phase_0_task_cards.md`
  - `docs/task_cards/m9_phase_1_task_cards.md`
  - `docs/task_cards/m9_phase_2_task_cards.md`
  - `docs/task_cards/m9_phase_3_task_cards.md`
  - `docs/task_cards/m9_phase_4_task_cards.md`
  - `docs/task_cards/m9_phase_5_task_cards.md`
- Avoid:
  - runtime code
  - debt registry closeout
  - default-lane promotion language

## Interfaces And Data Changes

- documentation only
- freeze the milestone to:
  - Phase 1: replay linkage and metrics
  - Phase 2: durable lineage and reconciliation
  - Phase 3: governance metrics and alerts
  - Phase 4: `optional` review-policy completion
  - Phase 5: freeze review and scope closure

## Invariants

- preserve the local-first canonical lane
- keep external or pilot lanes explicitly opt-in
- keep Theme C outside `M9`

## Implementation Steps

1. Freeze the approved `M9` theme ordering in the phase doc.
2. Write the five downstream phase docs with explicit in-scope/out-of-scope boundaries.
3. Generate the corresponding phase index files.
4. Record the explicit deferred set and non-goals.

## Test Plan

- documentation audit across the full `m9_phase_docs/` and `docs/task_cards/m9_phase_*` pack

## Risks And Rollback

- Main risk: broadening `M9` while writing its sequence.
- Roll back by removing any task or phase that reopens concurrency or default pilot promotion.

## Completion Evidence

- Actual modified files:
  - `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`
  - `m9_phase_docs/phase_1_replay_linkage_and_metrics_baseline.md`
  - `m9_phase_docs/phase_2_durable_recovery_lineage_and_reconciliation.md`
  - `m9_phase_docs/phase_3_governance_metrics_and_alerting.md`
  - `m9_phase_docs/phase_4_optional_review_policy_completion.md`
  - `m9_phase_docs/phase_5_freeze_review_and_scope_closure.md`
  - `docs/task_cards/m9_phase_0_task_cards.md`
  - `docs/task_cards/m9_phase_1_task_cards.md`
  - `docs/task_cards/m9_phase_2_task_cards.md`
  - `docs/task_cards/m9_phase_3_task_cards.md`
  - `docs/task_cards/m9_phase_4_task_cards.md`
  - `docs/task_cards/m9_phase_5_task_cards.md`
- Validation:
  - documentation audit completed
- Implementation note:
  - this card froze Theme A plus Theme B into `M9` and pushed Theme C to `M10`
