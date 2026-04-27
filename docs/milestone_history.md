# 里程碑历史摘要

本文档只提供历史摘要，不作为活跃执行计划。当前判断以 README、当前开发工作流和技术债登记为准。

## 当前基线

- 日期：2026-04-27
- 最新接受实现基线：`M83`
- 当前修正阶段：`M85-M90` LangGraph 与 workflow 长线收敛规划
- 产品前提：个人自用、本地优先的 operator runtime
- 当前硬规则：workflow 共同开发、bug-first、scoped receipt、provider live proof、route/evidence/operator packet、phase 多 task card

## 历史里程碑

| 阶段 | 摘要 | 当前结论 |
| --- | --- | --- |
| M20 | 深层 core-complete baseline，包含 scheduler-authority、remote worker、治理和 operator control 基础 | 已吸收 |
| M25-M30 | policy control、operator packet、goal packet、dashboard/operator convergence | 已吸收 |
| M31-M38 | 恢复 phase/task 模式、doctor、本地 task-card 到 PR-ready summary 闭环 | 已吸收 |
| M39-M40 | `/ui/workbench` streaming chat workbench、SSE、confirmation card、LangGraph chat control graph | 已接收 |
| M41-M42 | 强模型 workflow dogfood、Codex CLI 后端、MMX/Vertex/Claude artifact-only 骨架、多 cluster 角色层 | 已接收 |
| M43-M47 | 真实 PDF 输入、block puzzle 示例、adaptive LLM routing、dynamic cluster routing、operator 可见性 | 已接收 |
| M48-M51 | workspace root、receipt gate、repo mutation atomicity、capability invocation ledger、local lease naming | 已归档 |
| M52-M60 | bug-first 清债、测试矩阵、service decomposition、capability probes、cluster route stats、治理报告 | 已吸收 |
| M61-M66 | Chat runtime package、CLI command families、Web UI receipt confirmation、计划内债务收口、all-provider live probe | 已接收 |
| M67 | workflow-dogfood 可信收口：receipt scope、capability live-proof、validation/CI、Web/CSP、scheduler 语义、热点瘦身 | 已完成 |
| M68 | LangGraph advisory comparison：planning/review/evidence 子图，opt-in，不直接 mutation | 已完成 |
| M69 | capability control plane：统一 policy decision、live proof、receipt/write_set 校验 | 已完成 |
| M70 | provider contract consolidation：澄清 Codex/OpenCode/Claude/MMX/Vertex/LangChain/Shell 边界 | 已完成 |
| M71 | cluster/concurrent execution contract：并发审计、串行降级、partial failure resume、route stats | 已完成 |
| M72 | self-development loop：self-development manifest、task-card policy、机器检查报告 | 已完成 |
| M73-M76 | capability control、MCP broker、AutomationLease、Pipeline contract/execution、Cocos E2E 骨架 | 已完成骨架 |
| M77-M78 | provider/asset repair、MMX/GCP/Vertex generation live proof、Cocos build/playtest scaffold | 已完成技术链路 |
| M79 | Cocos commercial pipeline v1：编辑器可见结构、资源绑定、动画/粒子/皮肤/关卡入口、Web Mobile build/playtest | 技术上完成，但不能视为商业成品 |
| M80 | provider runtime stabilization：verified-only health、route stats、runtime truth | 已完成 |
| M81 | multimodal asset factory：style guide、prompt manifest、provenance、hash 去重、required asset NO-GO、Vertex QA | 已完成 |
| M82 | workflow self-development：active truth check、dogfood evidence、DeepSeek direct API 兼容修复 | 已完成 |
| M83 | `commercial_cocos_game` pipeline 模板：asset factory -> Cocos generation/build/playtest -> readiness gate | 已完成模板化 |
| M84 | 卫生清理与商业化质量重置：清理生成态文件，修正“商业化 GO”过度表述 | 当前阶段 |
| M85-M90 | LangGraph 与 workflow 长线收敛：迁移矩阵、graph execution kernel、interrupt/receipt 融合、checkpoint/time travel、multi-agent subgraph、垂直 pipeline rebase | 计划阶段 |

## M84/M85 关键结论

- 商业化 Cocos/H5 游戏生成仍是正式业务需求。
- 当前 pipeline 和代码保留，不从仓库删除。
- 最近一次真实生成质量不足：UI 原始、关卡浅层、面板不可用、音频突兀、HTML 双击不可玩。
- 不能再把状态变量覆盖、feature flag、HTML/APK 打包或浏览器事件覆盖当成商业化成品验收。
- 下一阶段先做 LangGraph 与 workflow 的编排底座收敛，避免继续重复实现 checkpoint、人审、并发、repair loop 和多 agent 编排；商业化游戏作为后续压力测试和业务验证场景。

## 历史材料治理

已关闭材料不再保留为活跃 Markdown：

- 旧 `m*_phase_docs/`
- 旧 `docs/task_cards/`
- 根目录长期路线图、评估文档、恢复计划、重复执行报告
- 临时 workflow state evidence

需要逐字审计时使用 Git 历史。
