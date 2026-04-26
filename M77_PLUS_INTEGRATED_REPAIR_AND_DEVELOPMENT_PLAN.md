# M77+ 集成修复与后续开发计划

## 1. 当前事实判断

本计划整合 M77-M83 的修复路线。M77-M79 已执行完成的内容以 README、当前开发工作流、里程碑历史和技术债 JSON 为准；本文保留为路线说明，避免丢失 provider / workflow / pipeline / Cocos 的设计意图。

当前关键事实如下：

- 当前用户没有 OpenAI API。项目中的 OpenAI 直连 API 代码只能算可选路径/测试路径，不能作为真实可用 provider 宣称。当前 OpenAI 系能力实际应通过 Codex CLI 使用。
- Codex CLI 是复杂 coding、安全协议、repo mutation 和强模型 fallback 的真实主力入口。
- MiniMax 与 DeepSeek API 都可以用于 coding。它们不应只藏在 OpenCode 或 LangChain 后面，也应作为直接 API coding/review/patch proposal 能力进入 workflow。
- OpenCode 当前已接入 CLI，但没有接入 OMO / Oh My OpenCode / OpenCode 插件生态。当前最大价值是低成本模型池和外部 coding CLI 壳，而不是完整工具生态。
- MMX CLI、gcloud CLI、本机 OpenCode CLI 都存在，但当前项目里 MMX/Vertex 主要被接成 artifact-only 文本 evidence 通道，没有真正接多模态生成资产。
- MMX/MiniMax 接入的核心目的应是多模态生成，而不是只做视觉/文档提取。视觉提取很多大模型本身可做，MMX 的主要价值应体现在 image / speech / music / video 等资产生成。
- Vertex 当前也存在同类降级：名义是 Gemini-family / multimodal entrypoint，实际主要是 `generate_content()` 文本 evidence。gcloud 更应作为认证和环境工具，而不是生成执行器本身；Cloud Text-to-Speech 属于 GCP TTS 能力，不再归入 Vertex 本体。
- LangChain 当前对主线几乎没有不可替代价值，应降级为 experimental / opt-in agent framework。未来可用于动态工具 agent、RAG、MCP 组合、provider 快速实验，但不应位于 provider control plane 主路径。
- MCP 应定位为工具接入层，不是 LLM provider 本体。MCP 适合 workspace readonly、web search、understand image、外部业务工具等能力。
- M75 pipeline 与 M76 Cocos E2E 曾偏 v0/技术 demo；M78 补强真实 Cocos build/playtest 和生成资产接入，M79 已进一步补商业化 Cocos v1 的编辑器可见 Scene / UI / Component / asset binding / animation / particle / skin / level / prop 结构。
- 留存策略本轮暂不处理。后续仍会频繁大规模清理，因此 evidence 保留只需满足当前 closeout 和可追踪需要，不做长期归档策略设计。

## 2. 总体原则

- 继续采用 workflow 共同开发，而不是纯人工工程推进。
- 每个 phase 至少拆成多张 task card：implementation、verification、review/evidence。单 task card phase 必须写明例外原因。
- 每个 phase 前跑 route preview、policy preview、goal packet，并记录 evidence。
- artifact-only、review、disjoint write_set task 可并发；repo mutation 并发必须通过 write_set audit，默认最多 `--max-workers 2`。
- bug-first：workflow、receipt、lease、capability probe、provider live proof、pipeline executor、Cocos E2E、route/evidence 任一路径出 bug，先修 workflow bug 并补回归测试，再继续业务 phase。
- 所有 provider readiness 必须来自 live proof。dry-run、simulated、fallback-only、generic greeting 不得标记为 `verified_ready`。
- 成功 phase 可以 1 phase 1 commit；失败 phase 不提交，只留下 evidence 和阻塞说明。

## 3. M77 修复计划：接入层与降级项收口

M77 是一个完整 milestone，内部包含多个 phase，不拆成多个小 M。目标是修复 M73-M76 暴露的降级项，让后续能力开发建立在可信的 provider/control plane/pipeline 上。

### P0：真实能力基线与文档校准

