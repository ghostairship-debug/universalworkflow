# 商业小游戏 Pipeline 与 Workflow-Wide 修复开发文档 - 2026-04-28

## 文档目的

本文档是 2026-04-28 之后继续开发的执行入口，承接：

- [Commercial Game Pipeline Handoff](commercial_game_pipeline_handoff_2026_04_28.md)
- [当前开发工作流](../../CURRENT_DEVELOPMENT_WORKFLOW.md)
- [Commercial Game Pipeline Evaluation 2026-04-28](../evaluations/commercial_game_pipeline_evaluation_2026_04_28.md)
- [技术债登记](../governance/tech_debt_registry.json)

目标不是新开一个平行真相源，而是把当前聊天中已经收束的要求转成下一轮 workflow 开发的 milestone / phase 级计划。本文档不生成 task card；只有 active phase 打开后，才允许把该 phase 拆成 DB-backed task cards。

## 当前真相

- 接受基线：`M109` 是 pipeline / technical-smoke baseline，不是商业化可玩游戏交付。
- 真实商业小游戏入口：只能使用 `commercial_game_production`。
- 旧固定模板入口：`commercial_cocos_game` 必须阻断为 `legacy_cocos_template_removed`。
- Cocos Creator 已确认安装在 `C:\ProgramData\cocos\editors\Creator\3.8.8\CocosCreator.exe`；之前缺失结论来自 pipeline 未自动发现安装路径的 bug，该 bug 已修复。
- OpenCode 和 Codex CLI 都可被本机调用；旧 180s 无 patch 不是“CLI 不存在”，而是长程 patch 任务缺少 progress-aware watchdog，超时后只留下失败结果。
- MiniMax/MMX 当前有 image / speech / music 集成；短游戏 SFX 已从 speech/TTS 路线拆出，本地 `procedural_sfx_local` 可作为商业默认微型音效方案，只要 artifact QA gate 通过。它不是 placeholder，也不替代后续 premium SFX/provider 评估。
- 当前 Cocos 连接能力已从 `CLI 构建 + 文件系统工程生成 + E2E/browser playtest + graph/evidence bridge` 扩展到 project-local Editor extension 包、trusted bridge report contract、license/cost manifest 和 filesystem-only report rejection；这仍不等于生态接入完成。真实 Editor API 回传、AssetDB、Scene/Prefab、Build API、插件或 MCP bridge 操作仍是正式后续目标。

## 2026-04-28 执行进展

- Milestone A 的当前阻塞项已修复并回归：progress-aware watchdog、Codex/OpenCode 默认路由、receipt scope/propagation、repo mutation evidence、scheduler lease terminal release、stale lease repair、remote callback idempotency和 heartbeat evidence 均有测试覆盖。
- Milestone B 的短音效路径已通过 workflow task-card 执行：`voice` / `music` / `sfx` modality 分离，`sfx_place` / `sfx_clear` 使用 `procedural_sfx_local` WAV artifact，记录 mime、sha256、duration、RMS/peak、non-silent、clipping、provenance 和 QA gate。
- Milestone C 尚未完成：当前 Cocos 能力已有 Editor extension 包和 evidence contract，但缺真实 Editor/AssetDB/Scene/Prefab/Build API report，local MCP server 和生态资产许可/成本评估仍必须作为后续 capability phase 处理。
- Milestone D 的本轮 business 补全通过 DB task card / workflow-controlled execution 完成；后续业务修改仍必须继续遵守 receipt/lease/write_set/evidence。
- No-degradation 纠偏后，`pipeline_a41e231c69a4` 只作为 gate v1 automated scaffold/build/playtest 历史证据保留。当前严格真相是 `zero_degradation_cocos_worker_rerun4_20260429`：`commercial_game_no_degradation_failed`，不得声明 `commercial_playable_go=true`。该 run 中 real assets 和 live role proof 通过，但同项目 task-card patch 触发 `provider_idle_timeout`，真实 Editor bridge report、人审和产品深度仍缺失。

## 总原则

### Bug-First

任何 workflow、receipt、probe、evidence、route、repo mutation、test matrix、adapter、API/MCP provider、长程 watchdog 问题，都先暂停业务 pipeline / game 开发：

