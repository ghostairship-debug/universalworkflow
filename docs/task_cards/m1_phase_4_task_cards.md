# M1 Phase 4 Task Cards

## Reassessment

- `Phase 3` 结束后，M1 的 compile / recompile / resume / handoff / status-detail 主链已经稳定。
- `Phase 4` 不再新增新的基础架构方向，而是把 `human_required` 从冻结语义推进到真实 operator loop。
- 本阶段必须同时完成三件事：人审闭环、M1 验收工具链、freeze review 收口。

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P4-T01` | `complex` | 在 service 层打通 `human_required` 的 `awaiting_review -> approve/reject -> terminal` 闭环 | `Phase 3 gate` | `packages/core_domain/services.py`, `tests/test_execution_loop.py` | `packages/core_domain/services.py`, `tests/test_execution_loop.py` | execution loop tests | policy-aware review runtime |
| `P4-T02` | `complex` | 暴露 approve / reject API 与 CLI，并补齐 operator DX | `P4-T01` | `apps/orchestrator_api/main.py`, `apps/operator_cli/main.py`, `tests/test_api.py`, `tests/test_cli.py` | same | API + CLI tests | operator review surface |
| `P4-T03` | `complex` | 升级 smoke、offline validation、README 到 M1 实际能力 | `P4-T01`, `P4-T02` | `infra/scripts/manage.py`, `infra/scripts/offline_validation.py`, `README.md`, `docs/smoke/` | same | smoke + validation dry run | M1 acceptance tooling |
| `P4-T04` | `complex` | 完成 full verification、freeze review 与阶段关门 | `P4-T01`, `P4-T02`, `P4-T03` | `pyproject.toml`, `tests/`, `docs/reviews/`, `docs/tech-debt-registry.md` | same | full `pytest` + smoke + validation dry run | M1 closeout |

## Gate Checklist

- `research_spike` 在 `resume` 后进入 `awaiting_review`
- `approve / reject` 能把 run 推进到 terminal
- `README`、`smoke`、`offline validation` 都切换到 M1 口径
- 全量 `pytest` 通过
- `infra/scripts/manage.py ... smoke` 通过
- `infra/scripts/offline_validation.py --skip-offline-probe` dry run 通过
- `docs/reviews/m1-freeze-review.md` 给出明确结论

## Gate Review Result

- Decision: `pass`
- Verified on: `2026-04-16`
- Evidence:
  - `pytest` -> `37 passed`
  - `python -m infra.scripts.manage --db-path state/m1_smoke.db smoke` -> `status = completed`
  - `python -m infra.scripts.offline_validation --report-path state/offline_validation_m1_dry_run.json --skip-offline-probe` -> `overall_passed = true`
- Residual note:
  - 本轮完成的是联机环境 dry run；物理断网后的 `offline_probe` 仍需在需要时由操作者实际执行，但代码路径与 M0 已验证探测逻辑保持一致。