- 新建 M77 issue register，登记 open / repaid / blocked / obsolete。
- 修正文档口径：M73-M76 是“骨架已落地，但部分实现降级”，不能继续写成全部完整完成。
- 明确当前真实 provider：
  - `codex_cli`：复杂 coding 主路径。
  - `minimax_api`：直接 LLM coding/review/asset generation 主路径之一。
  - `deepseek_api`：中等 review/validation/patch proposal 主路径之一。
  - `opencode_cli`：低成本 coding CLI 壳，当前不含 OMO 生态。
  - `mmx_generation_api`：MiniMax 图像/语音/音乐/后续视频生成。
  - `vertex_generation_api`：Imagen/Gemini image 与视觉审查。
  - `gcp_tts_api`：Cloud Text-to-Speech 语音 fallback。
  - `mcp_tool`：工具接入。
  - `langchain_agent`：experimental opt-in。

### P1：统一 Provider / Tool / Agent / Asset 接入模型

新增或固化一个统一能力分类：

- `api_model`：MiniMax、DeepSeek、Vertex Gemini、可选 OpenAI。
- `cli_agent`：Codex CLI、OpenCode CLI、Claude CLI。
- `mcp_tool`：workspace、web search、understand image、外部工具。
- `asset_generator`：MMX image/speech/music/video、Vertex Imagen/Veo/Gemini image、GCP TTS。
- `experimental_agent_framework`：LangChain。

所有能力输出统一进入 `CapabilityInvocation`，至少记录：

- provider、adapter、transport：`api | sdk | cli | mcp | langchain`。
- modality：`text | code | image | audio | music | video | tool`。
- live proof 状态。
- artifact path、mime、hash、size、model、latency、failure class。
- 是否需要 receipt / automation lease / write_set。

### P2：MiniMax / DeepSeek 直接 Coding API

- 新增 `llm_coding_api` 能力，不再把 MiniMax/DeepSeek coding 只放在 OpenCode/LangChain 背后。
- MiniMax M2.7 支持 plan、review、patch proposal、small refactor proposal。
- DeepSeek V4 Flash 支持 medium review、validation analysis、patch proposal；失败直接 fallback Codex CLI，不 fallback MiniMax。
- 直接 API 只生成 proposal，不直接写仓库。真正落地必须走 workflow `patch_apply + write_set + receipt/lease`。
- OpenCode 保留为 external coding CLI，用于需要 agent 自读仓库、长上下文命令循环、低成本模型池的任务。

### P3：MMX/MiniMax 多模态生成主路径

当前 `MMXMultimodalAdapter` 应重命名或重新定位为 `minimax_text_evidence`，保留兼容 alias，但不再把它当作多模态生成能力。

新增真实 MMX 生成能力：

- `mmx_image_generation`：调用 MiniMax image generation API，输出 PNG/WebP/JPEG。
- `mmx_speech_generation`：调用 MiniMax TTS，输出 MP3/WAV。
- `mmx_music_generation`：调用 MiniMax music generation，输出 BGM 音频。
- `mmx_video_generation`：先进入 future/optional，不作为 M77 必交付，避免扩大主线。

MiniMax Token Plan 作为默认支持目标：

- Token Plan key 可用于多模态模型访问。
- 不能把 Token Plan 不支持的 highspeed 模型当作默认。
- probe 必须生成真实二进制资产，小 PNG / 小音频 / 短音乐片段，而不是只返回 JSON。

### P4：Vertex 生成能力修复

当前 `VertexMultimodalAdapter` 应重命名或重新定位为 `vertex_text_evidence`，保留兼容 alias。

新增 Vertex 生成/审查能力：

- `vertex_imagen_image_generation`：用 Imagen 生成游戏素材 fallback。
- `vertex_gemini_image_generation`：用 Gemini image 模型做图像生成/编辑或视觉方案补充。
- `gcp_tts_audio_generation`：用 Cloud Text-to-Speech 作为语音/提示音 fallback；旧 `vertex_tts` 仅作为兼容 alias。
- `vertex_visual_review`：用 Gemini-family 做截图/素材/游戏界面审查。
- `vertex_veo_video_generation`：列为 future，不进 M77 必交付。

gcloud 的角色：

- 认证状态检查。
- 项目、区域、ADC、启用 API 的 doctor 诊断。
- 必要时获取 access token。
- 不作为主生成执行器。

### P5：LangChain 降级为 Experimental

- 从默认 route / provider contract 主路径移除 LangChain。
- 保留 `LangChainAgentAdapter`，但明确标记为 experimental / opt-in。
- LangChain 只用于：
  - 动态工具 agent。
  - RAG / memory / document workflow。
  - MCP 工具组合实验。
  - provider 快速验证。
- 不允许 LangChain 的 fallback-only 输出被标记为真实 provider ready。

