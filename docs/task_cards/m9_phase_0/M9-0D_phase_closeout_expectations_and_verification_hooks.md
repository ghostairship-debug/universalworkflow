# M9-0D - Phase Closeout Expectations And Verification Hooks

- Task ID: `M9-0D`
- Phase: `M9 Phase 0 - Post-M8 Rebaseline And Scope Freeze`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9-0C`

## Goal

- Make closeout duties, living-doc touchpoints, and verification hooks explicit before feature work starts.
- Keep later `M9` closeout work anchored to a known checklist.

## Out Of Scope

- changing the frozen `M9` scope
- implementing feature work
- closing debts

## Read Set

- `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`
- `docs/task_cards/m9_phase_0_task_cards.md`
- `docs/current_development_workflow.md`
- `docs/documentation_governance.md`

## Write Set

- Allowed:
  - `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`
  - `docs/task_cards/m9_phase_0_task_cards.md`
- Avoid:
  - runtime code
  - debt registry updates
  - living-doc truth changes before milestone closeout

## Interfaces And Data Changes

- documentation only
- define:
  - later phase closeout expectations
  - link-check expectations
  - living-doc update rules

## Invariants

- keep the phase pack execution-ready
- do not let later closeout work become implicit tribal knowledge

## Implementation Steps

1. Add closeout expectations to the phase index.
2. Add verification hooks for doc-pack updates.
3. Confirm the later feature-bearing phases can execute without re-debating Phase 0.

## Test Plan

- `python -m infra.scripts.check_doc_links`

## Risks And Rollback

- Main risk: closeout requirements become too vague and later milestone truth drifts.
- Roll back by reducing this card to explicit verification and document-touch rules only.

## Completion Evidence

- Actual modified files:
  - `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`
  - `docs/task_cards/m9_phase_0_task_cards.md`
- Validation:
  - `python -m infra.scripts.check_doc_links` passed during milestone closeout
- Implementation note:
  - later M9 execution used these hooks to drive the final freeze review, living-doc updates, and verification baseline