1. 记录 workflow bug。
2. 生成 active phase 内的 DB task card。
3. 先修 workflow bug。
4. 补回归测试。
5. 重跑验证。
6. 再恢复商业 pipeline 补全。

Codex 直接手改只允许用于 workflow 基础设施 bug-first 修复。商业 pipeline 功能补全必须回到 workflow/task card/receipt 执行。

### 高风险动作

以下动作继续要求 scope-bound `OperatorActionReceipt` 或明确 `AutomationLease`：

- `launch_execute`
- `resume_run`
- `approve_run`
- `reject_run`
- `cancel_run`
- `batch_resume_runs`
- repo mutation / patch apply
- watchdog auto-apply
- git commit / push / PR

GET 请求不得产生状态变更。`execute=true` 不得绕过 receipt 或 lease。

### 长程无人值守

长程任务必须有两层 evidence：

- 外层 pipeline/run heartbeat：证明 workflow 仍在推进、可恢复、可诊断。
- 内层 provider/child process watchdog：证明 CLI/API/MCP worker 是否仍有输出、是否 idle、是否达到总时限，以及失败时保留 stdout/stderr/response 摘要。

只有外层 heartbeat 不够。若子进程 180s 内没有 patch，但仍在输出或 provider job 仍在运行，不能粗暴等同于“无结果”；必须区分 idle timeout、wall timeout、provider quota、auth、parse failure、no patch、sandbox/write denied 等失败类别。

## 已知 Blockers

### B1: CLI/Provider 执行 watchdog 仍不够精细

已确认：

- OpenCode 默认 simple lane 使用，不能作为 pipeline completion repo mutation 默认路由。
- `from-task-card` 默认 `patch_apply` 应固定走 Codex CLI enforcement。
- Codex/OpenCode 可调用，但 patch 任务可能在 180s 内无有效 patch。

2026-04-28 当前状态：

- CLI adapter 的 stream-aware watchdog 已落地，Codex/OpenCode 能区分 wall timeout 与 idle timeout，并记录 stream event count、last output age、stdout/stderr preview 和 recovery suggestion。
- API provider 需要 connect timeout、read idle timeout、total deadline、retry/backoff、job id polling/cancel 和结构化 failure evidence。
- MCP stdio/provider 也需要 idle/wall watchdog、工具调用日志、partial evidence 和 cancel/terminate 策略。
- Cocos build、安全命令、playtest 等长命令同样需要 heartbeat/idle/wall 分类。

验收要求：

- 无 receipt 时 fail fast，不启动 patch-capable worker。
- scope 不匹配的 receipt fail fast。
- 默认 `patch_apply` 不落 OpenCode。
- adapter timeout 必须写入 `failure_class`、stdout/stderr 或 API response 摘要、`mutation_result`、last output timestamp、可恢复建议。
- 长输出但未完成的进程不应被 idle timeout 杀死；无输出超过 idle 阈值才触发 idle timeout。

### B2: SFX 被错误归入 speech/audio 路线

原问题：

- `sfx_place` / `sfx_clear` 是短游戏音效，不应走 speech/TTS。
- MiniMax Speech 默认模型适合语音，不适合消耗在游戏点击/消除短音效。
- MiniMax Music 更接近 BGM；Vertex 当前路线也不是短 SFX 默认生成器。

目标修复：

- 在资产工厂中拆分 `voice`、`music`、`sfx` 三类 modality。
- `voice_reward` 走 TTS。
- `bgm_loop` 走 music/BGM。
- `sfx_place` / `sfx_clear` 走 `sfx`。
- 首选集成成熟本地 procedural SFX 方案，而不是从零写 DSP。

2026-04-28 当前状态：

- `sfx_place` / `sfx_clear` 已改为 `modality=sfx`、`provider=procedural_sfx_local`、WAV artifact。
- `voice_reward` 保持 `modality=voice` 和 TTS provider；`bgm_loop` 保持 music/BGM。
- Asset factory QA 已验证 procedural SFX 的 artifact、mime、sha256、duration、RMS/peak、non-silent、clipping、provenance 和 `qa_gate_passed`。
- Cocos resource binding 和 runtime audio hooks 已识别 `audio` / `music` / `sfx` / `voice`；后续仍需在真实商业游戏 run 中验证玩家可见音频体验。

本地方案建议：

