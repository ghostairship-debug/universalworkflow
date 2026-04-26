# M77 Issue Register

本登记表是 M77 修复执行的当前入口，吸收最近几轮关于 OpenAI/Codex、MiniMax/DeepSeek、OpenCode、MMX、Vertex、LangChain、Pipeline 和 Cocos E2E 的评估结论。

## 状态口径

- `repaid`：已有代码、文档和测试证明问题已偿还。
- `partially_repaid`：主路径已修正，但仍缺 live proof、生产级闭环或后续集成。
- `open`：仍是当前能力开发前的阻塞或核心缺口。
- `carry_forward`：已登记但不阻塞当前主线。

## 当前问题

| ID | 状态 | 问题 | 当前处理 |
| --- | --- | --- | --- |
| M77-PROVIDER-001 | repaid | OpenAI API、Codex CLI、MiniMax/DeepSeek API、OpenCode CLI、MMX/Vertex generation、MCP tool、LangChain experimental 的边界混乱 | M80 已新增 verified-only capability health、provider alias live-proof 聚合和 30 天 route stats；provider、transport、modality、auth、fallback、cost hint 均可查询，OpenAI API 继续不冒充 ready。 |
| M77-MMX-001 | repaid | MMX/MiniMax 之前主要是 text evidence，没有真实 image/speech/music 生成主路径 | M77-M81 已新增 MiniMax image/speech/music generation API wrapper、二进制资产落盘、live proof、Cocos asset manifest、通用 asset factory、hash 去重、批量生成和 required asset NO-GO gate。 |
| M77-VERTEX-001 | repaid | Vertex/gcloud/GCP TTS 边界混乱，Vertex 主要停留在文本 evidence | 已把 Cloud Text-to-Speech 拆为 `gcp_tts_api`，`gcloud` 只作为认证/环境工具；Vertex Imagen 与 Gemini visual review 已进入 generation/review wrapper、live proof 和 M81 asset factory QA。 |
| M77-LANGCHAIN-001 | partially_repaid | LangChain 容易被误认为默认主路由 | provider contract 和文档已降级为 experimental / opt-in agent framework，不再作为默认 provider control plane。仍保留现有 adapter 兼容旧测试和实验用途。 |
| M77-PIPE-001 | partially_repaid | Pipeline run 会把未真实执行的 stage 标成 completed | 已修复为真实 stage 状态机：planning/review 只产 evidence，未显式执行的 capability stage 返回 blocked，validation gate 会短路，CLI 非 completed 返回非零退出码；AutomationLease 可约束 pipeline write_set。仍需把 workflow run / capability invocation 全量接入 stage executor。 |
| M77-COCOS-001 | repaid | Cocos E2E 仍偏技术 demo / E2E scaffold，缺编辑器可见的商业化 UI、美术、音效、动画、粒子、皮肤和关卡闭环 | M79 已完成商业化 Cocos pipeline v1：真实 Cocos Scene/Prefab/Component/UI/Audio/Animation/Particle/skin/level 结构、资产绑定、Web Mobile build 与浏览器 playtest。后续 M83 只处理模板化复用，不再把半成品 scaffold 视为完成。 |
| M67-CARRY-001 | carry_forward | 若干大文件仍偏大 | 当前不阻塞 provider/pipeline/Cocos 修复；后续能力开发触发痛点时再拆。 |

## 本轮已落地证据

- 新增 provider access contract：`packages/core_domain/provider_access.py`。
- 新增 direct coding proposal/API patch apply：`packages/core_domain/llm_coding_api.py`；`coding-apply` 需要 `AutomationLease(coding_patch_apply)`、write_set、unified diff、测试和 evidence。
- 新增 asset generation wrapper：`packages/core_domain/asset_generation.py`，并依据 MiniMax 官方 TTS/Music hex 响应修复 audio parser。
- capability descriptor/probe/control plane 已区分 `api_model`、`cli_agent`、`asset_generator`、`mcp_tool`、`experimental_agent_framework`。
- `workflowctl capability coding-proposal` 已支持 MiniMax/DeepSeek proposal-only 路径。
- `workflowctl capability coding-apply` 已支持 MiniMax/DeepSeek 生成 unified diff 后经 workflow write_set/lease/test gate 受控落盘。
- `workflowctl pipeline run` 不再伪完成 capability stage，失败/阻塞会写 evidence 并返回非零退出码。
- `workflowctl game cocos-e2e --require-commercial` 会拒绝明显缺失商业化美术/音效/UI/动画/粒子的技术 demo；M79 已补编辑器级商业化 v1 evidence。
- 测试：`tests/test_m77_provider_access.py`、`tests/test_pipeline_and_automation_cli.py` 覆盖当前修复。

## 下一步

1. 把 Pipeline stage executor 继续接到真实 workflow run、capability invocation 和 validation command manifest。
2. M83 把 M79 Cocos 商业化小游戏 pipeline 模板化，要求从 PDF/brief 到 asset factory、Cocos project、build、playtest 和 commercial readiness report 全链路可复用。
## M77 当前补充

- `M77-VERTEX-001`：已新增并真实跑通 `vertex_imagen` 与 `vertex_gemini_review` 两条 REST probe/wrapper；`gcp_tts_api` 继续独立表示 Cloud Text-to-Speech。
- `M77-MMX-001`：已新增并真实跑通 Cocos commercial asset manifest 批量生成，覆盖 MMX image/speech/music、GCP TTS voice 和可选 Vertex Gemini review。
- `M77-COCOS-001`：M79 真实跑通商业化 Cocos pipeline v1、Web Mobile build、browser playtest 和生成资产绑定；M83 的剩余目标是模板化为可复用 `commercial_cocos_game` pipeline。
- `M81-ASSET-FACTORY`：已新增通用 asset factory，支持 style guide、prompt manifest、provenance、hash 去重、批量生成、失败重试、required asset NO-GO 和 Vertex visual QA。
