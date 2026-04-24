# 里程碑历史摘要

本文档合并了旧 phase docs、task cards、freeze reviews、archive、M2M 交接文档和根目录重复计划中的必要信息。它只提供历史摘要，不作为活跃执行计划。

## 1. 当前基线

- 日期：2026-04-24
- 最新接受基线：`M37`
- 当前状态：没有打开 post-`M37` bounded phase
- 当前产品前提：个人自用 / 本地 operator runtime
- 下一建议阶段：`M38 Phase 0`

## 2. 历史里程碑

| 阶段 | 摘要 | 当前结论 |
| --- | --- | --- |
| M20 | 达成深层 core-complete baseline，包含 scheduler-authority、remote worker、治理和 operator control 的关键基础 | 历史基线已吸收 |
| M25-M30 | 完成 policy control、operator packet、goal packet、dashboard/operator convergence 和 operator control freeze | 历史结论已吸收 |
| M31 | 做 boundary contraction 和 semantic honesty，确认后续需要继续收缩服务边界 | 主要遗留进入 `TD-STRUCT-*` |
| M32 | 吸收历史规划输入，建立 interaction / profile / cluster foundation | 历史结论已吸收 |
| M33 | 收缩 orchestration substrate，建立共享 orchestration service 和 canonical plan builder | `TD-STRUCT-004` 已偿还 |
| M34 | 继续 facade reduction 和 scheduler-authority interior cleanup | `TD-STRUCT-001`、`TD-STRUCT-003` 仍部分存在 |
| M35 | 建立 execution-profile contract、resolver precedence、config/read surfaces 和 execution explainability | 已接受 |
| M36 | 将 workbench preview 推进到 natural-language workbench v1，加入 follow-up queue 和 Web/CLI/API parity | 已接受 |
| M37 | 加入 governed generated profiles 和 bounded automation watchdog/controller | 已接受 |
| M2M 修复 | 完成根目录历史文档归档、scheduler-authority flag 双态兼容、默认 local-only 语义修正 | 结论已吸收，本轮清理移除旧交接计划 |

## 3. 已移除的历史材料

以下材料已经关闭，不再保留为活跃文件：

- `m21_phase_docs/` 到 `m37_phase_docs/`
- `docs/task_cards/`
- `docs/reviews/`
- `docs/archive/`
- `docs/m2m/`
- `M2M_REMEDIATION_PLAN.md`
- `NEXT_DEVELOPMENT_PLAN.md`
- `POST_M34_MULTIPHASE_ROADMAP.md`
- `README.zh-CN.md`

如需逐字审计旧材料，请使用 git 历史查看对应文件。

## 4. M37 后真实判断

M37 后项目已经有足够多的能力入口，下一步不应继续堆新能力。最重要的判断是：

- `OrchestratorService` 仍然过大，M38 应优先收缩。
- 个人自用场景下，不需要外部用户 onboarding、SaaS、多租户或插件市场。
- capability health、运行证据、失败原因、成本/使用情况需要更直观。
- Web workbench 应逐步变成个人日常驾驶舱，而不是只做功能目录。

## 5. 推荐 M38 形状

`M38 Phase 0` 应该先做：

1. 写 M38 phase doc 和 task cards。
2. 固化个人自用边界和日常操作剧本。
3. 选择 `OrchestratorService` 第一批抽取切口。
4. 设定运行证据、capability health、成本/失败展示的最小合同。
5. 跑 `pytest -q`、offline validation 和 doc link validation 作为入口门槛。