- 优先评估 `rFXGen`、`sfxr`、`jsfxr`、`Bfxr` 这类成熟 procedural SFX 算法或工具。
- workflow 需要写 wrapper、manifest、provider evidence、音频 QA、商业 gate，而不是重写底层合成算法。
- 对点击、消除、奖励、失败等微型 SFX，`procedural_sfx_local` 可以是最终可发布资产，只要 QA 通过；不能一概标 placeholder。

验收要求：

- SFX artifact 有真实文件、mime、sha256、duration、RMS/peak、clipping 检查、non-silent 检查和 provenance。
- provider 不可用时，若 commercial policy 禁止本地 procedural 或 QA 失败，必须输出 `sfx_provider_missing` / `sfx_qa_failed`，不能降级成 speech。
- provider 选择不是“本地永远优先导致后续不触发”的死链路；应按质量档位和资产类型做编排：`dev_smoke`、`commercial_default`、`premium_release`。

### B3: Cocos 生态接入尚未完成

当前已落地能力：

- Cocos CLI build。
- 文件系统写入 Cocos 工程结构。
- 本地 scaffold / E2E 执行。
- HTTP + browser playtest。
- graph/evidence bridge。
- project-local Cocos Editor extension 包生成。
- trusted bridge report contract、license/cost manifest、filesystem-only report rejection。

尚未完成但必须进入开发计划的生态接入：

- Cocos Editor 插件桥的真实 Editor 进程执行与 report 回传。
- AssetDB / Scene / Prefab / Build Editor API 的真实操作。
- Cocos 生态市场、模板市场、扩展包或编辑器内工作流编排。
- workflow 与 Cocos Editor extension / local MCP bridge 的双向证据回传。

开发要求：

- 不要把当前 CLI/E2E 能力包装成已经完成的 Cocos ecosystem integration。
- 不要把“extension 包已生成”包装成 Editor bridge 已完成；只有真实 Editor/API report 才能满足 `ecosystem_integration_go`。
- 不要把 Cocos 方向重命名或降级为测试壳；当前能力只是阶段性接入面。
- Cocos 生态接入是 workflow-wide capability，不是商业 pipeline 局部补丁。
- 生态接入应单独开 architecture/capability phase：`workflow/pipeline -> Cocos Editor Bridge -> local MCP server or Cocos Editor extension -> AssetDB/Scene/Prefab/Build APIs -> workflow evidence`。

## 下一轮开发计划

### Milestone A: Workflow-Wide Bug-First Hardening

目标：先修复所有会阻塞无人值守、真实 provider、repo mutation 和 evidence 可信度的问题。

Phase A1: Provider Execution Watchdog Contract

- 统一 CLI/API/MCP/long command 的 idle timeout、wall timeout、stream heartbeat、partial evidence 和 failure classification。
- Codex/OpenCode adapter 必须暴露 last output、stream event count、stdout/stderr preview、timeout type、patch parse 状态。
- API provider 必须区分 auth、quota、connect、read idle、total deadline、provider response parse、empty artifact。
- MCP provider 必须记录 tool name、arguments hash、response preview、stderr/stdout、cancel/terminate 结果。

Phase A2: Route And Receipt Regression

- 证明无 receipt 不启动 patch-capable worker。
- 证明 scope-bound receipt 才能 repo mutation。
- 证明默认 `patch_apply` 固定走 Codex CLI enforcement。
- 证明 OpenCode 保留 simple lane，但不作为 pipeline completion 默认 repo mutation route。

Phase A3: Long Unattended Evidence

- 所有长程 pipeline run 写 heartbeat JSONL。
- worker lease renewal、provider child progress、pipeline stage progress 能关联到同一 run id。
- 失败 closeout 必须包含恢复命令、evidence 路径和下一步建议。

### Milestone B: Asset Modality And SFX Repair

目标：修复音频资产真实性，避免把 SFX 错路由到 TTS。

Phase B1: Audio Modality Split

- 引入或落实 `voice` / `music` / `sfx` 的清晰 contract。
- 更新 commercial Cocos asset manifest，让 `sfx_place` / `sfx_clear` 使用 `modality=sfx`。
- 旧 `audio` 路径只能作为兼容 alias，必须能够映射到具体 voice/music/sfx，否则 blocked。

Phase B2: Procedural SFX Provider

