# 里程碑历史摘要

本文档合并旧 phase docs、task cards、freeze reviews、archive、M2M 交接文档和根目录重复计划中的必要信息。它只提供历史摘要，不作为活跃执行计划。

## 当前基线

- 日期：2026-04-26
- 最新接受基线：`M72`
- 下一阶段建议：`M73` 能力层开发
- 产品前提：个人自用 / 本地 operator runtime
- 主入口：CLI、API、Web operator console、`/ui/workbench` streaming chat workbench
- 当前硬规则：workflow 共同开发、bug-first、scoped receipt、provider live proof、route/evidence/operator packet、phase 多 task card。

## 历史里程碑

| 阶段 | 摘要 | 当前结论 |
| --- | --- | --- |
| M20 | 达成深层 core-complete baseline，包含 scheduler-authority、remote worker、治理和 operator control 的关键基础 | 历史基线已吸收 |
| M25-M30 | 完成 policy control、operator packet、goal packet、dashboard/operator convergence 和 operator control freeze | 历史结论已吸收 |
| M31-M38 | 收缩边界、恢复 phase/task 模式、建立 doctor、本地 task-card 到 PR-ready summary 闭环 | 已吸收 |
| M39-M40 | `/ui/workbench` 升级为 LLM streaming chat workbench，加入 transcript、SSE、confirmation card 和 LangGraph chat control graph | 已接受 |
| M41-M42 | 建立强模型优先 workflow dogfood、Codex CLI 后端、MMX/Vertex/Claude artifact-only 骨架和多 cluster 角色层 | 已接受 |
| M43-M47 | 用真实 PDF 输入完成 block puzzle 示例，新增 adaptive LLM routing、dynamic cluster routing 和 operator 可见性 | 已接受 |
| M48-M51 | 恢复计划执行：workspace root、receipt gate、repo mutation atomicity、capability invocation ledger、local lease naming | 已吸收并归档 |
| M52-M60 | Bug-first 清债：测试矩阵、service decomposition、capability probes、cluster route stats 和治理报告 | 已吸收 |
| M61-M66 | 全量清债收口：Chat runtime package、CLI command families、Web UI receipt confirmation、计划内债务收口和 all-provider live probe | 已接受 |
| M67 | Workflow-dogfood 可信收口：真实调用 workflow 共同开发，修 receipt scope、capability live-proof、validation/CI、Web/CSP、scheduler 语义和热点瘦身 | 已完成 |
| M68 | LangGraph focused runtime：只接 advisory planning/review/evidence 子图，不直接 mutation，保留 opt-in | 已完成 |
| M69 | Capability control plane：统一 policy decision、live proof、receipt/write_set 校验与 execution receipt metadata | 已完成 |
| M70 | Provider contract consolidation：明确 Codex/OpenCode/Claude/MMX/Vertex/LangChain/Shell 的 provider contract，澄清 Gemini CLI/gcloud/Vertex 边界 | 已完成 |
| M71 | Cluster/concurrent execution contract：batch-resume 增加并发审计、串行降级、partial failure resume 和 route stats 维度 | 已完成 |
| M72 | Self-development loop：新增 self-development manifest，机器检查报告、task cards、evidence、operator packets 和 task-card policy | 已完成；M73 GO |

## M67-M72 关键结论

- workflow 已真实参与开发，不再只是文档声称：M67-M72 均有 task cards、route previews、workflow evidence、operator packets 和 phase commits。
- provider live probe 全量通过：shell、Codex、OpenCode、MMX、Vertex、Claude、LangChain 均有 require-live evidence。
- Gemini CLI 暂未接入；Gemini-family 能力当前走 Vertex/GCP；`gcloud` 是凭据/环境工具，不是 worker adapter。
- batch-resume 已具备并发前审计和降级语义：write_set 冲突、dirty write_set、SQLite lock 会降级串行。
- self-development manifest 固化了规则：phase 默认多 task card，单卡必须 `single_card_exception`。

## 历史材料治理

已关闭材料不再保留为活跃文档：

- 旧 `m*_phase_docs/`
- 旧 `docs/task_cards/`
- 根目录长期路线图、评估文档、恢复计划和重复执行报告
- 关闭后的临时 workflow state evidence

需要逐字审计旧材料时，使用 git 历史或 [docs/archive/evaluations/](archive/evaluations/)。
