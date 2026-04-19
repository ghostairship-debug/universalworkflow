# M10-1A - Ownership Contract And Persistence Freeze

- Task ID: `M10-1A`
- Phase: `M10 Phase 1 - Ownership Topology And Claim Domain Freeze`
- Status: `completed`
- Depends On: `Phase entry`

## Goal

- Add explicit ownership-topology fields to `RuntimeClaim` and `WorkerLease`.
- Persist those fields in SQLite and repository mapping code.

## Out Of Scope

- lifecycle wiring
- CLI/API surface work
- barrier or parallel semantics

## Read Set

- `packages/contracts/runtime.py`
- `packages/contracts/events.py`
- `packages/core_domain/repositories.py`
- `infra/migrations/003_m2_runtime_claims.sql`
- `infra/migrations/006_m2_worker_leases.sql`
- `tests/test_contracts.py`
- `tests/test_repositories.py`

## Write Set

- Allowed:
  - `packages/contracts/runtime.py`
  - `packages/contracts/events.py`
  - `packages/core_domain/repositories.py`
  - `infra/migrations/*`
  - `tests/test_contracts.py`
  - `tests/test_repositories.py`
  - active phase docs

## Invariants

- preserve current claim/lease lifecycle validation
- keep the new fields additive and explicit
- do not claim distributed scheduling support yet

## Test Plan

- `python -m pytest tests/test_contracts.py tests/test_repositories.py -q`

## Completion Evidence

- Actual modified files:
  - `packages/contracts/runtime.py`
  - `packages/contracts/events.py`
  - `packages/contracts/__init__.py`
  - `packages/core_domain/repositories.py`
  - `infra/migrations/010_m10_ownership_topology.sql`
  - `tests/test_contracts.py`
  - `tests/test_repositories.py`
- Validation result:
  - `python -m pytest tests/test_contracts.py tests/test_repositories.py -q` -> `34 passed`
