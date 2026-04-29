# 当前开发工作流

## 2026-04-28 新窗口交接

当前商业小游戏 pipeline 补全任务必须从交接文档继续：

- [Commercial Game Pipeline Handoff](docs/development/commercial_game_pipeline_handoff_2026_04_28.md)
- [Commercial Game Workflow Next Development](docs/development/commercial_game_workflow_next_development_2026_04_28.md)
- [Commercial Game Pipeline Evaluation 2026-04-28](docs/evaluations/commercial_game_pipeline_evaluation_2026_04_28.md)

2026-04-28 closeout notes:

- Bug-first workflow repairs are complete for route/evidence, progress-aware watchdogs, scheduler lease terminal release, stale scheduler lease repair, parent receipt propagation into orchestration children, and duplicate remote worker callback idempotency.
- OpenCode is not the default repo-mutation route for `from-task-card` patch apply; Codex/OpenCode adapter timeouts now produce structured timeout type, `failure_class`, stream previews, last-output context, mutation result, and recovery guidance instead of an opaque no-patch timeout.
- Unattended execution now has heartbeat evidence for local worker lease renewals and pipeline runs; scheduler-authority leases are released on terminal or human-review states instead of leaving false expired-authority findings.
- Asset modality repair split `voice` / `music` / `sfx`. Commercial Cocos `sfx_place` and `sfx_clear` now use local procedural SFX WAV generation with QA metadata; `voice_reward` remains voice/TTS, and Cocos runtime bindings preserve SFX/voice/music modalities.
- `commercial_game_production` evaluation reached honest final-gate failures with repair packets. Correction: Cocos Creator is installed locally at `C:\ProgramData\cocos\editors\Creator\3.8.8\CocosCreator.exe`; the previous `cocos_creator_exe_missing` result was a pipeline autodiscovery bug when `--creator-exe` was omitted, and that bug is now fixed.
- The older real game attempt `pipeline_061e3703e442` remains `NO-GO`.
- Superseding no-degradation gate v2 review reclassified `pipeline_a41e231c69a4` as historical automated scaffold/build/playtest evidence, not final commercial readiness proof.
- Strict rerun `zero_degradation_rerun_20260428_evidencefix` wrote evidence at `state/long_runs/zero_degradation_rerun_20260428_evidencefix/zero_degradation_rerun_20260428_evidencefix.json` and failed honestly with `commercial_game_no_degradation_failed`. Live LLM role proof passed; missing Cocos ecosystem bridge, same-project worker patch proof, 8 real level goals, visible shop/skin state, audio runtime verification, strict build-exit acceptance, and human player review remain blockers.
- 2026-04-29 zero-degradation Cocos/worker repair: `collect_cocos_ecosystem_bridge_evidence` now produces a project-local Cocos Editor bridge package, trusted bridge-report contract, license/cost manifest, and filesystem-only rejection evidence. Follow-up Cocos ecosystem repair added an unattended bridge runner and verified local Cocos Creator 3.8.8 Editor/AssetDB/Scene/Prefab/Build API evidence in `cocos_bridge_smoke_20260429_145028`; `ecosystem_integration_go` can now pass for the local Editor bridge. `commercial_game_production` task-card worker now uses one persistent Cocos project shell and calls `workflowctl run from-task-card --execute` with receipt-bound Codex patch apply, writing `same_project_patch_ledger.json`; it no longer hands DB task cards to the deterministic Cocos E2E generator. Strict rerun `zero_degradation_cocos_worker_rerun4_20260429` remained `NO-GO`: real assets and live role proof passed, first same-project patch failed with `provider_idle_timeout`, product-depth gates and human player review were absent.

核心规则：workflow 自己出 bug 时，Codex 可以先做 bug-first 兜底修复；业务 pipeline 补全必须回到 `workflowctl run from-task-card ...` 执行，Codex 只做审阅、兜底和验收。

