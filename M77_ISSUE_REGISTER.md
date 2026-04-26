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
| M77-PROVIDER-001 | partially_repaid | OpenAI API、Codex CLI、MiniMax/DeepSeek API、OpenCode CLI、MMX/Vertex generation、MCP tool、LangChain experimental 的边界混乱 | 已新增 provider access contract，明确 Codex CLI 是当前 OpenAI-family 主路径，OpenAI API 只是可选 API route；MiniMax/DeepSeek direct coding API、MMX/GCP/Vertex asset generator、MCP tool、LangChain experimental 分层已进入 capability 描述和测试。 |
| M77-MMX-001 | partially_repaid | MMX/MiniMax 之前主要是 text evidence，没有真实 image/speech/music 生成主路径 | 已新增 MiniMax image/speech/music generation API wrapper、二进制资产落盘、manifest 和 live probe 路径；本轮真实跑通 image、speech、music 三类二进制 live proof，并真实跑通 Cocos commercial asset manifest 批量调用。商业化风格管理和 game body 集成仍需继续。 |
| M77-VERTEX-001 | partially_repaid | Vertex/gcloud/GCP TTS 边界混乱，Vertex 主要停留在文本 evidence | 已把 Cloud Text-to-Speech 拆为 `gcp_tts_api`，旧 `vertex_tts` 仅兼容 alias；已修复 Windows gcloud shim、ADC quota project、IAM Service Usage Consumer、Vertex AI API/IAM 和 token source 选择，并真实跑通 GCP TTS、`vertex_imagen`、`vertex_gemini_review` live proof。 |
| M77-LANGCHAIN-001 | partially_repaid | LangChain 容易被误认为默认主路由 | provider contract 和文档已降级为 experimental / opt-in agent framework，不再作为默认 provider control plane。仍保留现有 adapter 兼容旧测试和实验用途。 |
| M77-PIPE-001 | partially_repaid | Pipeline run 会把未真实执行的 stage 标成 completed | 已修复为真实 stage 状态机：planning/review 只产 evidence，未显式执行的 capability stage 返回 blocked，validation gate 会短路，CLI 非 completed 返回非零退出码；AutomationLease 可约束 pipeline write_set。仍需把 workflow run / capability invocation 全量接入 stage executor。 |
| M77-COCOS-001 | partially_repaid | Cocos E2E 仍偏技术 demo / E2E scaffold，缺编辑器可见的商业化 UI、美术、音效、动画、粒子、皮肤和关卡闭环 | 已新增 `--require-commercial` 硬门禁，并在 M78 跑通真实 Cocos build/playtest 与生成资产接入；但打开 Cocos 工程仍是半成品脚手架，不能声明商业化游戏已完成。M79 必须重做为真实 Cocos Scene/Prefab/Component/UI/Audio/Animation 生产线。 |
| M67-CARRY-001 | carry_forward | 若干大文件仍偏大 | 当前不阻塞 provider/pipeline/Cocos 修复；后续能力开发触发痛点时再拆。 |

## 本轮已落地证据

- 新增 provider access contract：`packages/core_domain/provider_access.py`。
- 新增 direct coding proposal/API patch apply：`packages/core_domain/llm_coding_api.py`；`coding-apply` 需要 `AutomationLease(coding_patch_apply)`、write_set、unified diff、测试和 evidence。
- 新增 asset generation wrapper：`packages/core_domain/asset_generation.py`，并依据 MiniMax 官方 TTS/Music hex 响应修复 audio parser。
- capability descriptor/probe/control plane 已区分 `api_model`、`cli_agent`、`asset_generator`、`mcp_tool`、`experimental_agent_framework`。
- `workflowctl capability coding-proposal` 已支持 MiniMax/DeepSeek proposal-only 路径。
- `workflowctl capability coding-apply` 已支持 MiniMax/DeepSeek 生成 unified diff 后经 workflow write_set/lease/test gate 受控落盘。
- `workflowctl pipeline run` 不再伪完成 capability stage，失败/阻塞会写 evidence 并返回非零退出码。
- `workflowctl game cocos-e2e --require-commercial` 会拒绝明显缺失商业化美术/音效/UI/动画/粒子的技术 demo；M78 暴露出当前 gate 仍偏 E2E feature flag，不能替代编辑器级成品验收。
- 测试：`tests/test_m77_provider_access.py`、`tests/test_pipeline_and_automation_cli.py` 覆盖当前修复。

## 下一步

1. 把 MiniMax image/speech/music live proof 从单点 probe 扩展为 Cocos asset manifest 批量生成。
2. 补 Vertex Imagen/Gemini image/visual review，TTS 之外的生成能力不能继续停留在计划中。
3. 把 Pipeline stage executor 继续接到真实 workflow run、capability invocation 和 validation command manifest。
4. M79 重做 Cocos 商业化小游戏 pipeline，要求真实 Cocos Scene / Node / Prefab / Component / UI、SpriteFrame/AudioClip 绑定、Animation/Particle、皮肤、关卡、广告点位、道具和移动端视觉 playtest。
## M77 当前补充

- `M77-VERTEX-001`：已新增并真实跑通 `vertex_imagen` 与 `vertex_gemini_review` 两条 REST probe/wrapper；`gcp_tts_api` 继续独立表示 Cloud Text-to-Speech。
- `M77-MMX-001`：已新增并真实跑通 Cocos commercial asset manifest 批量生成，覆盖 MMX image/speech/music、GCP TTS voice 和可选 Vertex Gemini review。
- `M77-COCOS-001`：M78 真实跑通 Cocos E2E scaffold、Web Mobile build、browser playtest 和生成资产接入；但 Cocos 原生 UI、Prefab/Component、动画、粒子、关卡切换、皮肤/画廊和真正商业化 game body 仍未完成，不能声明商业化游戏已完成。
