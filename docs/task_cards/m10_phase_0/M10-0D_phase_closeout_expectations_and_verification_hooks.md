# M10-0D - Phase Closeout Expectations And Verification Hooks

- Task ID: `M10-0D`
- Phase: `M10 Phase 0 - Post-M9 Rebaseline And Scope Freeze`
- Status: `completed`
- Depends On: `M10-0C`

## Goal

- Make current-phase closeout duties, verification hooks, and task-card timing rules explicit before feature-bearing `M10` work begins.

## Out Of Scope

- changing the frozen `M10` scope
- implementing ownership or concurrency code
- generating any future phase task-card pack

## Read Set

- `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`
- `docs/task_cards/m10_phase_0_task_cards.md`
- `docs/task_cards/m1_execution_loop_protocol.md`
- `docs/documentation_governance.md`

## Write Set

- Allowed:
  - `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`
  - `docs/task_cards/m10_phase_0_task_cards.md`
- Avoid:
  - runtime code
  - future phase files

## Interfaces And Data Changes

- documentation only
- define:
  - current-phase closeout expectations
  - link-check expectations
  - the "current phase only" task-card-pack rule

## Invariants

- there should be only one active phase task-card pack at a time
- future phase names may appear in the phase doc, but their task cards stay unopened
- closeout and verification rules must stay explicit

## Implementation Steps

1. Add current-phase closeout expectations to the index.
2. Reassert verification hooks and task-pack timing rules.
3. Confirm the phase pack is execution-ready without pre-generating `M10 Phase 1`.

## Test Plan

- `python -m infra.scripts.check_doc_links`

## Risks And Rollback

- Main risk: future phase task packs get opened too early again.
- Roll back by restating the current-phase-only rule directly in the active phase pack.

## Completion Evidence

- Actual modified files:
  - `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`
  - `docs/task_cards/m10_phase_0_task_cards.md`
  - `docs/reviews/m10-phase-0-post-m9-rebaseline-and-scope-freeze-review.md`
  - `README.md`
  - `docs/current_development_workflow.md`
- `check_doc_links` result:
  - `passed=true`
- Timing-rule clarifications added during closeout:
  - `M10 Phase 0` is closed
  - the next approved work is `M10 Phase 1 - Ownership Topology And Claim Domain Freeze`
  - no future `M10` task-card pack was generated during this closeout
