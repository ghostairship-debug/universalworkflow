# C1-T01 - Claim Contract, Migration, And Repository

## Basic Info

- Task ID: `C1-T01`
- Phase: `M2 Phase 1`
- Status: `completed`
- Depends On: `Phase 1 entry`

## Goal

Create the persisted local runtime claim baseline that later service logic can rely on.

## Read Set

- `packages/contracts/runtime.py`
- `packages/core_domain/repositories.py`
- `infra/migrations/`
- `tests/test_contracts.py`
- `tests/test_repositories.py`

## Write Set

- `packages/contracts/runtime.py`
- `packages/contracts/__init__.py`
- `packages/core_domain/repositories.py`
- `infra/migrations/*.sql`
- `tests/test_contracts.py`
- `tests/test_repositories.py`

## Invariants

- claim semantics stay local-only
- repository methods must support audit history, not just a mutable singleton
- migration must be additive

## Implementation Steps

1. Add runtime claim enums / model.
2. Add a migration for persisted runtime claims and active-claim uniqueness.
3. Add repository methods for create, release, expire, active lookup, and per-run listing.
4. Add contract and repository tests.

## Test Plan

- claim contract round-trip
- active-claim query tests
- release / expire repository tests

## Completion Note

Completed with the `RuntimeClaim` contract, migration `003_m2_runtime_claims.sql`, repository query/release surfaces, and passing contract/repository tests.
