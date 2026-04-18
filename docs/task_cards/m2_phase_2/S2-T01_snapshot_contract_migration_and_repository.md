# S2-T01 - Snapshot Contract, Migration, And Repository

## Basic Info

- Task ID: `S2-T01`
- Phase: `M2 Phase 2`
- Status: `completed`
- Depends On: `Phase 2 entry`

## Goal

Create the persisted `RunSnapshot` baseline that later service hooks and operator projections can rely on.

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

- snapshot semantics stay additive and non-authoritative
- repository methods must preserve history, not overwrite a singleton
- migration must be additive

## Implementation Steps

1. Add snapshot enum / model.
2. Add a migration for persisted run snapshots.
3. Add repository methods for create, latest lookup, and per-run listing.
4. Add contract and repository tests.

## Test Plan

- snapshot contract round-trip
- latest snapshot query tests
- per-run history tests

## Completion Note

Completed with the `RunSnapshot` contract, migration `004_m2_run_snapshots.sql`, repository query surfaces, and passing contract/repository tests.
