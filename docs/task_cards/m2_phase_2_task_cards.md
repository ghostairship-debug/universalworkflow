# M2 Phase 2 Task Cards

## Reassessment

- `M2 Phase 1` completed the local claim lifecycle and made claim state auditable.
- The next gap is not raw claim correctness anymore; it is the lack of replay-friendly checkpoints for recovery reasoning.
- This phase therefore introduces a lightweight `RunSnapshot` baseline before any deeper worker-lease or concurrency semantics are attempted.

Phase outcome:

- `S2-T01`, `S2-T02`, and `S2-T03` are completed.
- Verification closed with `91 passed` plus `offline_validation --skip-offline-probe` returning `overall_passed=true`.
- The next recommended phase is `M2 Phase 3 - Budget Ledger Baseline And Enforcement Projections`.

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `S2-T01` | `complex` | Add the `RunSnapshot` contract, persistence migration, repository methods, and query surfaces | `Phase 2 entry` | `packages/contracts/runtime.py`, `packages/core_domain/repositories.py`, `infra/migrations/`, `tests/test_contracts.py`, `tests/test_repositories.py` | `packages/contracts/*`, `packages/core_domain/repositories.py`, `infra/migrations/*`, `tests/test_contracts.py`, `tests/test_repositories.py` | contract + repository tests | persisted snapshot baseline |
| `S2-T02` | `complex` | Capture snapshots on key lifecycle and repair paths, and project them through operator diagnostics | `S2-T01` | `packages/core_domain/services.py`, `packages/contracts/events.py`, `tests/test_execution_loop.py` | `packages/core_domain/services.py`, `packages/contracts/events.py`, `tests/test_execution_loop.py`, `tests/test_api.py`, `tests/test_cli.py` | service + API + CLI tests | recovery projection baseline |
| `S2-T03` | `complex` | Expose snapshot surfaces through CLI/API, update docs/validation, and run full verification | `S2-T01`, `S2-T02` | `README.md`, `infra/scripts/offline_validation.py`, `m2_phase_docs/phase_2_run_snapshot_baseline_and_recovery_projections.md`, `tests/` | docs + validation + surfaces | full `pytest` | phase closeout |

## Gate Checklist

- run snapshots are persisted and auditable
- lifecycle and repair hooks capture snapshots consistently
- status / inspection expose the latest snapshot without bloating payloads
- shell and noop execution paths remain green
- snapshot semantics stay recovery-oriented and do not pretend to be full replay

Implementation status:

- `S2-T01`: completed, including the snapshot contract, migration, repository methods, and repository tests
- `S2-T02`: completed, including snapshot capture hooks plus latest-snapshot recovery projections in status / inspection
- `S2-T03`: completed, including CLI/API snapshot query surfaces, README and validation updates, full `pytest`, and offline validation

Gate result:

- Passed for all checklist items
