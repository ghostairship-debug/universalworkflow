# P2-T02 — Compile Service And Status Detail

## Basic Info

- Task ID: `P2-T02`
- Phase: `M1 Phase 2`
- Status: `verified`
- Depends On: `P2-T01`

## Goal

把 compile 从内部 prepare 升级为公开服务能力，并让 run 的 compile 结果可查询。

## Read Set

- `packages/core_domain/compile.py`
- `packages/core_domain/services.py`
- `packages/core_domain/repositories.py`
- `packages/runtime_langgraph/gateway.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Write Set

- `packages/core_domain/compile.py`
- `packages/core_domain/services.py`
- `packages/core_domain/repositories.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Tests

- compile -> prepared
- recompile only on prepared
- status-detail includes handoffs / runtime state refs / next action

## Output

- compile / recompile service
- status-detail query
- handoffs query
