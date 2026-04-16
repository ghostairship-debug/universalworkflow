# P1-T01 — Contracts And Runtime Interface Delta

## Basic Info

- Task ID: `P1-T01`
- Phase: `M1 Phase 1`
- Status: `verified`
- Depends On: `Phase 0 gate`

## Goal

把 Phase 0 冻结的状态机与 runtime interface 增量正式落进 contracts 层。

## Read Set

- `packages/contracts/models.py`
- `packages/contracts/events.py`
- `packages/contracts/__init__.py`
- `packages/runtime_langgraph/gateway.py`
- `tests/test_contracts.py`
- `tests/test_runtime_boundary.py`

## Write Set

- `packages/contracts/models.py`
- `packages/contracts/events.py`
- `packages/contracts/__init__.py`
- 新增 `packages/contracts/runtime.py`
- `packages/runtime_langgraph/gateway.py`
- `tests/test_contracts.py`
- `tests/test_runtime_boundary.py`

## Tests

- contracts round-trip
- event payload validation
- runtime boundary import test

## Output

- `awaiting_review`
- `PresetSuggestion`
- `RuntimeStateRef`
- contracts-owned `RuntimeGateway`
