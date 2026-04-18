# C1-T03 - Claim Surfaces, Docs, And Verification

## Basic Info

- Task ID: `C1-T03`
- Phase: `M2 Phase 1`
- Status: `completed`
- Depends On: `C1-T01`, `C1-T02`

## Goal

Close the phase by exposing claim visibility through operator surfaces, updating docs, and running full verification.

## Read Set

- `README.md`
- `infra/scripts/offline_validation.py`
- `m2_phase_docs/phase_1_local_claim_lifecycle_and_lease_guard.md`
- `docs/task_cards/m2_phase_1_task_cards.md`
- `tests/`

## Write Set

- `README.md`
- `infra/scripts/offline_validation.py`
- `m2_phase_docs/phase_1_local_claim_lifecycle_and_lease_guard.md`
- `docs/task_cards/m2_phase_1_task_cards.md`
- `tests/`

## Invariants

- docs describe local claim semantics accurately
- verification covers claim visibility plus stale-claim repair

## Implementation Steps

1. Expose claim query surfaces in CLI/API.
2. Update README with claim-aware status / reconcile usage.
3. Extend validation to cover claim acquisition and release behavior.
4. Backfill phase gate status after full verification.

## Test Plan

- full `pytest`
- offline validation dry run if practical

## Completion Note

Completed with `run claims` / `GET /runs/{run_id}/claims`, claim-aware README and validation coverage, `81 passed`, and `offline_validation --skip-offline-probe` returning `overall_passed=true`.
