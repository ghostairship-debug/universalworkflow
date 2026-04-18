# B3-T01 - Budget Ledger Contract, Migration, And Repository

## Basic Info

- Task ID: `B3-T01`
- Phase: `M2 Phase 3`
- Status: `completed`
- Depends On: `Phase 3 entry`

## Goal

Create the persisted `BudgetLedger` baseline that later service accounting and operator projections can rely on.

## Read Set

- `packages/contracts/models.py`
- `packages/core_domain/repositories.py`
- `infra/migrations/`
- `tests/test_contracts.py`
- `tests/test_repositories.py`

## Write Set

- `packages/contracts/*`
- `packages/core_domain/repositories.py`
- `infra/migrations/*`
- `tests/test_contracts.py`
- `tests/test_repositories.py`

## Invariants

- budget semantics stay local and deterministic
- repository methods must preserve auditable state
- migration must be additive

## Implementation Steps

1. Add budget-ledger model.
2. Add a migration for persisted budget ledgers.
3. Add repository methods for create, get, and update.
4. Add contract and repository tests.

## Test Plan

- budget-ledger round-trip
- update / projection repository tests
- migration coverage

## Completion Note

Completed with the `BudgetLedger` contract, migration `005_m2_budget_ledgers.sql`, repository create/get/update surfaces, and passing contract/repository tests.
