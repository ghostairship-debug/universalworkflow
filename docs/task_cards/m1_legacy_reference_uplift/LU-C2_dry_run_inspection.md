# LU-C2 — Dry Run Inspection

## Basic Info

- Task ID: `LU-C2`
- Phase: `M1 Legacy Uplift / Phase C`
- Status: `ready`
- Depends On: `LU-C1`

## Goal

新增 4 类坏状态的 dry-run inspection，只诊断、不修改真实状态。

## Target Cases

- `completed` 但 runtime 非 terminal
- `awaiting_review` 但缺 evidence
- `cancelled` 但仍有 live runtime
- `prepared` 但 compile snapshot 不完整

## Read Set

- `packages/core_domain/services.py`
- `infra/scripts/offline_validation.py`
- `tests/test_execution_loop.py`
- `D:\AI Agent\src\agentic_kernel\services\runtime_reconcile_service.py`
- `D:\AI Agent\tests\services\test_phase_task_card_runtime.py`

## Write Set

- diagnostics / inspection 入口
- `infra/scripts/offline_validation.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`

## Invariants

- inspection 不得修改数据库状态
- inspection 输出必须明确指出问题类型与建议动作

## Test Plan

- 4 类坏状态识别测试
- dry-run 无副作用测试
- 输出包含 problem / reason / next_action
