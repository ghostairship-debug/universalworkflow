# M9-1C - Docs, Reviews, And Phase Closeout

- Task ID: `M9-1C`
- Phase: `M9 Phase 1 - Replay Linkage And Metrics Baseline`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9-1A`, `M9-1B`

## Goal

- Record the replay/metrics baseline in the `M9` planning pack and later milestone closeout materials.
- Keep phase-level scope and deliverables explicit.

## Out Of Scope

- new feature work
- debt retirement
- separate hosted docs site work

## Read Set

- `m9_phase_docs/phase_1_replay_linkage_and_metrics_baseline.md`
- `docs/task_cards/m9_phase_1_task_cards.md`
- `README.md`
- later `docs/reviews/m9-freeze-review.md`

## Write Set

- Allowed:
  - `m9_phase_docs/phase_1_replay_linkage_and_metrics_baseline.md`
  - `docs/task_cards/m9_phase_1_task_cards.md`
  - `README.md` if phase-level wording needs it
  - later `docs/reviews/m9-freeze-review.md`
- Avoid:
  - runtime code
  - debt registry closeout

## Interfaces And Data Changes

- documentation only
- the phase pack must say replay packet plus run metrics are in scope and completed

## Invariants

- phase closeout text must match actual delivered operator surfaces
- do not overclaim durable or governance work before later phases land

## Implementation Steps

1. Keep the phase doc and phase index aligned with the frozen scope.
2. Update later closeout materials to mention replay packet and first-class run metrics.
3. Leave debt retirement and current-state living docs to later cards.

## Test Plan

- documentation audit
- later `python -m infra.scripts.check_doc_links`

## Risks And Rollback

- Main risk: phase-closeout wording claims more than the implementation delivered.
- Roll back by scoping documentation to replay/metrics only and leaving later topics untouched.

## Completion Evidence

- Actual modified files:
  - `m9_phase_docs/phase_1_replay_linkage_and_metrics_baseline.md`
  - `docs/task_cards/m9_phase_1_task_cards.md`
  - later `README.md`
  - later `docs/reviews/m9-freeze-review.md`
- Validation:
  - documentation audit completed
  - later `python -m infra.scripts.check_doc_links` passed
- Implementation note:
  - no standalone phase-1 review document was created; the phase closeout was consolidated into the milestone freeze review