## 2026-04-28 收束：删除旧 Cocos 模板交付路径

- `commercial_cocos_game` 固定模板流水线不再作为可执行交付入口；调用它只能得到 `legacy_cocos_template_removed` 阻塞结果。
- 后续商业化小游戏必须走 `commercial_game_production` 真实生产管线：统一资料包、单 agent 角色输出、数据库 task card、真实资产生成、task-card worker 实现、玩家 QA、supervisor 和最终商业化验收。
- Cocos empty project 或 E2E scaffold 只能作为底层诊断/启动壳，不能作为商业游戏内容模板，也不能单独证明 `commercial_playable_go`。
- 修复循环必须围绕同一个目标工程做定点修复；不得每次重新生成模板工程来掩盖问题。

## 当前版本说明

- 当前工作状态：`M109` 已作为 pipeline / technical-smoke baseline 接受；2026-04-28 的后续工作是 `commercial_game_production` 与 workflow-wide bug-first 修复，不自动进入 M110 或生成 M110 task card。
- 接受实现基线：M109 已完成统一资料包、单 agent 角色管线、设计/方案输出、多模态路由真相表、DB task-card quality gate、有限 Cocos technical-smoke trial 和 cluster-upgrade review。
- 当前纠偏：Cocos 生产线可生成可检查的本地样机工程，但 `commercial_playable_go` 仍必须依赖真实玩家视角证据；缺少 build/playtest 证据时只能标为样机，不能宣称商业化成品。后续商业小游戏必须走 `commercial_game_production`，并继续保留 workflow receipt、lease、write_set、provider live proof、evidence 和 operator packet 边界。
- 2026-04-29 no-degradation 纠偏结果：`pipeline_a41e231c69a4` 只保留为 gate v1 历史证据；最新严格 run `zero_degradation_cocos_worker_rerun4_20260429` 为 `NO-GO`，不得声明 `commercial_playable_go=true`。后续 `cocos_bridge_smoke_20260429_145028` 已补齐真实本地 Editor bridge/API 证据，但商业本体的同项目 task-card patch、产品深度、构建/试玩和人工验收仍未完成。
- 商业化生产线 v2 细化设计见根目录 [COMMERCIAL_GAME_PRODUCTION_V2_PIPELINE_DESIGN.md](COMMERCIAL_GAME_PRODUCTION_V2_PIPELINE_DESIGN.md)：它定义 stage 内部 phase graph、资产图、Cocos bridge worker、supervisor repair loop 和 final gate contract；它不是 active task-card 导出，也不自动开启 M110。
- 活跃真相集：`README.md`、`AGENTS.md`、本文件、`docs/milestone_history.md`、`docs/tech-debt-registry.md`、`docs/governance/tech_debt_registry.json`。
- 历史评估、旧路线图、旧计划和生成态 evidence 不保留为活跃工作树文档。需要逐字审计时使用 Git 历史。

本项目仍是个人自用、本地优先的 operator runtime。所有计划、文档和验证都服务于“能否稳定、诚实、可恢复地继续开发”，不服务于公开 SaaS、多租户、公共 onboarding 或第三方托管执行。

## Plan / Milestone / Phase / Task Card

- 一个 plan 应包含多个 milestone。
- 一个 milestone 应包含多个 phase。
- 一个 phase 默认应包含多张 task card。
- task card 是最小可执行单元。
- 开发计划文档只写到 milestone 和 phase，不提前生成 task card。
- 只有 active phase 才生成 task card。
- 单卡 phase 必须显式写入 `single_card_exception` 并说明原因。
- task card 的权威来源是 SQLite `task_cards` 表；Markdown 只作为自动导出的人工快照。
- task card 不得只是任务清单，必须包含 goal、write_set、read_set、test commands、acceptance、evidence requirements、blocking conditions、risk level、model guidance 和 expected artifacts。
- 每个 active phase 默认只导出一份 `state/<milestone_phase>/task_cards.md` 或 `state/task_cards/<run_id>/task_cards.md`；不要生成大量散装 task card 文档。
- 每个 phase 前运行并保存 `plan-graph`、`policy-preview`、`goal-packet`。
- 每个 phase 至少输出 task cards、route evidence、test evidence、operator packet 和 closeout summary。
- 成功 phase 可以 1 phase 1 commit；失败 phase 不提交，只保留 evidence 和恢复指针。