### P6：AutomationLease 与 Capability Control Plane 补强

- 将 AutomationLease 真正接入 unattended resume、batch-resume、pipeline run、validation/test matrix、Cocos E2E。
- 校验 workspace root、allowed actions、denied actions、write_set allowlist、expires_at、max_resume_count。
- 所有 high-risk 或 asset generation 写入均进入 CapabilityInvocation。
- 失败路径必须返回结构化拒绝，而不是静默 fallback。

### P7：真实 Pipeline Executor

修复当前 pipeline run 偏 preview/mock 的问题：

- stage 必须真实执行 workflow run、capability invocation 或 validation command。
- `depends_on` 和 serial execution 必须生效。
- validation gate 失败后后续 stage 不得假 completed。
- 每个 stage 输出 stage_result、evidence path、failure class。
- `h5_game_commercialization_pipeline` 必须能驱动 PDF intake、设计、资产生成、Cocos 构建、浏览器 playtest。

### P8：真实商业化 Cocos 小游戏 Pipeline

使用桌面 PDF 作为产品需求输入，输出真实 Cocos Creator 项目，不再用 DOM canvas overlay 或技术 demo 冒充完成。

商业化游戏产物最低要求：

- Cocos Scene / Node / Component / UI 真实实现。
- 10x10 棋盘、三候选块、拖拽放置、行列消除、刷新、防卡死、Game Over。
- 经典模式和前 7 关闯关。
- Combo / Streak / 分数 / 目标 / 奖励。
- 三类道具、复活广告占位、插屏广告点位。
- 皮肤、背景、拼图收集、关卡切换均真实可见。
- MMX 生成主美术资源：背景、皮肤、道具 icon、按钮、粒子贴图、宣传图。
- MMX 生成主音频资源：BGM、点击、放置、消除、combo、失败、奖励音效。
- Vertex 可作为图像 fallback 和视觉审查；GCP TTS 作为语音 fallback。
- 程序化占位只允许用于 CI 或无凭据测试，不得标记商业化完成。
- 浏览器自动测试必须覆盖 canvas 非空、像素变化、拖拽成功、分数变化、消除、关卡切换、皮肤切换、道具、广告占位、移动端 390x844 无遮挡。

## 4. M78-M83 后续开发计划

M77/M78 已完成 provider/asset/E2E scaffold 关键修复；M79 已完成商业化 Cocos pipeline v1。当前恢复能力层开发的顺序是 M80 provider runtime truth、M81 asset factory、M82 workflow 自开发闭环、M83 commercial Cocos pipeline template。

### M78：Provider/Asset Repair + Cocos E2E Scaffold（已执行）

- 实际执行中，M78 优先修复了 provider/asset generation 与 Cocos E2E game body。
- 已真实跑通 MMX/MiniMax image、speech、music，GCP TTS，Vertex Imagen/Gemini review。
- 已真实生成 Cocos Creator 项目、构建 Web Mobile、跑浏览器 playtest，并把 generated assets 接入 runtime manifest。
- 当前结论：M78 是可信 E2E scaffold，不是完整商业化 Cocos 工程；不能把 `commercial_go_no_go=GO` 解读为 final commercial ready。

### M79：H5 / Cocos 商业化游戏生产线 v1（已执行）

- 已将 Cocos E2E 从单个 scaffold 推进为可打开、可构建、可试玩的 Cocos production pipeline v1。
- 支持从 PDF/策划文档生成：
  - 产品需求映射。
  - 游戏设计 brief。
  - 美术风格 brief。
  - 资源清单。
  - Cocos 项目。
  - 编辑器可见的 Scene / Node / Prefab / Component / UI 层级。
  - MMX/Vertex 图片到 SpriteFrame、MMX/GCP 音频到 AudioClip/AudioSource 的真实绑定。
  - 构建与 playtest。
- 支持商业化检查：广告点位、付费/道具入口、留存任务、移动端性能、首屏体验、编辑器可见性、视觉质量、半成品拒绝。

### M80：Provider Runtime 体系稳定化（当前执行）

- 完成 provider registry：每个 provider 记录 transport、modality、成本等级、凭据来源、live proof、fallback 策略。
- CLI/API capability health 的 `--verified-only` / `verified_only=true` 只展示 live probe 或近期真实成功调用支撑的 provider。
- 增加 provider route decision ledger，统计最近 30 天成功率、失败类型、延迟、成本估计。

### M81：多模态资产工厂

