# 里程碑历史摘要

本文档合并了旧 phase docs、task cards、freeze reviews、archive、M2M 交接文档和根目录重复计划中的必要信息。它只提供历史摘要，不作为活跃执行计划。

## 1. 当前基线

- 日期：2026-04-24
- 最新接受基线：`M38`
- 当前状态：`M38` 已接受；下一轮 M 尚未打开
- 当前产品前提：个人自用 / 本地 operator runtime
- 下一建议阶段：打开 M39 或下一轮 M 级计划

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
| M38 Phase 0 | 恢复当前 phase/task 模式，冻结安全 test runner、MCP canonical identity、doctor 和 `OrchestratorService` 第一批收缩切口 | 已接受 |
| M38 Phase 1 | 实现安全 test runner，移除 repo mutation test command 的默认 shell 执行和完整环境继承，新增 timeout、输出上限、scoped env、secret redaction 和 blocked attempt | 已接受 |
| M38 测试分层插入修复 | 将默认 `pytest -q` 从覆盖率全量慢测改为快速核心回归；CLI/API/Web/release 端到端套件标记为 `slow`；完整 `pytest -q --run-slow` 改为每个 M 收口跑一次 | 已接受 |
| M38 Phase 2 | 增加 MCP / capability canonical tool identity，并新增 `workflowctl doctor` 本地诊断入口；离线验证断言 canonical id 和 doctor redaction | 已接受 |
| M38 Phase 3 | 收缩 `OrchestratorService`，迁出 repo mutation coordinator 和 execution profile resolution helper；`services.py` 从 3833 行减少到 3520 行，净减少 313 行 | 已接受 |
| M38 Phase 4 | 打通本地 task card / issue-like 输入到 bounded patch、safe tests、review、PR-ready summary 的个人闭环；新增 `workflowctl run from-task-card`、`workflowctl run pr-ready-summary` 和 `/runs/{run_id}/pr-ready-summary` | 已接受 |
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

## 4. M37 后真实判断与 M38 处理结果

M37 后项目已经有足够多的能力入口，下一步不应继续堆新能力。M38 已处理其中的安全、测试分层和第一轮结构收缩问题；仍需长期关注的判断是：

- `OrchestratorService` 已从 3833 行降到 3520 行，但仍然过大，后续仍应继续收缩。
- 个人自用场景下，不需要外部用户 onboarding、SaaS、多租户或插件市场。
- capability health、运行证据、失败原因、成本/使用情况需要更直观。
- Web workbench 应逐步变成个人日常驾驶舱，而不是只做功能目录。

## 5. 推荐 M38 形状

`M38` 已完成。下一轮打开前的要求：

1. 先写新的 M 级计划和当前 phase/task 材料。
2. 保持个人自用 / 本地 operator runtime 的产品前提。
3. 不自动提交、不推送、不创建 GitHub PR，除非拥有者明确要求。
4. 每个 M 最终收口时再跑一次完整 `pytest -q --run-slow`。
