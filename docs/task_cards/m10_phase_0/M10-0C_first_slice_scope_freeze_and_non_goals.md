# M10-0C - First Slice Scope Freeze And Non-Goals

- Task ID: `M10-0C`
- Phase: `M10 Phase 0 - Post-M9 Rebaseline And Scope Freeze`
- Status: `completed`
- Depends On: `M10-0A`, `M10-0B`

## Goal

- Freeze the first approved feature-bearing `M10` slice.
- Record explicit early-`M10` non-goals and control-plane guardrails.

## Out Of Scope

- implementing ownership or barrier logic
- opening future `M10` task-card packs
- rewriting the persistence model or public contract

## Read Set

- `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`
- `docs/reviews/m9-freeze-review.md`
- `docs/adrs/ADR-005.md`
- `docs/adrs/ADR-M8-009.md`
- `README.md`

## Write Set

- Allowed:
  - `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`
  - `docs/task_cards/m10_phase_0_task_cards.md`
- Avoid:
  - runtime code
  - future phase task-card packs
  - living-doc milestone truth unrelated to the active phase

## Interfaces And Data Changes

- documentation only
- freeze:
  - the first approved `M10` slice
  - explicit deferred items
  - explicit early-`M10` non-goals

## Invariants

- preserve the repository as a local-first control plane
- do not weaken feature-flag promotion rules while planning `M10`
- do not let "ownership" or "concurrency" automatically expand into a hosted external scheduler rewrite

## Implementation Steps

1. Freeze one first feature-bearing `M10` slice based on `M10-0B`.
2. Record explicit non-goals for early `M10`.
3. State the next approved phase name only as a planning placeholder.
4. Reassert that future phase task-card packs stay unopened until active.

## Test Plan

- documentation audit
- later `python -m infra.scripts.check_doc_links`

## Risks And Rollback

- Main risk: the freeze wording quietly approves too much scope.
- Roll back by trimming scope until only the first slice plus clear non-goals remain.

## Completion Evidence

- Actual modified files:
  - `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`
  - `docs/task_cards/m10_phase_0_task_cards.md`
  - `docs/reviews/m10-phase-0-post-m9-rebaseline-and-scope-freeze-review.md`
- Final first-slice decision:
  - `M10 Phase 1 - Ownership Topology And Claim Domain Freeze`
- Final non-goal list:
  - do not open `M10` with barrier/join or parallel-attempt semantics before ownership topology is frozen
  - do not auto-approve true external worker-pool or multi-node scheduler breadth
  - do not promote `M8` experimental lanes to default paths as part of early `M10`
  - do not reframe `M10` as a generic multi-agent role-system rewrite
