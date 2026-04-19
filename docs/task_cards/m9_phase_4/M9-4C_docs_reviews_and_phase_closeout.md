# M9-4C - Docs, Reviews, And Phase Closeout

- Task ID: `M9-4C`
- Phase: `M9 Phase 4 - Optional Review Policy Completion`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9-4A`, `M9-4B`

## Goal

- Record the closure of the `optional` policy gap in the phase pack and later milestone closeout materials.

## Out Of Scope

- debt retirement before Phase 5
- broader review-policy replanning
- new runtime work

## Read Set

- `m9_phase_docs/phase_4_optional_review_policy_completion.md`
- `docs/task_cards/m9_phase_4_task_cards.md`
- `docs/governance/review_policy_cases.json`
- later `README.md`
- later `docs/reviews/m9-freeze-review.md`

## Write Set

- Allowed:
  - `m9_phase_docs/phase_4_optional_review_policy_completion.md`
  - `docs/task_cards/m9_phase_4_task_cards.md`
  - later `README.md`
  - later `docs/reviews/m9-freeze-review.md`
- Avoid:
  - debt registry files before closeout
  - lifecycle code

## Interfaces And Data Changes

- documentation only
- closeout wording must say `optional` is executable and advisory-only, not reference-only

## Invariants

- preserve clear semantic differences among all five policies
- do not overclaim debt retirement before Phase 5

## Implementation Steps

1. Keep the phase doc/index aligned with the actual optional-policy scope.
2. Feed the result into later milestone closeout language.
3. Leave debt registry changes to the freeze-closeout phase.

## Test Plan

- documentation audit
- later `python -m infra.scripts.check_doc_links`

## Risks And Rollback

- Main risk: documentation mixes old reference-only language with new executable language.
- Roll back by scanning governance/docs surfaces for stale wording before freeze closeout.

## Completion Evidence

- Actual modified files:
  - `m9_phase_docs/phase_4_optional_review_policy_completion.md`
  - `docs/task_cards/m9_phase_4_task_cards.md`
  - later `README.md`
  - later `docs/reviews/m9-freeze-review.md`
- Validation:
  - documentation audit completed
  - later `python -m infra.scripts.check_doc_links` passed
- Implementation note:
  - final current-state doc updates were intentionally deferred to Phase 5
