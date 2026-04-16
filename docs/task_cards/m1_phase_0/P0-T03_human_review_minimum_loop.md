# P0-T03 — Human Review Minimum Loop

## Basic Info

- Task ID: `P0-T03`
- Phase: `M1 Phase 0`
- Status: `verified`
- Depends On: `P0-T01`

## Goal

冻结 `human_required` preset 在 M1 的最小闭环：何时挂起、如何 approve/reject、产生什么 verdict、落到什么终态。

## Non-goals

- 不实现 review timeout
- 不实现 reviewer queue / assignment / notification

## Read Set

- `packages/contracts/models.py`
- `packages/core_domain/auto_review.py`
- `packages/core_domain/services.py`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Write Set

- `m1_phase_docs/phase_0_rebaseline_and_scope_freeze.md`
- 本文件
- 后续 Phase 4 的 service / API / CLI / tests

## Interface / Data Changes

- `RunStatus.awaiting_review`
- CLI：
  - `workflowctl run approve <run_id>`
  - `workflowctl run reject <run_id>`
- API：
  - `POST /runs/{run_id}/approve`
  - `POST /runs/{run_id}/reject`
- event：
  - `review_requested`
  - `review_submitted`

## Invariants

- `human_required` 路径不走 auto review
- approve / reject 必须产出 `ReviewVerdict(reviewer_type=human)`
- `awaiting_review` 可无限挂起

## Implementation Steps

1. evidence 生成后检查 preset review policy。
2. 若为 `auto_only`，继续沿用 auto review。
3. 若为 `human_required`，run 状态转 `awaiting_review`，写 `review_requested` event。
4. `approve` / `reject` 分别写 human verdict，并把 run 送到 `completed` / `failed`。
5. 在 Phase 4 中为 CLI / API 增加人工决策路径。

## Test Plan

- `research_spike` 路径运行后进入 `awaiting_review`
- approve 后 `status=completed`
- reject 后 `status=failed`
- 非 `awaiting_review` 状态下 approve / reject 应报错

## Risks / Rollback

- 风险：把 human review 做成第二套复杂状态机
- 回退：只保留 `awaiting_review` 一个挂起状态

## Completion Evidence

- phase 文档中已冻结 `human_required` 最小闭环
- Phase 4 可以直接基于此卡编写 API / CLI / tests
