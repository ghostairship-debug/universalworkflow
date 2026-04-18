# P4-T03 - Docs, Validation, And Closeout

## Basic Info

- Task ID: `P4-T03`
- Phase: `M3 Phase 4`
- Status: `completed`
- Depends On: `P4-T01`, `P4-T02`

## Goal

Make review-policy governance part of standard acceptance and document the current expansion boundary clearly.

## Read Set

- `README.md`
- `docs/reviews/`
- `docs/tech-debt-registry.md`
- `infra/scripts/offline_validation.py`
- `m3_phase_docs/phase_4_review_policy_governance_and_expansion_baseline.md`

## Write Set

- `README.md`
- `docs/reviews/`
- `docs/tech-debt-registry.md`
- `infra/scripts/offline_validation.py`
- `m3_phase_docs/phase_4_review_policy_governance_and_expansion_baseline.md`
- `docs/task_cards/m3_phase_4_task_cards.md`

## Invariants

- docs must be honest that richer policies are still reference-only
- validation should touch governance surfaces without simulating unsupported runtime policies

## Implementation Steps

1. Document the governance review-policy command / route.
2. Extend offline validation to query the new governance report through CLI and API.
3. Update the decision table and debt registry notes to reflect the new governance baseline.
4. Run full verification and close the phase.

## Test Plan

- full `pytest`
- offline validation dry run if practical

## Outcome

- README and offline validation now include the review-policy governance surface.
- `TD-006` notes now reflect the structured governance / decision-table baseline.
- Verified with `pytest -q` and `python -m infra.scripts.offline_validation --skip-offline-probe`.
