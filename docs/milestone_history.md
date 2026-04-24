# 里程碑历史摘要

本文档合并旧 phase docs、task cards、freeze reviews、archive、M2M 交接文档和根目录重复计划中的必要信息。它只提供历史摘要，不作为活跃执行计划。

## 当前基线

- 日期：2026-04-25
- 最新接受基线：`M42`
- 当前产品前提：个人自用 / 本地 operator runtime
- 当前主入口：`/ui/workbench` LLM streaming chat workbench
- 下一步建议：继续围绕真实多模态输入、Claude architect gate 低频实测、Codex artifact prompt 收缩、Workbench 体验和 `OrchestratorService` 收缩做小步开发

## 历史里程碑

| 阶段 | 摘要 | 当前结论 |
| --- | --- | --- |
| M20 | 达成深层 core-complete baseline，包含 scheduler-authority、remote worker、治理和 operator control 的关键基础 | 历史基线已吸收 |
| M25-M30 | 完成 policy control、operator packet、goal packet、dashboard/operator convergence 和 operator control freeze | 历史结论已吸收 |
| M31 | 做 boundary contraction 和 semantic honesty，确认后续需要继续收缩服务边界 | 主要遗留进入 `TD-STRUCT-*` |
| M32 | 吸收历史规划输入，建立 interaction / profile / cluster foundation | 历史结论已吸收 |
| M33 | 收缩 orchestration substrate，建立 shared orchestration service 和 canonical plan builder | `TD-STRUCT-004` 已偿还 |
| M34 | 继续 facade reduction 和 scheduler-authority interior cleanup | 部分结构债保留 |
| M35 | 建立 execution-profile contract、resolver precedence、config/read surfaces 和 execution explainability | 已接受 |
| M36 | 将 workbench preview 推进到 natural-language workbench v1，加入 follow-up queue 和 Web/CLI/API parity | 已接受 |
| M37 | 加入 governed generated profiles 和 bounded automation watchdog/controller | 已接受 |
| M38 | 恢复 phase/task 模式，实现安全 test runner、MCP canonical identity、`workflowctl doctor` 和本地 task-card 到 PR-ready summary 闭环 | 已接受 |
| M39 | 将 `/ui/workbench` 改造为 streaming chat workbench，新增持久化 transcript、SSE workflow event stream、确认卡和 chat action router | 已接受 |
| M40 | 将 `/ui/workbench` 升级为 LLM 流式聊天驾驶舱，新增 chat LLM runtime、assistant delta/final、LangGraph control graph、`after_event_id` 去重和聊天/状态事件分离 | 已接受 |
| M41 | 建立强模型优先 workflow dogfood：默认 Codex CLI 后端、MiniMax/DeepSeek LangChain 控制层、MMX/Vertex/Claude artifact-only 能力骨架、`architecture_delivery_cluster` 真机 E2E | 已接受 |
| M42 | 补齐搜索、设计、多模态、review、管理五类角色集群，扩展强 dogfood 路由，并修复 Windows Codex CLI 子进程树超时清理 | 已接受 |
| M2M 修复 | 完成根目录历史文档归档、scheduler-authority flag 双态兼容、默认 local-only 语义修正 | 结论已吸收 |

## M41 关键结论

M41 证明：没有 `OPENAI_API_KEY` 时，核心 dogfood 可以通过本机 Codex CLI 跑通。真实 `architecture_delivery_cluster` E2E 为 `intent_session_557cecbe8fc4` / `run_c0cad7dc9f58`，父 run `completed`，输出位于 `state/m41_phase13_dogfood_e2e_rerun4/`。

保留结论：MMX/Claude 仍主要是 degraded/fallback 验证，不代表真实多模态和 Claude gate 已完全产品化。

## M42 关键结论

M42 将 M41 的单条架构交付链路扩展为更完整的个人 runtime 角色层：

- `search_cluster`：搜索、来源、证据和引用核验。
- `design_cluster`：产品方向、交互/视觉方案和设计审查。
- `multimodal_cluster`：PDF、图片、截图、设计稿 evidence 入口。
- `review_cluster`：质量、测试、治理和中文文档收口。
- `management_cluster`：roadmap、phase/task 和 closeout 管理。

M42 真实 smoke 记录：

- `state/m42_management_cluster_smoke/summary.json`：一次长 timeout smoke，证明部分 Codex 子 run 可成功，失败子 run 会被保留为 failed 并 fallback。
- `state/m42_management_cluster_tree_timeout_smoke/summary.json`：进程树 timeout 修复后的收口 smoke，根 run `run_665006c2016d` completed，Codex 子 run 均在约 8 秒收束，无残留 `codex.exe`。

## 已移除的历史材料

以下材料已经关闭，不再保留为活跃文件：

- 旧 `m21_phase_docs/` 到 `m39_phase_docs/`
- 旧 `docs/reviews/`
- 旧 `docs/archive/`
- 旧 `docs/m2m/`
- 旧根目录重复计划或交接文档

如需逐字审计旧材料，请使用 git 历史查看对应文件。
