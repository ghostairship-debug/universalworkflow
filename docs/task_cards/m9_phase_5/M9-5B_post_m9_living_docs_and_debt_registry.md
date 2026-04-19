# M9-5B - Post-M9 Living Docs And Debt Registry

- Task ID: `M9-5B`
- Phase: `M9 Phase 5 - Freeze Review And Scope Closure`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9-5A`

## Goal

- Update living docs and debt registry entries to post-`M9` truth.
- Rescope deferred debt explicitly to `M10`.

## Out Of Scope

- running final verification commands
- changing delivered `M9` scope
- opening `M10` work

## Read Set

- `docs/reviews/m9-freeze-review.md`
- `README.md`
- `docs/current_development_workflow.md`
- `docs/tech-debt-registry.md`
- `docs/governance/tech_debt_registry.json`
- `infra/validation/doc_hygiene.py`

## Write Set

- Allowed:
  - `README.md`
  - `docs/current_development_workflow.md`
  - `docs/tech-debt-registry.md`
  - `docs/governance/tech_debt_registry.json`
  - `infra/validation/doc_hygiene.py`
  - `docs/task_cards/m9_phase_5_task_cards.md`
- Avoid:
  - runtime code
  - old historical review docs except where explicitly needed

## Interfaces And Data Changes

- living docs must point to `M9` as the completed milestone
- debt registry must retire `TD-006`, `TD-007`, `TD-008`, and `TD-010`
- deferred items `TD-001` and `TD-009` must be marked for `M10`
- living-doc hygiene must check `m9-freeze-review.md` instead of `m8-freeze-review.md`

## Invariants

- current-state docs must stay aligned with the controlling freeze review
- historical docs remain historical and should not be rewritten to erase earlier truth

## Implementation Steps

1. Update README and current workflow guide to post-`M9` truth.
2. Update technical-debt registry markdown and JSON.
3. Align living-doc hygiene with the new controlling closeout record.

## Test Plan

- `python -m infra.scripts.check_doc_links`
- later `python -m infra.scripts.offline_validation --skip-offline-probe`

## Risks And Rollback

- Main risk: current-state docs and debt registry drift apart.
- Roll back by treating `docs/reviews/m9-freeze-review.md` as the single source for closeout truth and propagating from there.

## Completion Evidence

- Actual modified files:
  - `README.md`
  - `docs/current_development_workflow.md`
  - `docs/tech-debt-registry.md`
  - `docs/governance/tech_debt_registry.json`
  - `infra/validation/doc_hygiene.py`
  - `docs/task_cards/m9_phase_5_task_cards.md`
- Validation:
  - `python -m infra.scripts.check_doc_links` passed
  - later `python -m infra.scripts.offline_validation --skip-offline-probe` passed
- Implementation note:
  - the living-doc hygiene target was corrected to `m9-freeze-review.md` during closeout hardening
