# LU-A1 — State Transition Matrix

## Basic Info

- Task ID: `LU-A1`
- Phase: `M1 Legacy Uplift / Phase A`
- Status: `ready`
- Depends On: none

## Goal

冻结当前仓库版本的 `RunStatus / RuntimeStateRef` 迁移矩阵与 terminal 规则。

## Non-goals

- 不引入遗产 `Project` 顶层模型
- 不引入 phase/task-card runtime 主链

## Read Set

- `packages/contracts/models.py`
- `packages/contracts/runtime.py`
- `packages/core_domain/services.py`
- `D:\AI Agent\src\agentic_kernel\domain\project.py`
- `D:\AI Agent\src\agentic_kernel\domain\task_state.py`

## Write Set

- `docs/m1_legacy_reference_uplift_plan.md`
- `packages/contracts/models.py`
- `packages/contracts/runtime.py`
- `tests/test_contracts.py`

## Interface / Data Changes

- 显式定义 `RunStatus` 允许迁移集合
- 明确 `RuntimeStateRef` 的 terminal / non-terminal 规则

## Invariants

- 仍保持当前 `run-centric` 模型
- 不为兼容遗产命名而扭曲当前 contract

## Implementation Steps

1. 抽取当前实际使用的 `RunStatus` 与 `RuntimeStateRef.graph_step`。
2. 参考遗产状态机，只提炼合法迁移与 terminal 分类，不提炼其 project 命名。
3. 形成当前仓库版本的迁移矩阵。
4. 补 contracts tests，验证 terminal 规则与非法跳转集合。

## Test Plan

- 状态枚举 round-trip
- terminal / non-terminal 分类测试
- 迁移矩阵表驱动断言

## Completion Evidence

- 迁移矩阵成文
- tests 覆盖新增状态守卫边界
