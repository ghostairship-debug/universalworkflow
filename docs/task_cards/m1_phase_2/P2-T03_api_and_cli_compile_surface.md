# P2-T03 — API And CLI Compile Surface

## Basic Info

- Task ID: `P2-T03`
- Phase: `M1 Phase 2`
- Status: `verified`
- Depends On: `P2-T02`

## Goal

把 suggestion / compile / recompile / status-detail / handoffs 暴露给 operator，同时保持 `POST /runs` 边界不变。

## Read Set

- `apps/orchestrator_api/main.py`
- `apps/operator_cli/main.py`
- `README.md`
- `tests/test_api.py`
- `tests/test_cli.py`

## Write Set

- `apps/orchestrator_api/main.py`
- `apps/operator_cli/main.py`
- `README.md`
- `tests/test_api.py`
- `tests/test_cli.py`

## Tests

- create run still returns `pending`
- compile / recompile API
- compile / recompile CLI
- status-detail / handoffs CLI/API

## Output

- operator-visible compile surface
