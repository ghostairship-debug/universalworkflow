# 当前开发工作流

## 当前版本说明

- 当前工作状态：M105-M108 Cocos 真实工程接入计划。
- 接受实现基线：M104 的本地 LangGraph 运行时、SQLite checkpoint、interrupt/resume、repair loop、subgraph/supervisor 探针、stream evidence、Studio graph 配置和 Cocos graph pressure test。
- 当前纠偏：LangGraph 底座已经可用于后续开发；当前重点转向 Cocos 真实工程能力和玩家视角验收，但仍不能把技术 smoke 宣称为商业化成品。
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
- required dependency 只能由 `completed` 满足；`skipped` 只能满足显式 optional dependency。
- validation command 必须使用 `packages/runtime_security/safe_command_runner.py` 的安全 argv runner，默认 `shell=False`，不得通过 shell metacharacter 绕过审核。
- validation/capability 失败后必须短路后续 stage。
- 复杂写入仍走既有 run/control-plane、receipt/lease、write_set 和 repo mutation 语义。

## Core Domain 边界

- `packages/core_domain` 只应包含 control plane、receipt/lease、workspace/write_set、provider truth、evidence/governance、generic pipeline contract 等通用核心能力。
- Cocos/H5/game executor、commercial asset generator、业务 pipeline template、垂直 QA/playtest runner 不应新增到 `core_domain`。
- 兼容 shim 必须写明 `remove_after_milestone`，默认不晚于 M89，并禁止新代码继续依赖旧路径；延期必须以 shim 命中率或下游迁移 evidence 支撑。
- LOC 纪律使用 production/core/file ratchet，不用包含 tests 的总 LOC 作为唯一硬门禁。

## LangGraph 收敛规则

- LangGraph 适合承担状态机、checkpoint/resume、human interrupt、multi-agent/subgraph、repair loop 和 graph observability。
- LangGraph 不得绕过 `OperatorActionReceipt`、`AutomationLease`、workspace root、write_set audit、provider live proof 或 evidence/operator packet。
- M104 后的默认方向是：能用 LangGraph 承载的状态推进、checkpoint、人审暂停、subgraph、repair loop 和 stream evidence，优先用 LangGraph。
- 短期目标不是让 LangGraph 接管全部控制面，而是让 graph-backed executor 服务于 workflow 的安全和证据规则。
- `workflowctl run ...`、`pipeline preview/run`、`capability probe/health`、`test matrix` 必须保持兼容。
- graph-backed phase 仍必须遵守 plan / milestone / phase / task card 四层语义。
- `WorkflowGraphState` 不得成为绕过 workflow 的权威状态源；它必须继续服务于 `OrchestrationPlanGraph`、`WorkflowPipeline` 和 run lifecycle 的关系。

## 商业化 Cocos 游戏规则

商业化 H5/Cocos 游戏是正式业务需求，应作为 pipeline 场景承载，而不是新增一堆 `game_*_cluster`。

必须区分：

- 技术 smoke：工程能生成、构建能跑。
- E2E scaffold：有 Cocos 工程、资产绑定和自动试玩 evidence。
- 商业化可玩成品：真实 UI、可用面板、玩法闭环、关卡流程、皮肤/画廊、音频设计、动效反馈、移动端体验都达到玩家可接受标准。

当前结论：

- M78/M79/M83 证明了 Cocos 项目生成、asset factory、Web Mobile build、browser playtest 和 pipeline 模板可以跑通。
- M84 真实试玩反馈确认：当前产物仍是样机级，不具备商业化可玩质量。
- `workflowctl game cocos-e2e --require-commercial` 的验收门禁必须升级，不能继续只看状态变量或事件覆盖。
- 后续 gate 必须输出 `technical_smoke_go`、`production_scaffold_go`、`commercial_playable_go` 三层结论；`--require-commercial` 必须绑定玩家视角的 `commercial_playable_go`。
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
- `state/.pytest-tmp-workflow/` 是测试临时工作区；测试后可以整目录删除，不影响 `workflow.db`。
- 清理文件不等于清理功能。商业化游戏 pipeline 代码、测试和说明继续保留。
- 删除递归目录前必须确认目标解析后仍在当前 workspace 或明确目标目录内。

## 下一阶段开发计划

- M105-M108 是当前活跃方案。
- M85-M90、M91-M98、M99-M104 已压缩进 `docs/milestone_history.md` 和 `docs/architecture/langgraph_runtime_notes.md`，不再保留根目录散装计划书。
- 范围：用 LangGraph-backed 底座推进 Cocos command、构建配置、工程检查、真实 UI/Prefab、浏览器试玩和玩家视角验收。
- 暂不纳入：Gemini CLI、视频生成、GitHub 自动化、Hugging Face Jobs、远程 worker 扩展、托管 SaaS、广告 SDK 和 IAP。
- active phase 开始后才生成 task card；phase closeout 必须包含 workflow 实际执行范围、Codex 兜底范围和 evidence。

### M105：Cocos 真实工程底座

- M105.1：Cocos command 与构建配置真相，明确命令、配置文件、项目路径、输出路径和失败证据。
- M105.2：Cocos project inspector v2，检查真实工程结构、场景、脚本、资源、Prefab/Panel、构建配置和入口场景。
- M105.3：运行方式与交付方式真相，区分 HTTP 服务运行、双击 HTML、移动端预览和打包说明。
- M105.4：Cocos graph evidence bridge，把生成、检查、构建、试玩和修复接入 graph evidence，同时保留 workflow 安全规则。

### M106：Cocos 原生内容生产

- M106.1：UI/Panel/Prefab 生产约束，覆盖开始、暂停、结算、设置、皮肤、画廊和复活等界面。
- M106.2：场景、Prefab 与资源绑定，把场景、Prefab、脚本和资源关系写成可检查的工程事实。
- M106.3：本地稳定资产包，确保没有外部 API 时也能产出稳定样机。
- M106.4：玩法交互与反馈入口，补齐点击、拖拽、关卡目标、解锁、音效和动效反馈。

### M107：玩家视角验收

- M107.1：浏览器试玩证据，补充桌面与移动视口截图、事件、控制台、加载、画布和可见 UI 证据。
- M107.2：面板与流程验收，验证开始、暂停、结算、设置、关卡、皮肤、画廊等流程真的可见可点。
- M107.3：音频、动效与移动端体验，检查突兀音效、动效反馈、遮挡、按钮可点性和文字溢出。
- M107.4：商业化 GO/NO-GO 重分层，继续区分 technical smoke、production scaffold 和 commercial playable。

### M108：真实样机闭环

- M108.1：样机目标与验收口径，选一个小目标并写清玩法、界面、资产、运行方式和 GO/NO-GO。
- M108.2：真实工程生成，用 M105/M106 的能力生成项目并保存 evidence。
- M108.3：构建、试玩与修复循环，用 M107 验收；发现问题进入 repair loop。
- M108.4：关闭报告，诚实说明哪些能力已成、哪些只是样机、哪些还不能宣称商业化可玩。

建议起点是 M105.1。原因很简单：如果 Cocos 命令、构建配置、输出目录和失败证据不够真，后面的 UI、Prefab、试玩验收都会继续踩空。
