# M9-2C - Docs, Reviews, And Phase Closeout

- Task ID: `M9-2C`
- Phase: `M9 Phase 2 - Durable Recovery Lineage And Reconciliation`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9-2A`, `M9-2B`

## Goal

- Record the durable hardening result in the phase pack and later milestone closeout.

## Out Of Scope

- governance automation
- policy-breadth documentation
- debt retirement ahead of milestone closeout

## Read Set

- `m9_phase_docs/phase_2_durable_recovery_lineage_and_reconciliation.md`
- `docs/task_cards/m9_phase_2_task_cards.md`
- `README.md`
- later `docs/reviews/m9-freeze-review.md`

## Write Set

- Allowed:
  - `m9_phase_docs/phase_2_durable_recovery_lineage_and_reconciliation.md`
  - `docs/task_cards/m9_phase_2_task_cards.md`
  - `README.md` if durable wording needs updating
  - later `docs/reviews/m9-freeze-review.md`
- Avoid:
  - debt registry closeout
  - governance docs outside durable scope

## Interfaces And Data Changes

- documentation only
- phase closeout must say durable runs now persist inspectable lineage and transition-aware reconciliation signals

## Invariants

- documentation must keep the durable lane opt-in
- do not imply durable pilot promotion

## Implementation Steps

1. Keep the phase doc and index aligned with the actual durable scope.
2. Add durable-lineage wording to later milestone closeout materials.
3. Leave cross-phase debt retirement to Phase 5.

## Test Plan

- documentation audit
- later `python -m infra.scripts.check_doc_links`

## Risks And Rollback

- Main risk: docs imply durable behavior is now the default runtime lane.
- Roll back by explicitly labeling the durable lane as pilot and opt-in in every closeout note.

## Completion Evidence

- Actual modified files:
  - `m9_phase_docs/phase_2_durable_recovery_lineage_and_reconciliation.md`
  - `docs/task_cards/m9_phase_2_task_cards.md`
  - later `README.md`
  - later `docs/reviews/m9-freeze-review.md`
- Validation:
  - documentation audit completed
  - later `python -m infra.scripts.check_doc_links` passed
- Implementation note:
  - like Phase 1, the durable phase closeout was consolidated into the final milestone freeze review
