# M10-2A - Local Batch Barrier Runtime Semantics

- Task ID: `M10-2A`
- Phase: `M10 Phase 2 - Local Barrier And Parallel Batch Execution`
- Status: `completed`
- Depends On: `Phase entry`

## Goal

- Add one repository-owned local batch barrier for multiple prepared runs.
- Keep batch concurrency grounded in the current local-first control plane.

## Out Of Scope

- distributed locking
- multi-node worker pools
- generic branch/join DAG execution

## Read Set

- `packages/contracts/events.py`
- `packages/core_domain/errors.py`
- `packages/core_domain/services.py`
- `packages/core_domain/service_lifecycle.py`
- `tests/test_execution_loop.py`

## Write Set

- Allowed:
  - runtime semantics and event/error files above
  - focused execution-loop tests
  - active phase docs

## Invariants

- keep ownership topology coherent under the batch path
- keep the barrier local-first and prepared-run scoped
- do not hold SQLite write locks across the synchronization point

## Test Plan

- `python -m pytest tests/test_execution_loop.py -q -k "batch or parallel or barrier"`

## Completion Evidence

- Actual modified files:
  - `packages/contracts/events.py`
  - `packages/core_domain/errors.py`
  - `packages/core_domain/services.py`
  - `packages/core_domain/service_lifecycle.py`
  - `tests/test_execution_loop.py`
- Key behavior delivered:
  - `resume_runs_parallel(...)`
  - local `batch_barrier_waiting` / `batch_barrier_released` events
  - `parallel_barrier_broken` structured error path
  - transaction shortening around the barrier to avoid SQLite lock amplification
