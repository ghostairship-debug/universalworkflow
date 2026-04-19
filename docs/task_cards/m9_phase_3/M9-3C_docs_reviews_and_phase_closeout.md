# M9-3C - Docs, Reviews, And Phase Closeout

- Task ID: `M9-3C`
- Phase: `M9 Phase 3 - Governance Metrics And Alerting`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9-3A`, `M9-3B`

## Goal

- Record the governance automation baseline in the phase pack and milestone closeout materials.

## Out Of Scope

- debt retirement before `M9` closeout
- external governance dashboards
- review-policy work

## Read Set

- `m9_phase_docs/phase_3_governance_metrics_and_alerting.md`
- `docs/task_cards/m9_phase_3_task_cards.md`
- `docs/tech-debt-registry.md`
- later `README.md`
- later `docs/reviews/m9-freeze-review.md`

## Write Set

- Allowed:
  - `m9_phase_docs/phase_3_governance_metrics_and_alerting.md`
  - `docs/task_cards/m9_phase_3_task_cards.md`
  - later `README.md`
  - later `docs/reviews/m9-freeze-review.md`
- Avoid:
  - debt registry status flips before Phase 5
  - runtime code

## Interfaces And Data Changes

- documentation only
- phase closeout must describe governance metrics, alerts, and release-readiness integration accurately

## Invariants

- documentation must keep governance automation local and repo-shaped
- do not claim debt retirement before it is recorded in Phase 5

## Implementation Steps

1. Keep the phase doc/index aligned with the shipped governance scope.
2. Feed the governance automation result into later milestone closeout language.
3. Leave debt-retirement wording for the final phase.

## Test Plan

- documentation audit
- later `python -m infra.scripts.check_doc_links`

## Risks And Rollback

- Main risk: docs imply broader automation than what CLI/API actually expose.
- Roll back by writing directly against the concrete `metrics`, `alerts`, and `release-readiness` surfaces.

## Completion Evidence

- Actual modified files:
  - `m9_phase_docs/phase_3_governance_metrics_and_alerting.md`
  - `docs/task_cards/m9_phase_3_task_cards.md`
  - later `README.md`
  - later `docs/reviews/m9-freeze-review.md`
- Validation:
  - documentation audit completed
  - later `python -m infra.scripts.check_doc_links` passed
- Implementation note:
  - milestone closeout absorbed the governance hardening result instead of adding a separate phase review