## Bug-First 规则

workflow、dogfood、receipt、probe、evidence、route、repo mutation、test matrix 任一路径出现 bug 时，暂停业务 phase：

1. 生成 workflow bug task card。
2. 修复 workflow bug。
3. 补回归测试。
4. 再恢复原 phase。

## 路由默认值

- OpenAI API 当前不是已配置主路径；OpenAI-family coding 真实入口是 Codex CLI。
- MiniMax / DeepSeek API 可以直接生成 plan、review、patch proposal；需要写仓库时必须通过受控 patch apply。
- simple 杂活：OpenCode + `minimax/MiniMax-M2.7`。
- medium review / validation：DeepSeek V4 Flash，失败直接 fallback Codex。
- complex 架构、安全协议、repo mutation：Codex CLI 或本地补丁兜底。
- MMX/MiniMax 的主要价值是 image / speech / music / future video 资产生成，不是只做文本 evidence。
- Vertex 生成能力走 API/SDK；`gcloud` 只是 Vertex/GCP 认证与环境工具。
- Cloud Text-to-Speech 使用 `gcp_tts_api`；旧 `vertex_tts` 只作为兼容 alias。
- Gemini CLI 暂不接入；Gemini-family 能力短期通过 Vertex/GCP。
- LangChain 是 experimental / opt-in agent framework，不进入默认主路由。

## Capability Truth

- Capability health 必须来自 runtime ledger / live probe，而不是 descriptor 自我声明。
- `verified_ready` 或 `recently_successful` 只能由真实 provider-specific live proof 产生。
- simulated、dry-run、generic greeting、fallback-only、非真实调用不能标记为 ready。
- text evidence、coding proposal、asset generation 必须分开声明。
- 生成类能力必须有真实二进制 artifact、mime、hash 和 evidence。

## 高风险动作边界

以下动作必须使用 scope-bound `OperatorActionReceipt` 或明确的 `AutomationLease`，并在消费时校验实际 request scope：

- `launch_execute`
- `resume_run`
- `approve_run`
- `reject_run`
- `cancel_run`
- `batch_resume_runs`
- repo mutation / patch apply
- watchdog auto-apply
- git commit / push / PR

GET 请求不得触发状态变更。所有文件写入必须解析明确 workspace root。

## Pipeline 规则

- `WorkflowPipeline` 是 `OrchestrationPlan` 之上的 plan-of-plans，不是 cluster 的别名。
- Pipeline preview 不直接 mutation。
- Pipeline run 必须写 stage evidence。
- 未真实执行的 capability stage 必须返回 `blocked`，不得伪装 `completed`。
- 未真实执行的 `agent_role` / `cluster` stage 必须返回 `stubbed` 或 `blocked`，不得伪装 `completed`。
- 后续 `cluster` 不再扩展为独立执行引擎；它只表示角色/能力模板。真正多角色执行应由 LangGraph subgraph 承载，并继续受 workflow 的安全和证据规则约束。
- required dependency 只能由 `completed` 满足；`skipped` 只能满足显式 optional dependency。
- validation command 必须使用 `packages/runtime_security/safe_command_runner.py` 的安全 argv runner，默认 `shell=False`，不得通过 shell metacharacter 绕过审核。
- validation/capability 失败后必须短路后续 stage。
- 复杂写入仍走既有 run/control-plane、receipt/lease、write_set 和 repo mutation 语义。

## Core Domain 边界

