# B3-T02 - Budget Accounting And Enforcement

## Basic Info

- Task ID: `B3-T02`
- Phase: `M2 Phase 3`
- Status: `completed`
- Depends On: `B3-T01`

## Goal

Integrate budget accounting into lifecycle boundaries and expose bounded enforcement decisions through operator diagnostics.

## Read Set

- `packages/core_domain/services.py`
- `packages/core_domain/errors.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Write Set

- `packages/core_domain/services.py`
- `packages/core_domain/errors.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Invariants

- accounting stays tied to explicit lifecycle events
- enforcement must return stable structured errors
- projections remain operator-facing and deterministic

## Implementation Steps

1. Create or refresh the ledger at compile / recompile boundaries.
2. Record execution consumption after runtime completion.
3. Expose remaining retry / timeout headroom through `status-detail` and `inspection`.
4. Add one bounded enforcement rule with service, API, and CLI tests.

## Test Plan

- compile / recompile ledger tests
- execution consumption tests
- over-budget enforcement tests
- operator projection tests

## Completion Note

Completed with compile/recompile/execution ledger accounting, operator-facing budget projections, and stable `budget_exhausted` enforcement for bounded recompile retries.
