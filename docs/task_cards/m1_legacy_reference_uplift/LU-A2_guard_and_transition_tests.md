# LU-A2 — Guard And Transition Tests

## Basic Info

- Task ID: `LU-A2`
- Phase: `M1 Legacy Uplift / Phase A`
- Status: `ready`
- Depends On: `LU-A1`

## Goal

把显式迁移矩阵落实到 service guard、API 错误与执行链测试。

## Read Set

- `packages/core_domain/services.py`
- `apps/orchestrator_api/main.py`
- `tests/test_api.py`
- `tests/test_execution_loop.py`
- `docs/task_cards/m1_legacy_reference_uplift/LU-A1_state_transition_matrix.md`

## Write Set

- `packages/core_domain/services.py`
- `apps/orchestrator_api/main.py`
- `tests/test_api.py`
- `tests/test_execution_loop.py`

## Interface / Data Changes

- 非法状态迁移动作的错误响应稳定化
- API / service guard 覆盖 compile / resume / execute / cancel / human review

## Invariants

- 状态守卫先于副作用执行
- 错误响应不泄露实现细节

## Implementation Steps

1. 为关键动作绑定 allowed statuses。
2. 在 service 层统一抛出非法迁移错误。
3. 在 API 层补对应该错误的回归断言。
4. 在 execution tests 中补非法跳转回归。

## Test Plan

- API 409 / 4xx 错误测试
- execution loop 非法顺序测试
- cancel / resume / review 边界测试
