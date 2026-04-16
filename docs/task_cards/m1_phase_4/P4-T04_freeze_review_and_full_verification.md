# P4-T04 — Freeze Review And Full Verification

## Basic Info

- Task ID: `P4-T04`
- Phase: `M1 Phase 4`
- Status: `verified`
- Depends On: `P4-T01`, `P4-T02`, `P4-T03`

## Goal

完成 M1 freeze review、全量测试和最终 closeout，并把结论落到正式文档。

## Read Set

- `pyproject.toml`
- `tests/`
- `docs/reviews/m0-freeze-review.md`
- `docs/tech-debt-registry.md`
- `docs/task_cards/m1_phase_4_task_cards.md`

## Write Set

- `pyproject.toml`
- `docs/reviews/m1-freeze-review.md`
- `docs/task_cards/m1_phase_4_task_cards.md`

## Implementation Steps

1. 补齐 `pytest` 配置，清掉测试期的已知弃用噪音。
2. 运行 full `pytest`。
3. 运行 M1 smoke。
4. 运行 offline validation 的联机 dry run。
5. 根据结果形成 `docs/reviews/m1-freeze-review.md`，并更新 `Phase 4` gate 结论。

## Test Plan

- `pytest`
- `python -m infra.scripts.manage --db-path state/m1_smoke.db smoke`
- `python -m infra.scripts.offline_validation --report-path state/offline_validation_m1_dry_run.json --skip-offline-probe`

## Verification Result

- Outcome:
  - `pytest` 全量 `37 passed`
  - `M1 smoke` 通过
  - offline validation dry run `overall_passed = true`
  - `docs/reviews/m1-freeze-review.md` 已形成正式结论
- Verified by:
  - `pytest`
  - `python -m infra.scripts.manage --db-path state/m1_smoke.db smoke`
  - `python -m infra.scripts.offline_validation --report-path state/offline_validation_m1_dry_run.json --skip-offline-probe`
