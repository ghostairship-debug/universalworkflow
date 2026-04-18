# S1-T03 - Docs, Validation, And Closeout

## Basic Info

- Task ID: `S1-T03`
- Phase: `M3 Phase 1`
- Status: `completed`
- Depends On: `S1-T01`, `S1-T02`

## Goal

Make the richer event-inspection / closure-discipline baseline part of normal operator acceptance and phase review.

## Read Set

- `README.md`
- `docs/reviews/`
- `docs/tech-debt-registry.md`
- `infra/scripts/offline_validation.py`
- `m3_phase_docs/phase_1_event_inspection_and_review_closure_discipline.md`

## Write Set

- `README.md`
- `docs/reviews/`
- `docs/tech-debt-registry.md`
- `infra/scripts/offline_validation.py`
- `m3_phase_docs/phase_1_event_inspection_and_review_closure_discipline.md`
- `docs/task_cards/m3_phase_1_task_cards.md`

## Invariants

- docs must describe the real operator flow
- validation must exercise the new closure-audit surface
- review materials should explain what changed and what is still intentionally out of scope

## Implementation Steps

1. Document the new event-inspection command / route and intended operator usage.
2. Extend offline validation to touch closure-audit state for auto and human-review flows.
3. Update review materials and technical-debt notes to reflect the stronger M3 governance baseline.
4. Run full verification and close the phase.

## Test Plan

- full `pytest`
- offline validation dry run if practical

## Outcome

- README, offline validation, and review materials now include event inspection and closure audit as standard acceptance surfaces.
- `TD-007` and `TD-010` notes now reflect the stronger event-inspection / governance baseline.
- Verified with `pytest -q` and `python -m infra.scripts.offline_validation --skip-offline-probe`.
