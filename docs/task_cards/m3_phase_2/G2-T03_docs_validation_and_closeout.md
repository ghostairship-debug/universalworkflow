# G2-T03 - Docs, Validation, And Closeout

## Basic Info

- Task ID: `G2-T03`
- Phase: `M3 Phase 2`
- Status: `completed`
- Depends On: `G2-T01`, `G2-T02`

## Goal

Make the governance report part of standard acceptance and phase review so debt visibility becomes a normal project checkpoint rather than a manual afterthought.

## Read Set

- `README.md`
- `infra/scripts/offline_validation.py`
- `docs/reviews/`
- `docs/tech-debt-registry.md`
- `m3_phase_docs/phase_2_governance_projection_and_tech_debt_visibility_baseline.md`

## Write Set

- `README.md`
- `infra/scripts/offline_validation.py`
- `docs/reviews/`
- `docs/tech-debt-registry.md`
- `m3_phase_docs/phase_2_governance_projection_and_tech_debt_visibility_baseline.md`
- `docs/task_cards/m3_phase_2_task_cards.md`

## Invariants

- acceptance should validate governance visibility without introducing a dashboard dependency
- review materials should describe what governance visibility now exists and what still remains manual

## Implementation Steps

1. Document the governance command / route in README.
2. Extend offline validation so CLI/API governance visibility is checked alongside runtime acceptance.
3. Update review materials and the debt registry note for `TD-010`.
4. Run full verification and close the phase.

## Test Plan

- full `pytest`
- offline validation dry run if practical

## Outcome

- README and offline validation now treat governance visibility as part of standard acceptance.
- `TD-010` notes now reflect the structured governance-report baseline instead of markdown-only tracking.
- Verified with `pytest -q` and `python -m infra.scripts.offline_validation --skip-offline-probe`.
