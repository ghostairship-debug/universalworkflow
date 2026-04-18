# M2 Phase 3 Task Cards

## Reassessment

- `M2 Phase 2` completed the replay-friendly snapshot baseline.
- The next gap is that budget policy still exists only as preset metadata, not as persisted runtime accounting.
- This phase therefore introduces a lightweight `BudgetLedger` baseline before worker-lease heartbeat or richer scheduling work is attempted.

Phase outcome:

- `B3-T01`, `B3-T02`, and `B3-T03` are completed.
- Verification closed with `102 passed` plus `offline_validation --skip-offline-probe` returning `overall_passed=true`.
- The next recommended phase is `M2 Phase 4 - Worker Lease Heartbeat And Interrupt Safety`.

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `B3-T01` | `complex` | Add the `BudgetLedger` contract, persistence migration, repository methods, and query surfaces | `Phase 3 entry` | `packages/contracts/models.py`, `packages/core_domain/repositories.py`, `infra/migrations/`, `tests/test_contracts.py`, `tests/test_repositories.py` | `packages/contracts/*`, `packages/core_domain/repositories.py`, `infra/migrations/*`, `tests/test_contracts.py`, `tests/test_repositories.py` | contract + repository tests | persisted budget ledger baseline |
| `B3-T02` | `complex` | Integrate budget accounting and bounded enforcement into service flows and operator projections | `B3-T01` | `packages/core_domain/services.py`, `packages/core_domain/errors.py`, `tests/test_execution_loop.py` | `packages/core_domain/services.py`, `packages/core_domain/errors.py`, `tests/test_execution_loop.py`, `tests/test_api.py`, `tests/test_cli.py` | service + API + CLI tests | budget-aware lifecycle |
| `B3-T03` | `complex` | Expose budget surfaces through CLI/API, update docs/validation, and run full verification | `B3-T01`, `B3-T02` | `README.md`, `infra/scripts/offline_validation.py`, `m2_phase_docs/phase_3_budget_ledger_baseline_and_enforcement_projections.md`, `tests/` | docs + validation + surfaces | full `pytest` | phase closeout |

## Gate Checklist

- budget ledgers are persisted and auditable
- compile / recompile / execution update ledger consumption consistently
- status / inspection expose remaining budget headroom
- enforcement stays explicit and bounded
- shell and noop execution paths remain green

Implementation status:

- `B3-T01`: completed, including the budget-ledger contract, migration, repository methods, and repository tests
- `B3-T02`: completed, including lifecycle accounting hooks, operator projections, and bounded retry-budget enforcement
- `B3-T03`: completed, including CLI/API budget query surfaces, README and validation updates, full `pytest`, and offline validation

Gate result:

- Passed for all checklist items
