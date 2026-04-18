# A3-T03 - Docs, Validation, And Closeout

## Basic Info

- Task ID: `A3-T03`
- Phase: `M3 Phase 3`
- Status: `completed`
- Depends On: `A3-T01`, `A3-T02`

## Goal

Make the audit bundle part of normal acceptance so review and handoff workflows have a stable, documented export shape.

## Read Set

- `README.md`
- `infra/scripts/offline_validation.py`
- `docs/reviews/`
- `docs/tech-debt-registry.md`
- `m3_phase_docs/phase_3_run_audit_report_and_review_packet_baseline.md`

## Write Set

- `README.md`
- `infra/scripts/offline_validation.py`
- `docs/reviews/`
- `docs/tech-debt-registry.md`
- `m3_phase_docs/phase_3_run_audit_report_and_review_packet_baseline.md`
- `docs/task_cards/m3_phase_3_task_cards.md`

## Invariants

- audit-report should improve packaging, not duplicate or fork semantics
- validation should touch the audit bundle without exploding acceptance complexity

## Implementation Steps

1. Document the audit-report command / route in README.
2. Extend offline validation to query the audit bundle on CLI/API paths.
3. Update review materials and debt notes to reflect the stronger audit packaging baseline.
4. Run full verification and close the phase.

## Test Plan

- full `pytest`
- offline validation dry run if practical

## Outcome

- README and offline validation now include audit-report as a standard acceptance surface.
- Debt notes now reflect the stronger run-level audit packaging baseline.
- Verified with `pytest -q` and `python -m infra.scripts.offline_validation --skip-offline-probe`.
