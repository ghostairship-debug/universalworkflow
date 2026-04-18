# P5-T01 - Adapter Base, NoopAdapter, And WorkerRouter

## Basic Info

- Task ID: `P5-T01`
- Phase: `M1.5`
- Status: `completed`
- Depends On: `M1.5 entry`

## Goal

Turn the second executor from a contract-only idea into a real runtime boundary by extracting shared adapter primitives, creating `NoopAdapter`, and routing through a dedicated `WorkerRouter`.

## Read Set

- `packages/worker_adapters/shell_adapter.py`
- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`

## Write Set

- `packages/worker_adapters/base.py`
- `packages/worker_adapters/noop_adapter.py`
- `packages/worker_adapters/router.py`
- `packages/worker_adapters/shell_adapter.py`
- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`

## Interface / Data Changes

- shared `ExecutionResult` / `WorkerAdapter` moves out of `shell_adapter.py`
- new `NoopAdapter`
- new `WorkerRouter`
- `ShellAdapter` only advertises `shell_exec`

## Invariants

- no fallback back to project-kernel semantics
- routing remains deterministic
- shell path stays backward-compatible

## Implementation Steps

1. Move shared adapter primitives into a dedicated base module.
2. Implement `NoopAdapter` as a real adapter that can emit deterministic artifact output.
3. Implement `WorkerRouter` that selects by capability/task kind and fails fast when unsupported.
4. Switch service execution to the router without changing external behavior yet.

## Test Plan

- shell path still passes
- noop path uses `NoopAdapter`
- unsupported task kind fails explicitly

## Outcome

- shared adapter primitives now live in `packages/worker_adapters/base.py`
- `NoopAdapter` and `WorkerRouter` are live runtime components
- execution routing no longer depends on `ShellAdapter` silently handling `noop`
