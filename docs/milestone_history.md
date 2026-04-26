# 里程碑历史摘要

本文档合并旧 phase docs、task cards、freeze reviews、archive、M2M 交接文档和根目录重复计划中的必要信息。它只提供历史摘要，不作为活跃执行计划。

## 当前基线

- 日期：2026-04-27
- 最新接受实现基线：`M79`
- 下一阶段建议：继续 M82-M83 能力层恢复：workflow self-development 与 commercial Cocos pipeline template。
- 产品前提：个人自用 / 本地 operator runtime。
- 主入口：CLI、API、Web operator console、`/ui/workbench` streaming chat workbench。
- 当前硬规则：workflow 共同开发、bug-first、scoped receipt、provider live proof、route/evidence/operator packet、phase 多 task card。

## 历史里程碑

| 阶段 | 摘要 | 当前结论 |
| --- | --- | --- |
| M20 | 达成深层 core-complete baseline，包含 scheduler-authority、remote worker、治理和 operator control 的关键基础 | 历史基线已吸收 |
| M25-M30 | 完成 policy control、operator packet、goal packet、dashboard/operator convergence 和 operator control freeze | 历史结论已吸收 |
| M31-M38 | 收缩边界、恢复 phase/task 模式、建立 doctor、本地 task-card 到 PR-ready summary 闭环 | 已吸收 |
| M39-M40 | `/ui/workbench` 升级为 LLM streaming chat workbench，加入 transcript、SSE、confirmation card 和 LangGraph chat control graph | 已接收 |
| M41-M42 | 建立强模型优先 workflow dogfood、Codex CLI 后端、MMX/Vertex/Claude artifact-only 骨架和多 cluster 角色层 | 已接收 |
| M43-M47 | 用真实 PDF 输入完成 block puzzle 示例，新增 adaptive LLM routing、dynamic cluster routing 和 operator 可见性 | 已接收 |
| M48-M51 | 恢复计划执行：workspace root、receipt gate、repo mutation atomicity、capability invocation ledger、local lease naming | 已吸收并归档 |
| M52-M60 | Bug-first 清债：测试矩阵、service decomposition、capability probes、cluster route stats 和治理报告 | 已吸收 |
| M61-M66 | 全量清债收口：Chat runtime package、CLI command families、Web UI receipt confirmation、计划内债务收口和 all-provider live probe | 已接收 |
| M67 | Workflow-dogfood 可信收口：真实调用 workflow 共同开发，修 receipt scope、capability live-proof、validation/CI、Web/CSP、scheduler 语义和热点瘦身 | 已完成 |
| M68 | LangGraph advisory comparison：只接 planning/review/evidence 子图，不直接 mutation，不承担 runtime substrate，保留 opt-in | 已完成 |
| M69 | Capability control plane：统一 policy decision、live proof、receipt/write_set 校验与 execution receipt metadata | 已完成 |
| M70 | Provider contract consolidation：明确 Codex/OpenCode/Claude/MMX/Vertex/LangChain/Shell 的 provider contract，澄清 Gemini CLI/gcloud/Vertex 边界 | 已完成 |
| M71 | Cluster/concurrent execution contract：batch-resume 增加并发审计、串行降级、partial failure resume 和 route stats 维度 | 已完成 |
| M72 | Self-development loop：新增 self-development manifest，机器检查报告、task cards、evidence、operator packets 和 task-card policy | 已完成 |
| M73 | Capability control layer：enforcement pilot、MCP broker v1、AutomationLease v0、LangGraph non-mutating spike、Manifest V2 provenance | 已完成 |
| M74 | Pipeline product layer：定义 `WorkflowPipeline` / `PipelineStage` contract 和 plan-of-plans preview | 已完成 |
| M75 | Pipeline execution v0：实现最小串行 pipeline run，并保留既有 run/control-plane 为 mutation 真相源 | 已完成 |
| M76 | H5 commercialization + Cocos E2E：加入 Cocos Creator 项目生成、Web Mobile build、browser playtest 和 feature coverage evidence | 已完成真实 E2E 骨架，不代表商业化成品完成 |
| M77 | Provider/asset generation repair：修正 OpenAI/Codex 边界、MiniMax/DeepSeek direct coding proposal、MMX/GCP/Vertex 生成能力与 pipeline 假完成风险 | 已完成主要接入修复 |
| M78 | Cocos commercial game body E2E scaffold：真实跑通生成资产、Cocos build、browser playtest 和商业化特征 coverage | 已完成 E2E scaffold；商业化 Cocos 成品仍未完成 |
| M79 | Cocos commercial pipeline v1：补真实 Cocos Scene/Node/Component/UI、资产绑定、动画/粒子、皮肤/关卡/道具入口、Web Mobile build 与 browser playtest | 已完成并推送；后续 M83 需模板化 |
| M80 | Provider runtime stabilization：verified-only health、provider route stats、30 天成功率/失败/延迟/fallback/cost 摘要 | 已完成 |
| M81 | Multimodal asset factory：style guide、prompt manifest、provenance、hash 去重、批量生成、失败重试、required asset NO-GO、Vertex visual QA | 已完成 |

## M73-M78 关键结论

- workflow 真实参与了本轮开发：保留 task cards、route previews、batch-resume evidence、operator packets 和 closeout gates。
- provider live probe 全量通过：shell、Codex、OpenCode、MMX、Vertex、Claude、LangChain 均有 require-live evidence。
- MCP broker 不再因 `include_mcp=True` 暴露全部 profile；必须显式 selector 或环境 selector。
- AutomationLease 为无人值守任务提供有界授权，但继续禁止 secrets、workspace root 扩大、未授权 publish/push/PR。
- Pipeline 已形成最小产品层，不替代既有 OrchestrationPlan，也不创建第二套 mutation 真相源。
- Cocos E2E 以桌面 PDF 为输入，生成真实 Cocos Creator 3.8 项目并跑 Web Mobile 浏览器验证。
- 事后评估确认：M78 产物是可运行脚手架；M79 已补编辑器可见商业化 v1 结构。M83 的重点是把该链路模板化和复用化，而不是再次做一次性脚本。
- M80-M81 已把 provider truth 和 asset generation 从具体 Cocos 脚本里抽出来；M82-M83 的剩余重点是 workflow 自开发闭环和 commercial Cocos pipeline template。

## 历史材料治理

已关闭材料不再保留为活跃文档：

- 旧 `m*_phase_docs/`
- 旧 `docs/task_cards/`
- 根目录长期路线图、评估文档、恢复计划和重复执行报告
- 关闭后的临时 workflow state evidence

需要逐字审计旧材料时，使用 git 历史。历史评估和阶段报告不再保留为工作树 Markdown，以避免仓库继续膨胀和旧结论污染当前入口。