- 评估并接入成熟本地 procedural SFX 工具或算法。
- 封装为 CLI/provider 或 MCP provider；输出 workflow 可读 manifest。
- 记录 license / attribution / commercial-use 判断。

Phase B3: Audio QA And Gate

- 对 SFX/BGM/voice 分别做 duration、non-silent、peak/RMS、clipping、format、hash、provider provenance 检查。
- commercial gate 根据资产类型和质量档位判断 GO/NO-GO。

### Milestone C: Cocos Ecosystem Integration

目标：把 Cocos 从“CLI/E2E 可运行”推进到“生态能力可编排”，让 workflow 能通过受控桥接使用 Cocos Editor、AssetDB、Scene、Prefab、构建和生态资产能力。

Phase C1: Ecosystem Capability Contract

- 定义 Cocos ecosystem capability contract，区分 CLI build、Editor bridge、AssetDB、Scene graph、Prefab、Asset import、Package/extension、Playtest evidence。
- 明确每类能力的输入、输出、write_set、receipt/lease、evidence schema 和失败分类。
- 当前已落地 CLI/E2E 能力保留为基础执行面，但不得冒充 Editor/AssetDB 接入。

Phase C2: Local Editor Bridge

- 选择并验证本地桥接形态：Cocos Editor extension、local MCP server，或二者组合。
- workflow 只能通过受控 bridge 发起高风险编辑器动作，不能绕过 receipt、lease、workspace root、write_set 和 evidence。
- bridge 必须返回 provider/tool proof、Cocos Editor 版本、项目路径、操作摘要、stderr/stdout 或 editor log 摘要。

Phase C3: AssetDB / Scene / Prefab Operations

- 接入真实 AssetDB import/query。
- 接入 Scene 创建、节点查询、组件绑定和场景保存。
- 接入 Prefab 创建、实例化、资源引用和 meta 校验。
- 所有操作必须可回放、可验证，并能落到 pipeline stage evidence。

Phase C4: Ecosystem Assets And Packages

- 评估 Cocos 生态资产、模板、扩展包或本地 package 的接入方式、许可、成本和可商用边界。
- 资产进入商业 pipeline 前必须记录 source、license、hash、attribution、商业使用判断和 QA evidence。
- 付费资产、平台 SDK、广告/IAP/analytics/cloud 服务不得静默接入，必须进入 operator decision。

Phase C5: Pipeline Integration Gate

- `commercial_game_production` 可以消费 Cocos ecosystem capability，但必须诚实标记每个 stage 使用的是 CLI/E2E 能力还是 Editor/AssetDB 能力。
- 如果生态 bridge 未 ready，pipeline 可以继续跑 CLI/E2E 基础路径，但 final report 必须标注生态接入缺口。
- 不得因为生态 bridge 尚未完成而删除、弱化或降级 Cocos 商业游戏目标。

### Milestone D: `commercial_game_production` Pipeline Completion

目标：补全真实商业小游戏生产 pipeline，但所有业务代码改动必须通过 workflow/task-card/receipt 执行。

Phase D1: Active Task Card Reuse

- 复用 `TC-commercial-game-pipeline-completion` 或在 active phase 内生成新的 DB task card。
- 现有直接改动只能作为 draft patch set，由 workflow 审查、细化或替换。
- 执行前必须运行并保存 `plan-graph`、`policy-preview`、`goal-packet`。

Phase D2: Role / Task / Worker Evidence

- role stages 必须真实执行或诚实 blocked/stubbed。
- 角色输出必须是结构化 artifact，不是聊天摘要。
- DB task-card worker 必须消费 unified brief、role outputs 和 acceptance。
- repo mutation 必须由 scope-bound receipt 或 lease 授权。

Phase D3: Same-Project Repair Loop

- pipeline repair 必须修改同一个目标工程，不能每轮重建模板工程掩盖问题。
- supervisor 必须生成 repair packets，并将 finding 路由给 owner。
- 每轮修复必须保留 patch、test、screenshot/playtest、gate evidence。

Phase D4: Commercial Final Gate

最终 gate 至少检查：

- 中文 UI。
- 真实玩法闭环。
- 关卡/成长/解锁。
- 商店/皮肤/收集或奖励系统。
- 可点击面板和玩家可见反馈。
- 动效。
- 音频/BGM/SFX。
- 真实资产 provider evidence。
- Cocos build。
- HTTP browser playtest。
- screenshot / player-visible evidence。
- `commercial_playable_go`。