- `packages/core_domain` 只应包含 control plane、receipt/lease、workspace/write_set、provider truth、evidence/governance、generic pipeline contract 等通用核心能力。
- Cocos/H5/game executor、commercial asset generator、业务 pipeline template、垂直 QA/playtest runner 不应新增到 `core_domain`。
- 兼容 shim 必须写明 `remove_after_milestone`，默认不晚于 M89，并禁止新代码继续依赖旧路径；延期必须以 shim 命中率或下游迁移 evidence 支撑。
- M105.1 启动前必须先运行 `rg -n "remove_after_milestone" . -g "!state/**"`。如果命中生产 shim，必须先删除，或写明延期 milestone、理由和验证证据；不能把过期 shim 带进新的 Cocos 开发。
- LOC 纪律使用 production/core/file ratchet，不用包含 tests 的总 LOC 作为唯一硬门禁。

## LangGraph 收敛规则

- LangGraph 适合承担状态机、checkpoint/resume、human interrupt、multi-agent/subgraph、repair loop 和 graph observability。
- LangGraph 不得绕过 `OperatorActionReceipt`、`AutomationLease`、workspace root、write_set audit、provider live proof 或 evidence/operator packet。
- M104 后的默认方向是：能用 LangGraph 承载的状态推进、checkpoint、人审暂停、subgraph、repair loop 和 stream evidence，优先用 LangGraph。
- 短期目标不是让 LangGraph 接管全部控制面，而是让 graph-backed executor 服务于 workflow 的安全和证据规则。
- `workflowctl run ...`、`pipeline preview/run`、`capability probe/health`、`test matrix` 必须保持兼容。
- graph-backed phase 仍必须遵守 plan / milestone / phase / task card 四层语义。
- `WorkflowGraphState` 不得成为绕过 workflow 的权威状态源；它必须继续服务于 `OrchestrationPlanGraph`、`WorkflowPipeline` 和 run lifecycle 的关系。
- cluster 与 LangGraph subgraph 的分工是：cluster 定义“需要哪些角色、各自负责什么、何时升级为多人协作”，LangGraph subgraph 定义“这些角色如何执行、交接、审阅和收敛”。旧 cluster runtime 不作为新的主执行路径继续加功能。

## 商业化 Cocos 游戏规则

商业化 H5/Cocos 游戏是正式业务需求，应作为 pipeline 场景承载，而不是新增一堆 `game_*_cluster`。

必须区分：

- 技术 smoke：工程能生成、构建能跑。
- E2E scaffold：有 Cocos 工程、资产绑定和自动试玩 evidence。
- 商业化可玩成品：真实 UI、可用面板、玩法闭环、关卡流程、皮肤/画廊、音频设计、动效反馈、移动端体验都达到玩家可接受标准。

当前结论：

- M78/M79/M83 证明了 Cocos 项目生成、asset factory、Web Mobile build、browser playtest 和 pipeline 模板可以跑通。
- M84 真实试玩反馈确认：当前产物仍是样机级，不具备商业化可玩质量。
- `workflowctl game cocos-e2e --require-commercial` 和 `commercial_game_production` final gate 不能继续只看状态变量或事件覆盖。
- 后续 gate 必须输出 `technical_smoke_go`、`production_scaffold_go`、`commercial_playable_go` 三层结论；`--require-commercial` 必须绑定玩家视角的 `commercial_playable_go`，而 `--require-cocos-ecosystem`、`--live-agent-roles`、`--require-human-player-review` 缺证据时只能 blocked/failed。
- Cocos ecosystem bridge 现在已有项目内 Editor extension 包、unattended runner、trusted report contract 和 license/cost manifest；本地 smoke `cocos_bridge_smoke_20260429_145028` 已证明 Editor/AssetDB/Scene/Prefab/Build API report 可回传并满足 `ecosystem_integration_go`。这只代表本地 Cocos Editor 生态桥接完成，不代表商业游戏本体完成。
- 后续修复重点是可玩性与玩家视角质量，而不是再生成更多 manifest。

