# AGENTS.md

## M109 Update (2026-04-27)

- Accepted baseline is now `M109`.
- M109 completed the unified project brief, single-agent role pipeline, design/planning role outputs, multimodal route truth table, DB-backed task-card quality gate, bounded Cocos technical-smoke trial, and cluster-upgrade review.
- Cocos result is `technical_smoke_go=true` and `production_scaffold_go=true`, but `commercial_playable_go=false`; do not claim commercial playable completion without build/playtest/player-visible evidence.
- Cluster decision: keep roles as single agents for now. Upgrade only a specific role later if repeated evidence shows the single-agent role is failing.
- Do not auto-create M110 task cards. Future work must open a new active phase first.

## 2026-04-28 Correction

- `commercial_cocos_game` fixed-template delivery is removed as an executable path; it must block with `legacy_cocos_template_removed`.
- Real commercial game work must use `commercial_game_production`, driven by unified brief, role outputs, DB task cards, real assets, task-card worker implementation, player QA, supervisor, and final gate.
- Low-level Cocos scaffold/E2E commands remain diagnostics only and cannot prove or deliver a commercial game.

## 当前基线

当前接受实现基线是 `M109`：统一资料包、单 agent 角色管线、设计/方案输出、多模态路由真相表、DB task-card quality gate、有限 Cocos technical-smoke trial 和 cluster-upgrade review 已落地。M108 Cocos 小目标样机闭环保留为历史基线。

商业化 Cocos 游戏生成是正式需求，相关功能和 pipeline 必须保留并继续优化；但最近一次真实生成结果质量不足，不能宣称“完整商业化游戏已完成”。

当前主线是 M109 后 `commercial_game_production` 无降级修复：不得自动进入 M110 或提前生成未来 phase task card，也不得把 technical smoke / production scaffold 解释为商业化可玩完成。LangGraph 可以承接状态推进、checkpoint、人审暂停、subgraph、多 agent 和 repair loop；workflow 仍负责 receipt、lease、write_set、provider live proof、evidence 和 operator packet。

本仓库是个人自用、本地优先的 agentic workflow runtime，不是公开 SaaS、多租户平台、插件市场、自动 PR 发布器或外部托管执行服务。

## 开发规则

- 优先读取 `README.md`、`CURRENT_DEVELOPMENT_WORKFLOW.md`、`docs/milestone_history.md` 和 `docs/governance/tech_debt_registry.json`。
- 当前活跃开发方案见 `CURRENT_DEVELOPMENT_WORKFLOW.md` 的“下一阶段开发计划”。
- M85-M90、M91-M98、M99-M104 只在 `docs/milestone_history.md` 和 `docs/architecture/langgraph_runtime_notes.md` 中保留压缩摘要，不再保留根目录散装计划书。
- `packages/core_domain` 不应新增 Cocos/H5/game executor、commercial asset generator、业务 pipeline template 或垂直 QA/playtest runner；需要兼容 shim 时必须写明 `remove_after_milestone`。
- pipeline stage truth 必须区分 `completed / blocked / failed / skipped / stubbed / simulated`；未真实执行、无 provider proof 或无 evidence contract 的 stage 不得标记 completed。
- validation command 默认必须走 `packages/runtime_security/safe_command_runner.py` 的安全 argv runner 和 `shell=False`；required dependency 不得由 skipped stage 满足。
- plan / milestone / phase / task card 必须保持四层语义：一个 plan 包含多个 milestone；一个 milestone 包含多个 phase；一个 phase 默认包含多个 task card；task card 是最小可执行单元。
- 开发计划文档只写到 milestone 和 phase，不提前生成 task card；只有 active phase 才生成 task card。
- 不要把“一 phase = 一 task card”当作默认模式。若某 phase 只有一张 task card，必须写明 `single_card_exception`。
- task card 的权威来源是数据库 `task_cards` 表；Markdown 只是自动导出的人工审阅快照，不再作为长期真相源。
- active phase 的 task card 不能只是任务清单，必须至少包含：目标、write_set、read_set、测试命令、验收标准、证据要求、阻塞条件、风险等级、模型执行提示和预期产物。
- phase 级 operator packet 必须汇总该 phase 内所有 task card 的 write_set、test commands、evidence 和阻塞项。
- 简单低风险任务优先通过 `workflowctl run from-task-card ... --adapter opencode --execute` 走 workflow；复杂安全协议和架构切片可以使用 Codex 或本地补丁兜底。
- bug-first：workflow、receipt、probe、evidence、route、repo mutation、test matrix 任一路径出 bug，先修 workflow bug 并补测试，再继续原 phase。
- `workflowctl test matrix` 成功后会自动清理本次 `state/.pytest-tmp-workflow/` 临时目录；失败时默认保留现场。需要保留全部测试产物时设置 `WORKFLOW_KEEP_TEST_TEMP=1`。
- 成功 phase 可以 1 phase 1 commit；不要把多个 phase 或多个 milestone 压成一个 commit，除非用户明确要求一次性收口提交。

