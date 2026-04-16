# LU-C1 — Status Detail Diagnostics

## Basic Info

- Task ID: `LU-C1`
- Phase: `M1 Legacy Uplift / Phase C`
- Status: `ready`
- Depends On: `LU-B2`

## Goal

增强 `status-detail` 与 operator diagnostics，让它更适合排障。

## Read Set

- `packages/core_domain/services.py`
- `apps/orchestrator_api/main.py`
- `apps/operator_cli/main.py`
- `infra/scripts/offline_validation.py`
- 遗产 deep dive / runtime tests

## Write Set

- `packages/core_domain/services.py`
- `apps/orchestrator_api/main.py`
- `apps/operator_cli/main.py`
- `infra/scripts/offline_validation.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## Interface / Data Changes

- `status-detail` 增加：
  - `failure_reason`
  - `waiting_reason`
  - `next_action`
  - `last_runtime_state`
  - `last_review_verdict`
  - `recoverability_hint`

## Test Plan

- API status-detail 字段测试
- CLI diagnostics 输出测试
- offline validation 字段校验