- 建立 asset manifest、prompt manifest、style guide、asset provenance。
- 支持批量生成、失败重试、同风格变体、素材 hash 去重。
- 引入视觉 QA：截图审查、UI 遮挡检测、风格一致性检查。
- 后续可加入视频素材生成，但不作为 v1 阻塞。

### M82：Workflow 自开发闭环

- 用 workflow 自己完成一个中等规模内部改进作为 dogfood demo。
- 真实使用并发 task cards、route decision、provider fallback、review gate、test gate。
- 输出完整 run manifest，从 task card 到 evidence、test、commit 可追踪。

### M83：能力层开发恢复

在 M77-M82 通过后，恢复更高层能力开发：

- 更完整的 game pipeline。
- 多模态内容生产。
- 模板化商业化 H5 项目。
- provider adaptive routing。
- 可选接入 OpenCode OMO / Gemini CLI / 更多 provider。

## 5. 验收标准

M77-M83 closeout 必须满足：

- 文档不再宣称 OpenAI API 可用；Codex CLI 与 OpenAI API 明确区分。
- MMX/Vertex 的 text evidence 与 generation 能力分离，命名不误导。
- MiniMax/DeepSeek API 可生成 coding proposal，并通过 `coding-apply` 的 AutomationLease/write_set/test gate 受控落地。
- MMX image/speech/music 至少各有一个真实 live proof；缺凭据则 M77 游戏商业化能力 NO-GO。
- Vertex image/visual review 或 GCP TTS 至少完成一个真实 live proof；不可用时标记 blocked，不冒充 fallback success。
- LangChain 不在默认主 route 中，只作为 experimental opt-in。
- AutomationLease 接入无人值守执行路径。
- Pipeline run 不再假 completed。
- Cocos pipeline 不能只生成 E2E scaffold；商业化验收必须打开 Cocos Creator 可见真实 2D 场景、UI、Prefab/Component、SpriteFrame/AudioClip、Animation/Particle、皮肤、关卡、广告/道具入口。M79 已完成 v1，M83 需模板化复用。
- workflow 编排和并发至少完成：
  - artifact-only 并发成功。
  - disjoint write_set 并发成功。
  - write_set conflict 拒绝或降级串行。

## 6. 测试计划

基础测试：

- `python -m pytest tests/test_capability_probe.py tests/test_capability_control_plane.py -q`
- `python -m pytest tests/test_pipeline_and_automation_cli.py -q`
- `python -m pytest tests/test_cocos_e2e.py -q`
- `python -m infra.scripts.check_doc_links`

新增测试方向：

- MiniMax/DeepSeek direct coding API proposal parser。
- API proposal 到 patch_apply 的 write_set/receipt/lease gate。
- MMX image/speech/music live proof 和 false-positive 拒绝。
- Vertex Imagen/TTS/Gemini image live proof 和 blocked evidence。
- LangChain experimental opt-in，不参与默认 route。
- OpenCode OMO 未集成时不宣称生态工具可用。
- Pipeline stage 真实执行和 validation failure short-circuit。
- Cocos 商业化游戏 browser playtest。

## 7. 默认决策

- 不接 OpenAI API，除非以后用户明确提供 `OPENAI_API_KEY`。
- Gemini CLI 暂不接，Gemini-family 继续走 Vertex。
- MMX 资产生成优先走 MiniMax API/Token Plan，不优先走 MMX CLI。
- Vertex 生成优先走 API/SDK，gcloud 只做认证/环境。
- OpenCode 保留，但当前定位为 low-cost coding CLI，不宣称 OMO 工具体系。
- LangChain 保留但 experimental，不进入主线默认路由。
- 商业化 Cocos 游戏要求真实美术/音效/动画/粒子/关卡/皮肤闭环，不能再用简单 demo 降级。
## Current Implementation Note

- `vertex_imagen` and `vertex_gemini_review` now exist as Vertex AI REST wrappers and capability probes; `gcp_tts_api` remains the separate Google Cloud Text-to-Speech route.
- `workflowctl game cocos-assets` now batches MMX/MiniMax image, speech, music, GCP TTS voice, and optional Vertex Gemini visual review into a commercial asset manifest.
- M78 added a real Cocos E2E scaffold and browser playtest with generated assets; M79 then added the commercial Cocos v1 body with editor-visible native Cocos UI, component manifests, animation/particle evidence, level/skin systems, asset bindings, Web Mobile build, and browser playtest evidence. M83 should template this path rather than rebuild it as another one-off.
