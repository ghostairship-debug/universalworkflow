# P5-T02 - Task-Kind Override And Service Routing

## Basic Info

- Task ID: `P5-T02`
- Phase: `M1.5`
- Status: `completed`
- Depends On: `P5-T01`

## Goal

Allow compile-time selection of an allowed task kind, validate it against the preset, and carry that choice through compile, recompile, and resume.

## Read Set

- `packages/core_domain/compile.py`
- `packages/core_domain/services.py`
- `packages/contracts/models.py`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`
- `tests/test_contracts.py`
- `tests/test_api.py`
- `tests/test_cli.py`
- `tests/test_execution_loop.py`

## Write Set

- `packages/core_domain/compile.py`
- `packages/core_domain/services.py`
- `packages/core_domain/errors.py`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`
- `tests/test_contracts.py`
- `tests/test_api.py`
- `tests/test_cli.py`
- `tests/test_execution_loop.py`

## Interface / Data Changes

- `compile_run()` / `recompile_run()` accept an optional task-kind override
- CLI compile/create surfaces may request `--task-kind`
- API compile/recompile surfaces may provide a task-kind body
- invalid preset/task-kind combinations return a stable error

## Invariants

- `POST /runs` stays create-only
- override can only pick from `allowed_task_kinds`
- no hidden inference for adapter selection

## Implementation Steps

1. Add task-kind validation against preset allow-lists.
2. Thread the selected task kind through compile snapshot creation.
3. Expose the override through service, CLI, and API.
4. Add shell-path and noop-path tests plus invalid-request tests.

## Test Plan

- compile with `noop` on `research_spike`
- reject `noop` on `feature_delivery`
- CLI and API noop happy path

## Outcome

- compile, recompile, and prepare can all take an explicit task-kind override
- preset allow-list validation now distinguishes unsupported kinds from disallowed ones
- CLI and API both expose the second executor path and stable error payloads
