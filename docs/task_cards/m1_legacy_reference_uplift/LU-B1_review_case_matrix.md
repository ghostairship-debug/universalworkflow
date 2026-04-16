# LU-B1 — Review Case Matrix

## Basic Info

- Task ID: `LU-B1`
- Phase: `M1 Legacy Uplift / Phase B`
- Status: `ready`
- Depends On: `LU-A2`

## Goal

把遗产 review policy 的边界案例翻译成当前仓库版本的测试矩阵。

## Non-goals

- 不立即扩 `ReviewPolicy` 枚举
- 不引入遗产 gate 存储模型

## Read Set

- `packages/contracts/models.py`
- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`
- `D:\AI Agent\src\agentic_kernel\services\review_service.py`
- `D:\AI Agent\tests\services\test_review_policy_routing.py`

## Write Set

- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`
- 补充 review semantics 说明文档

## Interface / Data Changes

- 明确当前 `auto_only / human_required` 的 case matrix
- 为 future richer policy 预埋测试骨架

## Implementation Steps

1. 提炼遗产 review policy case，而不是照搬 gate 模型。
2. 翻译为当前 run-centric 语义。
3. 先落测试，后看是否需要扩实现。

## Test Plan

- auto path
- human pending
- human approved
- human rejected
- 错误时序下的 review path
