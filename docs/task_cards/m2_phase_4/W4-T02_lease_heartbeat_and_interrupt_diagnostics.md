# W4-T02 - Lease Heartbeat And Interrupt Diagnostics

## Basic Info

- Task ID: `W4-T02`
- Phase: `M2 Phase 4`
- Status: `completed`
- Depends On: `W4-T01`

## Goal

Integrate worker-lease lifecycle and heartbeat-aware diagnostics into runtime execution without overstating the current synchronous model.

## Read Set

- `packages/core_domain/services.py`
- `packages/contracts/events.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Write Set

- `packages/core_domain/services.py`
- `packages/contracts/events.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Invariants

- worker leases must not outlive local execution paths silently
- heartbeat semantics must stay explicit and current-model aligned
- interrupt-safety diagnostics must stay operator-facing and bounded

## Implementation Steps

1. Create a worker lease at runtime start and release it at terminal / review-handoff / cancel boundaries.
2. Add worker-lease diagnostics and repairability metadata where appropriate.
3. Project worker-lease state through status / inspection.
4. Add service, API, and CLI tests for lease lifecycle and expiry diagnostics.

## Test Plan

- lease creation / release tests
- expiry diagnostic tests
- operator projection tests
- API / CLI regression tests

## Outcome

- worker leases are now created at runtime start and released explicitly at review-handoff, terminal, and cancel boundaries
- `status-detail` / `inspection` now project `latest_worker_lease`, `active_worker_leases`, and `worker_lease_projection`
- reconcile supports bounded `release_worker_lease` and `expire_worker_lease` actions without changing the current synchronous execution model
- targeted regression closed with `pytest tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q` -> `88 passed`
