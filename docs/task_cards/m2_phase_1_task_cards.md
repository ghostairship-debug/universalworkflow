# M2 Phase 1 Task Cards

## Reassessment

- `M2 Phase 0` completed the minimal repair loop.
- The next gap is that runtime actions are still protected only by run status, not by explicit claim / lease state.
- This phase therefore introduces a local claim lifecycle before any stronger concurrency semantics are attempted.

Phase outcome:

- `C1-T01`, `C1-T02`, and `C1-T03` are completed.
- Verification closed with `81 passed` plus `offline_validation --skip-offline-probe` returning `overall_passed=true`.
- The next recommended phase is `M2 Phase 2 - Run Snapshot Baseline And Recovery Projections`.

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `C1-T01` | `complex` | Add the local runtime claim contract, persistence migration, repository methods, and query surfaces | `Phase 1 entry` | `packages/contracts/runtime.py`, `packages/core_domain/repositories.py`, `infra/migrations/`, `tests/test_contracts.py`, `tests/test_repositories.py` | `packages/contracts/*`, `packages/core_domain/repositories.py`, `infra/migrations/*`, `tests/test_contracts.py`, `tests/test_repositories.py` | contract + repository tests | persisted claim baseline |
| `C1-T02` | `complex` | Integrate claim acquire / release / stale handling into services and reconcile logic | `C1-T01` | `packages/core_domain/services.py`, `packages/core_domain/errors.py`, `packages/contracts/events.py`, `tests/test_execution_loop.py` | `packages/core_domain/services.py`, `packages/core_domain/errors.py`, `packages/contracts/events.py`, `tests/test_execution_loop.py`, `tests/test_api.py`, `tests/test_cli.py` | service + API + CLI tests | local lease guard |
| `C1-T03` | `complex` | Expose claim surfaces through CLI/API, update docs/validation, and run full verification | `C1-T01`, `C1-T02` | `README.md`, `infra/scripts/offline_validation.py`, `m2_phase_docs/phase_1_local_claim_lifecycle_and_lease_guard.md`, `tests/` | docs + validation + surfaces | full `pytest` | phase closeout |

## Gate Checklist

- runtime claims are persisted and auditable
- inspection / reconcile understand stale or wrongly-live claims
- shell and noop execution paths remain green
- claim semantics remain local and do not pretend to be distributed coordination

Implementation status:

- `C1-T01`: completed, including the claim contract, migration, repository methods, and repository tests
- `C1-T02`: completed, including acquire / release semantics, claim-aware inspection / reconcile logic, and conflict coverage
- `C1-T03`: completed, including CLI/API claim query surfaces, README and validation updates, full `pytest`, and offline validation

Gate result:

- Passed for all checklist items
