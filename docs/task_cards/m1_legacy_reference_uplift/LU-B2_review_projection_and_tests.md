# LU-B2 — Review Projection And Tests

## Basic Info

- Task ID: `LU-B2`
- Phase: `M1 Legacy Uplift / Phase B`
- Status: `ready`
- Depends On: `LU-B1`

## Goal

增加 `latest_review_verdict / effective_review_state` 的查询与测试投影。

## Read Set

- `packages/core_domain/services.py`
- `apps/orchestrator_api/main.py`
- `apps/operator_cli/main.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Write Set

- `packages/core_domain/services.py`
- `apps/orchestrator_api/main.py`
- `apps/operator_cli/main.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Invariants

- 只补查询与投影，不把 review 模型扩成遗产 gate 系统
- `status-detail` 输出必须稳定、可读

## Test Plan

- latest verdict 查询
- effective review state 投影
- CLI / API 输出一致性