## 验证规则

文档变更至少运行：

```powershell
python -m infra.scripts.check_doc_links
```

涉及运行路径、API、UI、验证脚本或活跃真相源时追加：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite unit
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite core
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite integration
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" validation run --suite full --skip-offline-probe
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider all --require-live --evidence-dir state/<milestone>/capability_probes
python -m pytest -q
```

## 卫生清理规则

- `state/` 是生成态目录，默认不进入 Git；工作树只应保留 `.gitkeep`、必要的本地 `workflow.db` 和正在使用的短期 evidence。
- 大型 Cocos 工程、APK/HTML 包、pytest 临时目录、旧 evidence、离线验证 scratch DB 都应按需清理。
- `state/.pytest-tmp-workflow/` 是测试临时工作区；`workflowctl test matrix` 成功后会自动删除本次 pytest 临时目录，不影响 `workflow.db`。
- 测试失败时默认保留本次临时目录，方便排查；下一次测试会按 24 小时 TTL 和 256MB 上限清理旧目录。
- 如需临时保留所有测试产物，设置 `WORKFLOW_KEEP_TEST_TEMP=1`；如需调整阈值，使用 `WORKFLOW_TEST_TEMP_TTL_HOURS` 和 `WORKFLOW_TEST_TEMP_MAX_MB`。
- 清理文件不等于清理功能。商业化游戏 pipeline 代码、测试和说明继续保留。
- 删除递归目录前必须确认目标解析后仍在当前 workspace 或明确目标目录内。

## 下一阶段开发计划

- M105-M108 已完成并收口。
- M108.5 review 决策报告见 `docs/evaluations/m108_5_review_decision.md`。
- M108.5 已开始把 task card 权威源迁回数据库；Markdown 保留为快照，不再承担机器真相。
- Cocos 当前投入预算到 M108 已用完；M109 不得解释为“继续无限做游戏”，而是一次有边界的管线试运行：先解决输入整理、角色思考、任务交付、资产生成、玩家审阅和 gate 诚实性。
- M85-M90、M91-M98、M99-M104 已压缩进 `docs/milestone_history.md` 和 `docs/architecture/langgraph_runtime_notes.md`，不再保留根目录散装计划书。
- 范围：用现有 LangGraph-backed 底座和 workflow 控制面，先让 `agent_role` / 单 agent 角色阶段真实产出方案、资料包、task card、资产需求和审阅结果；Cocos 只作为试运行场景。
- 当前入口：M109 从“统一资料包 + 单 agent 角色管线试运行”开始；真实生产管线为 `commercial_game_production`，旧 `m109_single_agent_cocos` 只保留为兼容别名；active phase 开始后才生成 task card，不提前生成未来 phase 的 task card。
- 暂不纳入：Gemini CLI、视频生成、GitHub 自动化、Hugging Face Jobs、远程 worker 扩展、托管 SaaS、广告 SDK 和 IAP。
- active phase 开始后才生成 task card；phase closeout 必须包含 workflow 实际执行范围、Codex 兜底范围和 evidence。

### Acceptable Detours

M109 以真实工程管线打磨为主线，但不能冻结 workflow 和 LangGraph 底座。每个 milestone 最多允许 1 个 detour，且只能用于：

- workflow bug、receipt/lease、repo mutation、pipeline truth、active truth、provider live proof、安全 command runner、LangGraph runtime blocker。
- 会阻塞当前 milestone 的测试矩阵、evidence、operator packet 或 repair loop 问题。

detour 必须写明原因、范围、write_set、测试命令和 closeout。detour 不能引入新的业务路线，也不能提前生成非 active phase 的 task card。

### M109：统一资料包 + 单 Agent 角色管线试运行

M109 的目标不是直接继续堆 Cocos 功能，也不是全面重构 cluster，而是先把真实工程链路中缺失的“输入整理、角色思考、任务交付、多模态资产、玩家审阅和停止判断”补成可执行管线。

M109 的默认链路：

```text
杂乱输入
→ 统一项目资料包
→ 单 agent 角色链路
→ 高质量 task card
→ workflow worker / capability executor 执行
→ QA / 玩家视角审阅
→ validator / gate
→ supervisor 判断继续、修复、停止，或是否升级 cluster
```

M109 的边界：

- 原始材料不直接丢给各 agent；各 agent 读取整理后的统一资料包和自己的 agent packet。
- 整合阶段不做降级摘要，只做整理、分节、细化、归类和来源标注。
- cluster 先降格为单 agent；只有试运行证明某个单 agent 反复薄弱，才把该角色升级为 cluster template，并用 LangGraph subgraph 执行，而不是回到旧 cluster runtime。
- 多模态 agent 是角色，不是具体模型；图片、语音、音乐和视觉审查按能力类型走 API 主路由。
- supervisor 只做过程监督和停止/修复/升级判断，不接管 workflow 控制面，不绕过 receipt、lease、write_set、provider live proof、evidence 或 gate。

#### M109.0：Pipeline Truth Calibration

- 盘点当前 pipeline 中哪些 stage 真实执行，哪些 `agent_role` / `cluster` stage 仍是 `stubbed` 或 `blocked`。
- 入口命令：`workflowctl pipeline truth-report --template commercial_game_production`。
- 输出 `pipeline_truth_report` 和 `stubbed_stage_inventory`，明确 M109 的实际改造边界。
- 验证 task card 数据库仍是权威源，Markdown 只作为快照导出。
- closeout 必须说明 Cocos 在 M109 中只是试运行场景，不是自动续期的业务主线。

#### M109.1：Unified Project Brief

- 新增 intake / context packaging 层，把 PDF、MD、TXT、DOCX、XLSX、图片和用户 brief 转成统一项目资料包。
- 入口命令：`workflowctl intake package --input <file-or-dir> --output-dir state/<run>/brief_bundle`。
- 文字材料整合进 `project_brief.full.md`，保留完整内容；不允许只保留摘要或截断后的 `excerpt` 作为工作真相。
- 图片和媒体文件存文件系统并按 hash 去重；数据库只存元信息、OCR/多模态描述、来源关系、agent 分发记录和 hash。
- 统一资料包至少包含 `media_manifest`、`source_index`、`intake_manifest` 和每个角色的 agent packet。
- 原始文件可以作为证据和回查入口，但不能成为后续文本 agent 的唯一输入。

#### M109.2：Single-Agent Role Protocol

- 将原 cluster 能力先降格为单 agent：产品玩法、UI/体验、技术方案、多模态生成、task card 生成、QA/玩家视角和 supervisor。
- 入口开关：`workflowctl pipeline run ... --execute-agent-roles`；默认仍把未显式执行的角色 stage 记为 `stubbed`，避免伪装完成。
- 试运行预览：`workflowctl pipeline preview --template commercial_game_production`，旧 `m109_single_agent_cocos` 只保留为兼容别名。
- 建立角色输入、输出、证据和失败格式；角色输出必须是结构化 artifact，不是纯聊天记录。
- 建立角色默认模型档位：supervisor、技术方案和 task card 生成使用强模型；产品、UI、多模态文本判断和 QA 使用中强模型；执行 worker 按任务难度路由；validator 优先使用规则和测试。
- 用户不需要逐个指定每个 agent 的模型；只需要选择质量/速度/成本偏好，或在必要时显式覆盖某个角色。

#### M109.3：Design And Planning Execution

- 让之前占位的策划、设计和方案 stage 真实执行。
- 产品玩法 agent 输出玩法目标、核心循环、关卡/成长和验收口径。
- UI/体验 agent 输出界面流程、面板、移动端体验、可点击路径和玩家反馈要求。
- 技术方案 agent 输出 Cocos 工程结构、文件边界、实现顺序、风险和测试计划。
- 多模态生成 agent 输出资产清单、风格要求、生成优先级和视觉/音频 QA 要求。

#### M109.4：Multimodal API Lane

- 多模态 agent 负责提出资产需求和验收要求，不直接自由选择 provider。
- 默认主路由：图片/UI视觉/角色道具背景走 MiniMax/MMX Generation API；语音走 MiniMax Speech API，必要时 GCP TTS fallback；音乐/音效走 MiniMax Music API；截图审查和视觉 QA 走 Vertex/Gemini visual review API。
- MMX CLI 只保留为兼容、探测和临时证据通道，不作为商业化资产生成主路由。
- 每个生成物必须记录 `artifact_path`、`provider`、`model`、`mime_type`、`sha256`、`prompt_hash`、失败原因和 evidence。

#### M109.5：Task Card Quality Gate

- task card 仍写入 SQLite 权威表，Markdown 只导出 active phase 快照。
- 每张 task card 必须包含 `goal`、`read_set`、`write_set`、`test commands`、`acceptance`、`evidence requirements`、`blocking conditions`、`risk level`、`model guidance` 和 `expected artifacts`。
- task card 生成 agent 必须引用统一资料包和角色输出，不能只把 phase 拆成任务清单。
- 只有 active phase 生成 task card，不提前生成未来 phase 的 task card。

#### M109.6：Cocos Trial Run

- 用一个小目标 Cocos/H5 游戏跑完整链路，验证统一资料包、单 agent 方案、task card、多模态资产、执行 worker、QA 和 gate 是否能接上。
- 重点不是宣称商业化完成，而是验证管线是否比旧链路更会理解、拆解、执行、审阅和返工。
- 试运行必须诚实输出 `technical_smoke_go`、`production_scaffold_go`、`commercial_playable_go`，缺少真实玩家视角 evidence 时不得声明商业化可玩。

#### M109.7：Cluster Upgrade Review

- 根据试运行结果决定哪些单 agent 需要升级为 cluster template + LangGraph subgraph。
- 如果 UI/体验反复弱，升级 UI/体验 cluster template；如果多模态反复弱，升级多模态 cluster template；如果 QA 反复漏问题，升级玩家视角 QA cluster template；如果技术拆分反复错，升级技术方案 cluster template。
- 未暴露明显问题的角色继续保持单 agent，避免提前复杂化。
- closeout 必须给出 `cluster_upgrade_decision`，并说明继续、暂停、外部评估或进入 M110 的理由；任何升级都必须声明对应 subgraph 执行边界、输入输出和 gate。

M109 验收标准：

- 杂乱输入能变成统一资料包，长文字不会被截断降级为唯一工作真相。
- `agent_role` stage 不再只是 `stubbed`，关键角色能产出真实结构化方案。
- task card 质量提升，且权威来源仍是数据库。
- 多模态资产走 API 生成并保存可验收 evidence。
- workflow worker / capability executor 能消费资料包、角色输出和 task card。
- QA/gate 能诚实判断 GO / NO-GO，supervisor 能判断继续、修复、停止或升级 cluster。
# M109 Status Update (2026-04-27)

- Accepted baseline: `M109`.
- M109 is complete: unified project brief, single-agent roles, design/planning outputs, multimodal route truth table, DB task-card quality gate, bounded Cocos technical-smoke trial, and cluster-upgrade review all have evidence.
- Cocos M109 result: `technical_smoke_go=true`, `production_scaffold_go=true`, `commercial_playable_go=false`.
- Do not describe M109 as a commercial playable game delivery. It is a pipeline and technical-smoke milestone.
- Cluster decision: keep single-agent roles. Upgrade only if later evidence shows a specific role repeatedly fails.
- Next work must start with a new active phase and DB-backed task cards; do not auto-create M110 task cards from this document.
