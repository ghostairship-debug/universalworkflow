# M2 Phase 4 Task Cards

## Reassessment

- `M2 Phase 3` completed the budget-ledger baseline and bounded budget enforcement.
- The next gap is that worker ownership and heartbeat semantics are still implicit even though claims, snapshots, and budgets are now explicit.
- This phase therefore introduces a lightweight `WorkerLease` baseline before any stronger interrupt-safety or scheduling work is attempted.

Phase outcome:

- `W4-T01`, `W4-T02`, and `W4-T03` are completed.
- worker leases are now persisted, projected through `status-detail / inspection`, and queryable through CLI/API.
- Verification closed with `115 passed` plus `offline_validation --skip-offline-probe` returning `overall_passed=true`.

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `W4-T01` | `complex` | Add the `WorkerLease` contract, persistence migration, repository methods, and query surfaces | `Phase 4 entry` | `packages/contracts/runtime.py`, `packages/core_domain/repositories.py`, `infra/migrations/`, `tests/test_contracts.py`, `tests/test_repositories.py` | `packages/contracts/*`, `packages/core_domain/repositories.py`, `infra/migrations/*`, `tests/test_contracts.py`, `tests/test_repositories.py` | contract + repository tests | persisted worker-lease baseline |
| `W4-T02` | `complex` | Integrate worker-lease creation, release, expiry diagnostics, and interrupt-safety projections into services | `W4-T01` | `packages/core_domain/services.py`, `packages/contracts/events.py`, `tests/test_execution_loop.py` | `packages/core_domain/services.py`, `packages/contracts/events.py`, `tests/test_execution_loop.py`, `tests/test_api.py`, `tests/test_cli.py` | service + API + CLI tests | worker-lease lifecycle |
| `W4-T03` | `complex` | Expose worker-lease surfaces through CLI/API, update docs/validation, and run full verification | `W4-T01`, `W4-T02` | `README.md`, `infra/scripts/offline_validation.py`, `m2_phase_docs/phase_4_worker_lease_heartbeat_and_interrupt_safety.md`, `tests/` | docs + validation + surfaces | full `pytest` | phase closeout |

## Gate Checklist

- worker leases are persisted and auditable
- runtime execution creates and releases worker leases consistently
- inspection exposes expired or wrongly-live worker leases
- claim and worker-lease projections remain comprehensible together
- shell and noop execution paths remain green

Implementation status:

- `W4-T01`: completed, including `WorkerLease` contract, migration, repository, and query baseline
- `W4-T02`: completed, including lifecycle integration, expiry diagnostics, repair actions, and operator projections
- `W4-T03`: completed, including CLI/API lease surfaces, README and validation updates, full `pytest`, and offline validation

Gate result:

- Passed for all checklist items
