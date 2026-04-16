# P4-T03 — Smoke, Offline Validation And README

## Basic Info

- Task ID: `P4-T03`
- Phase: `M1 Phase 4`
- Status: `verified`
- Depends On: `P4-T01`, `P4-T02`

## Goal

把 smoke、offline validation 和 README 升级到 M1 实际能力口径，确保验收工具链覆盖 auto path 与 human-review path。

## Read Set

- `infra/scripts/manage.py`
- `infra/scripts/offline_validation.py`
- `README.md`
- `docs/smoke/m0-smoke.md`

## Write Set

- `infra/scripts/manage.py`
- `infra/scripts/offline_validation.py`
- `README.md`
- `docs/smoke/m1-smoke.md`

## Implementation Steps

1. 升级 `manage.py smoke`，让它同时验证 auto path 和 human-review path。
2. 升级 `offline_validation.py`，覆盖 CLI / API 的 compile、resume、approve、handoffs、status-detail。
3. README 切换到 M1 命令面，补充 human-review path 的手动路径说明。
4. 新增 `docs/smoke/m1-smoke.md`，明确定义预期 timeline 和人工 spot checks。

## Test Plan

- `python -m infra.scripts.manage --db-path state/m1_smoke.db smoke`
- `python -m infra.scripts.offline_validation --report-path state/offline_validation_m1_dry_run.json --skip-offline-probe`

## Verification Result

- Outcome:
  - smoke 已同时覆盖 auto 与 human-review path
  - offline validation dry run 的 CLI / smoke / API 三条链路全部通过
  - README 已切换到 M1 生命周期说明
- Verified by:
  - `python -m infra.scripts.manage --db-path state/m1_smoke.db smoke`
  - `python -m infra.scripts.offline_validation --report-path state/offline_validation_m1_dry_run.json --skip-offline-probe`
