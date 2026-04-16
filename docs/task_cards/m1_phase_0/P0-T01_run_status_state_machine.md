# P0-T01 — Run Status State Machine

## Basic Info

- Task ID: `P0-T01`
- Phase: `M1 Phase 0`
- Status: `verified`
- Depends On: `None`

## Goal

冻结 M1 的 `RunStatus` 增量、合法状态转换矩阵、关键动作与需要配套新增的 event。

## Non-goals

- 不在本卡中直接改代码
- 不讨论 M2 的并发、pause、rollback、replay、fork

## Read Set

- `packages/contracts/models.py`
- `packages/contracts/events.py`
- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`
- `M0_Evaluation_Claude_Opus.md`

## Write Set

- `m1_phase_docs/phase_0_rebaseline_and_scope_freeze.md`
- 本文件
- 后续 Phase 1 / Phase 3 的 contract、service、test 文件

## Interface / Data Changes

- `RunStatus` 新增 `awaiting_review`
- 保留 `prepared`，不新增 `compiled`
- `review_requested` 为 event，不为 run status
- 建议新增 event：
  - `run_compiled`
  - `runtime_resumed`
  - `handoff_created`
  - `review_requested`
  - `run_cancelled`

## Invariants

- 状态总数保持最小
- `resume` 是动作，不是状态
- `human_required` 只引入一个新增挂起状态

## Implementation Steps

1. 以 `pending / prepared / running / awaiting_review / completed / failed / cancelled` 作为唯一 M1 run status 集合。
2. 为每个 public action 定义 from/to 关系：
   `compile`、`recompile`、`resume`、`approve`、`reject`、`cancel`。
3. 标记每个状态转换需要写入的 timeline event。
4. 将该矩阵回填到 phase 文档。
5. 在 Phase 1 中按该矩阵调整 contracts / tests，在 Phase 3 中按该矩阵实现状态守卫。

## Test Plan

- Phase 1：contract round-trip + event schema test
- Phase 3：非法状态转换测试
- Phase 4：human review 路径测试

## Risks / Rollback

- 风险：状态过多导致实现复杂度膨胀
- 回退：优先删状态，不优先新增状态

## Completion Evidence

- 状态矩阵已进入 `phase_0_rebaseline_and_scope_freeze.md`
- 后续 Phase 1 / Phase 3 task cards 以此为前置输入
