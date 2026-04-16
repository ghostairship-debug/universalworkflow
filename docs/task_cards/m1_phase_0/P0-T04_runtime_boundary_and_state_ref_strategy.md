# P0-T04 — Runtime Boundary And State Ref Strategy

## Basic Info

- Task ID: `P0-T04`
- Phase: `M1 Phase 0`
- Status: `verified`
- Depends On: `P0-T01`

## Goal

冻结 M1 中 runtime “真实主链”的边界，明确 `RuntimeGateway` 的接口归属与 `RuntimeStateRef` 的持久化策略。

## Non-goals

- 不在 M1 接真实 LangGraph 图
- 不为 M1 引入 `langgraph` 依赖

## Read Set

- `packages/runtime_langgraph/gateway.py`
- `packages/core_domain/services.py`
- `tests/test_runtime_boundary.py`
- `M1_Evaluation_and_Suggestions.md`
- `M0_Evaluation_Claude_Opus.md`

## Write Set

- `m1_phase_docs/phase_0_rebaseline_and_scope_freeze.md`
- 本文件
- 后续 Phase 1 / Phase 3 的 contracts、runtime impl、tests

## Interface / Data Changes

- `RuntimeGateway` ABC 移入 `packages/contracts/`
- `RuntimeStateRef` 成为可持久化 contract
- 新增 `runtime_state_refs` 持久化表
- status-detail / handoff 查询需要能看到当前 state ref

## Invariants

- `contracts/` 和 `core_domain/` 仍不得直接 import `langgraph`
- state ref 中只存 ID、枚举、轻量 payload
- M1 的 runtime 主链用纯 Python 表达恢复点

## Implementation Steps

1. 将 `RuntimeGateway` 和 `RuntimeStateRef` 视为 contract，而不是 runtime 实现细节。
2. 规定 `NullRuntimeGateway` 继续作为默认实现，但其 `start/resume` 返回的 state ref 会真正落库。
3. 规定 M1 的 `resume_run()` 读取并更新持久化 state ref。
4. 规定 M1 不新增 `langgraph` 依赖，相关真实集成留到 M1.5 / M2。

## Test Plan

- AST 规则继续保证 `contracts/`、`core_domain/` 无 `langgraph` import
- state ref round-trip 测试
- resume 前后 `graph_step` 更新测试

## Risks / Rollback

- 风险：runtime 边界重新向 `core_domain -> runtime` 倒挂
- 回退：接口必须始终停留在 `contracts/`

## Completion Evidence

- phase 文档已冻结纯 Python runtime 策略
- Phase 1 / 3 可据此实现 state ref 落库和 resume 主链