### Milestone E: Workflow-Wide Evaluation And Repair Loop

目标：不是只评估当前 pipeline，而是评估 workflow 范围内的所有 blocker 和建议修复项。

Phase E1: Evaluation Matrix

必须覆盖：

- CLI receipt tests。
- capability control-plane tests。
- adapter route/default tests。
- mutation evidence tests。
- provider watchdog tests。
- API/MCP failure evidence tests。
- asset factory SFX tests。
- pipeline truth/preview/run tests。
- legacy template blocked negative test。
- doc link check。

Phase E2: Repair Loop

- workflow bug：回到 Milestone A bug-first 修。
- SFX/provider finding：回到 Milestone B 修。
- Cocos ecosystem capability finding：回到 Milestone C 修。
- business pipeline finding：回到 Milestone D task-card/workflow 修。
- 循环直到 workflow 范围内无建议修复项；不得把 NO-GO 或 skipped 包装成成功。

### Milestone F: Hygiene And Active Truth Sync

目标：确认工作树只留下需要长期维护的代码、测试、文档和证据索引。

清理范围：

- pytest 临时目录。
- 过期 evidence。
- 废弃 generated artifacts。
- 旧 handoff/scratch 文件。
- 重复或已被当前文档吸收的临时计划。

禁止：

- 删除商业 pipeline 功能。
- 删除仍用于证据链的 run artifacts。
- 删除 DB 权威 task-card 数据。
- 为了清理而改写历史结论。

文档更新：

- `README.md`
- `CURRENT_DEVELOPMENT_WORKFLOW.md`
- `docs/milestone_history.md`
- `docs/tech-debt-registry.md`
- `docs/governance/tech_debt_registry.json`
- 相关 handoff / evaluation docs。

### Milestone G: Real Commercial Game Run

仅在 Milestone A-F 通过后启动。

目标：用补全后的 `commercial_game_production` 跑一轮真实中文商业小游戏开发。

2026-04-29 no-degradation rerun 结果：`zero_degradation_cocos_worker_rerun4_20260429` 已完成严格重跑并被 gate v2 正确拦截。`commercial_game_task_card_worker` 不再用 E2E 生成器冒充实现，而是写入 same-project patch ledger 并逐卡调用 `workflowctl run from-task-card --execute`。该 run 中 real assets 与 live role proof 通过，但首张同项目业务卡触发 `provider_idle_timeout`；Cocos Editor bridge report、AssetDB/Scene/Prefab/Build API evidence、人审、8 关、商店/皮肤、音频 runtime、build/playtest 仍缺失，因此 `commercial_playable_go` 必须保持 false。

硬要求：

- 不允许降级为 demo / scaffold / old fixed template。
- 不允许缺真实资产 provider evidence。
- 不允许缺 build/playtest/player-visible evidence。
- 不允许把 `technical_smoke_go` 或 `production_scaffold_go` 当作 `commercial_playable_go`。
- 失败时输出 repair packets 并继续修复循环，直到 GO 或明确 blocked。

## 推荐执行命令

Phase 前置：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run plan-graph --goal "workflow-wide commercial game pipeline repair" --preset project_delivery
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run policy-preview --goal "workflow-wide commercial game pipeline repair" --preset project_delivery
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run goal-packet --goal "workflow-wide commercial game pipeline repair" --preset project_delivery
```

Pipeline truth：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline truth-report --template commercial_game_production
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline preview --template commercial_game_production
```

Pipeline run：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline run --template commercial_game_production --execute-agent-roles --execute-capabilities --repair-loop --require-real-assets --require-build --require-commercial
```

Validation：

```powershell
python -m pytest tests/test_capability_control_plane.py tests/test_cli.py tests/test_pipeline_and_automation_cli.py tests/test_asset_factory.py tests/test_cocos_e2e.py -q
python -m infra.scripts.check_doc_links
```

## Completion Report 要求

最终汇报必须列出：

- 修复的 bug。
- workflow run id。
- pipeline run id。
- game run id。
- evidence 路径。
- 测试结果。
- 清理清单。
- 剩余风险。

不得把失败 run、blocked stage、skipped dependency、NO-GO final gate 包装成成功。