## 高风险动作边界

以下动作必须由统一策略判断后才能执行：

- `launch_execute`
- `resume_run`
- `approve_run`
- `reject_run`
- `cancel_run`
- `batch_resume_runs`
- repo mutation / patch apply
- watchdog auto-apply
- git commit / push / PR

高风险动作必须使用 scope-bound `OperatorActionReceipt` 或明确的 `AutomationLease`。GET 请求不得产生状态变更；`execute=true` 不得绕过 receipt 或 lease。

## Provider 真实性

- 已接入：Codex、OpenCode、Claude、MMX/MiniMax、Vertex/GCP、LangChain、Shell/Noop。
- OpenCode 默认 simple lane 使用 `minimax/MiniMax-M2.7`。
- medium lane 可使用 `deepseek/deepseek-v4-flash`，失败时直接 fallback Codex。
- Gemini CLI 暂未接入；Gemini-family 能力当前通过 Vertex/GCP。
- `gcloud` 是 Vertex/GCP 凭据与环境工具，不是独立 worker adapter。
- LangChain 是 experimental / opt-in agent framework，不是默认 provider control plane。
- capability readiness 只接受 provider-specific live proof。simulated、dry-run、generic greeting、fallback-only、非真实调用都不能标记为 `verified_ready`。

## Game Pipeline 真实性

- H5/Cocos 商业化游戏是正式业务需求，不是示例 demo，也不应从代码中删除。
- 技术 smoke、E2E scaffold、商业化可玩成品必须分开记录。
- 不得把 `commercial_go_no_go=GO`、feature flag、canvas 非空、浏览器事件覆盖、HTML/APK 打包成功写成“完整商业化游戏已生成”。
- 最近一次 M84 真实生成暴露了成品质量缺口：UI 原始、面板不可用、关卡切换浅层、音频体验突兀、双击 HTML 不可直接运行。
- 后续商业化修复要优先补：玩家视角验收、真实 UI/Prefab/Panel、关卡目标与解锁、皮肤/画廊交互、音频设计、动效反馈、HTTP/双击运行说明或封装。
- 半成品可以作为 evidence，但不能标记为 final commercial ready。

## 并发与编排

- 每个 phase 前运行 `plan-graph`、`policy-preview`、`goal-packet`。
- artifact-only 和 disjoint write_set task card 可以并发，最多 `batch-resume --max-workers 2`。
- write_set conflict、dirty write_set、SQLite lock 或 repo mutation 异常时必须降级串行。
- 复杂能力开发仍要保留 workflow route/evidence/operator-packet，即使实现由 Codex 或本地补丁完成。
- LangGraph 可以承接状态推进、checkpoint、人审暂停、multi-agent/subgraph 和 repair loop，但不得绕过 receipt、lease、write_set、provider live proof 或 evidence/operator packet。
- 每个 active phase 最多导出一份 `state/<milestone_phase>/task_cards.md` 或 `state/task_cards/<run_id>/task_cards.md` 快照；不要为每张 task card 生成散装长期 Markdown。
