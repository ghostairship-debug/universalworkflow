# P4-T02 — Approve / Reject API And CLI

## Basic Info

- Task ID: `P4-T02`
- Phase: `M1 Phase 4`
- Status: `verified`
- Depends On: `P4-T01`

## Goal

把人工审核闭环暴露给 operator surface，使 API 和 CLI 都能显式执行 approve / reject。

## Read Set

- `apps/orchestrator_api/main.py`
- `apps/operator_cli/main.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Write Set

- `apps/orchestrator_api/main.py`
- `apps/operator_cli/main.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Interface Changes

- API:
  - `POST /runs/{run_id}/approve`
  - `POST /runs/{run_id}/reject`
- CLI:
  - `workflowctl run approve <run_id>`
  - `workflowctl run reject <run_id>`
  - `workflowctl run create --prepare --execute` 在 `human_required` 下返回 `awaiting_review`，而不是崩溃

## Implementation Steps

1. 在 API 层新增 approve / reject route，并返回统一 JSON payload。
2. 在 CLI 层新增 approve / reject 命令。
3. 修复 `run create --prepare --execute` 的输出一致性，确保返回最新 run 状态和 `review_decision=None`。
4. 增加 human review 的 API / CLI 测试。

## Test Plan

- `tests/test_api.py::test_api_human_review_path_requires_approval`
- `tests/test_api.py::test_api_human_review_reject_fails_run`
- `tests/test_cli.py::test_cli_run_create_with_human_required_returns_awaiting_review`
- `tests/test_cli.py::test_cli_human_review_approve_and_reject_paths`

## Verification Result

- Outcome:
  - API 与 CLI 均支持 approve / reject
  - CLI `create --prepare --execute` 对 `research_spike` 返回 `awaiting_review`
- Verified by:
  - `pytest tests/test_api.py tests/test_cli.py`
