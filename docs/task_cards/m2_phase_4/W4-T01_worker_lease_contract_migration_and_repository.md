# W4-T01 - Worker Lease Contract, Migration, And Repository

## Basic Info

- Task ID: `W4-T01`
- Phase: `M2 Phase 4`
- Status: `ready`
- Depends On: `Phase 4 entry`

## Goal

Create the persisted `WorkerLease` baseline that later service heartbeat and interrupt-safety logic can rely on.

## Read Set

- `packages/contracts/runtime.py`
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

- worker-lease semantics stay local-only
- repository methods must preserve auditable lease history
- migration must be additive

## Implementation Steps

1. Add worker-lease enums / model.
2. Add a migration for persisted worker leases.
3. Add repository methods for create, release, active lookup, and per-run listing.
4. Add contract and repository tests.

## Test Plan

- worker-lease round-trip
- active-lease query tests
- release repository tests
