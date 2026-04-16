# P4-T01 — Human Review Service Loop

## Basic Info

- Task ID: `P4-T01`
- Phase: `M1 Phase 4`
- Status: `verified`
- Depends On: `Phase 3 gate`

## Goal

让 `human_required` preset 走通 `resume -> awaiting_review -> approve/reject -> terminal` 真闭环，并且不破坏 `auto_only` 现有路径。

## Read Set

- `packages/core_domain/services.py`
- `packages/contracts/models.py`
- `packages/contracts/events.py`
- `tests/test_execution_loop.py`

## Write Set

- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`

## Contract / Behavior Constraints

- `resume_run()` 在 `human_required` 下不得创建 auto `ReviewVerdict`
- `human_required` 路径必须写入 `review_requested`
- run 必须进入 `awaiting_review`
- approve / reject 必须都生成 `ReviewerType.human` 的 `ReviewVerdict`
- terminal 之后 `RuntimeStateRef.is_terminal` 必须为 `true`

## Implementation Steps

1. 在 `resume_run()` 中根据 `preset.default_review_policy` 分叉 `auto_only` 与 `human_required`。
2. `human_required` 分支只落 evidence，不做 auto review，并把 run/status/state 推到 `awaiting_review`。
3. 新增 `approve_run_review()` / `reject_run_review()`，复用统一的 `_finalize_human_review()`。
4. 在人工审核完成时更新 `RuntimeStateRef`、`Run.status` 和 terminal event。

## Test Plan

- `tests/test_execution_loop.py::test_human_required_path_waits_for_manual_review`
- `tests/test_execution_loop.py::test_resume_run_updates_terminal_runtime_state`

## Verification Result

- Outcome:
  - `human_required` 路径现在会在 `resume` 后进入 `awaiting_review`
  - approve 会把 run 推到 `completed`
  - reject 会把 run 推到 `failed`
- Verified by:
  - `pytest tests/test_execution_loop.py`
