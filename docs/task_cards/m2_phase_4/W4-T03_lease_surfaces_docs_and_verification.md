# W4-T03 - Lease Surfaces, Docs, And Verification

## Basic Info

- Task ID: `W4-T03`
- Phase: `M2 Phase 4`
- Status: `completed`
- Depends On: `W4-T01`, `W4-T02`

## Goal

Close the phase by exposing worker-lease visibility through operator surfaces, updating docs, and running full verification.

## Read Set

- `README.md`
- `infra/scripts/offline_validation.py`
- `m2_phase_docs/phase_4_worker_lease_heartbeat_and_interrupt_safety.md`
- `docs/task_cards/m2_phase_4_task_cards.md`
- `tests/`

## Write Set

- `README.md`
- `infra/scripts/offline_validation.py`
- `m2_phase_docs/phase_4_worker_lease_heartbeat_and_interrupt_safety.md`
- `docs/task_cards/m2_phase_4_task_cards.md`
- `tests/`

## Invariants

- docs describe worker-lease semantics accurately
- verification covers worker-lease visibility plus expiry diagnostics

## Implementation Steps

1. Expose worker-lease query surfaces in CLI/API.
2. Update README with lease-aware status / inspect usage.
3. Extend validation to cover worker-lease capture and diagnostics.
4. Backfill phase gate status after full verification.

## Test Plan

- full `pytest`
- offline validation dry run if practical

## Outcome

- CLI now exposes `run leases <run_id>` and API now exposes `GET /runs/{id}/leases`
- README, smoke, and offline validation now describe and verify worker-lease visibility and event capture
- full verification closed with `pytest -q` -> `115 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe` returned `overall_passed=true`
