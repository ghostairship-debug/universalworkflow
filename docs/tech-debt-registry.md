# 技术债登记表

结构化真相源是 [docs/governance/tech_debt_registry.json](governance/tech_debt_registry.json)。本文档只提供人类可读摘要；治理 API/CLI 默认读取 JSON。

## 登记规则

- 只登记已经明确接受或在仓库中清晰观察到的债务。
- 不把未分析想法塞进登记表。
- 每条债务必须说明引入位置、计划偿还阶段、当前状态和阻塞影响。
- 历史债务可以汇总，但不能在没有证据的情况下静默删除。
- 不使用“项目零债”的表达；只说明 blocking debt 是否清零，以及 carry-forward debt 是否阻塞下一阶段。

## 当前结论

- M80-M108 的 provider runtime truth、asset factory、active truth check、workflow dogfood proof、historical `commercial_cocos_game` pipeline template、LangGraph 本地运行时、SQLite checkpoint、interrupt/resume、repair loop、subgraph/supervisor 探针、Cocos graph pressure test、Cocos inspector v2、本地稳定资产、玩家视角 gate 和小目标样机 closeout 已落地；2026-04-28 起旧 Cocos 固定模板交付入口已移除，真实游戏工作改走 `commercial_game_production`。
- M84 卫生清理确认：仓库源代码规模可控，膨胀主要来自 `state/` 生成态 evidence、pytest 临时目录和 Cocos 构建产物。
- 商业化游戏方向保留，但 M84 真实试玩反馈证明当前生成物不具备商业化可玩质量。
- 因此 `M77-COCOS-001` 从“已偿还”调整为“部分偿还”：技术链路已通，成品质量门禁未达标。
- M85-M104 已收敛 LangGraph 与 workflow 的主要边界：LangGraph 负责图状态、checkpoint、人审暂停、subgraph 和 repair loop；workflow 继续负责 receipt、lease、write_set、provider live proof、evidence 和 operator packet。
- M105-M108 已补齐 Cocos 真实工程样机闭环；M108.5 review 先修复证据闸口、做商业化 gap 归因，并把 task card 权威源迁回数据库，不能自动续到 M109。
- M109 已作为 pipeline / technical-smoke baseline 接受；2026-04-28 workflow-wide repair 已补齐 progress-aware watchdog、receipt propagation、scheduler lease terminal release/repair、remote callback idempotency、SFX modality/QA 和 Cocos audio modality binding。
- Fresh run `pipeline_a41e231c69a4` is preserved as gate v1 automated scaffold/build/playtest evidence. Superseding strict run `zero_degradation_rerun_20260428_evidencefix` failed gate v2 with `commercial_game_no_degradation_failed`; final commercial playable readiness remains blocked.
- 2026-04-29 strict rerun `zero_degradation_cocos_worker_rerun4_20260429` proved the new no-degradation path is stricter: real assets and live role proof passed, but same-project task-card patch stopped on `provider_idle_timeout`, Cocos Editor/API bridge report was missing, and human review remained absent. Follow-up smoke `cocos_bridge_smoke_20260429_145028` repaid the local Cocos Editor bridge/API blocker; this is still not commercial GO.
- 留存策略本轮暂不处理；大型生成态清理仍会持续发生。

## 当前未偿还或部分偿还债务

| ID | 描述 | 当前状态 | 阻塞影响 |
| --- | --- | --- | --- |
| M77-COCOS-001 | Cocos pipeline 已有 CLI/E2E/build/playtest 和 gate v1 证据，但 gate v2 严格商业 readiness 仍未通过 | partially_repaid | 阻塞声明 `commercial_playable_go=true`；允许继续声明 technical smoke / scaffold / automated playtest evidence |
| M84-GAME-QA-001 | 商业化验收已有结构化玩家视角 gate，但旧 gate 过宽；gate v2 已能拦截事件覆盖、浅关卡、皮肤标签、音频绑定和缺人工验收 | partially_repaid | 阻塞商业 GO；后续需真实玩家/设备和人工验收 |
| M109-NO-DEGRADATION-COMMERCIAL-001 | gate v2 严格 rerun `zero_degradation_cocos_worker_rerun4_20260429` 暴露同项目 patch `provider_idle_timeout`、8 关目标、商店/皮肤可见状态、音频 runtime、build/playtest 和人工验收缺口；Editor bridge blocker 已由后续 smoke 偿还 | open | 直接阻塞 `commercial_playable_go=true` |
| M109-COCOS-BRIDGE-SPLIT-001 | Cocos bridge runner 和 extension template 逻辑暂时扩大了 `ecosystem_bridge.py`，已由 ratchet exception 标注 M110 拆分窗口 | carry_forward | 非阻塞 maintainability debt；由 file-size/LOC ratchet 跟踪 |
| M77-LANGCHAIN-001 | LangChain 保留为实验性 agent adapter，但当前没有主线不可替代价值 | partially_repaid | 非阻塞；继续保持 opt-in |
| M67-CARRY-001 | `repositories.py`、`service_lifecycle.py`、`service_projection.py`、`interaction_catalog.py`、`models.py` 仍偏大 | carry_forward | 非阻塞；后续能力开发触发真实痛点时再拆 |

## 已偿还债务摘要

| ID | 描述 | 偿还阶段 | 结果 |
| --- | --- | --- | --- |
| TD-STRUCT-001 | Orchestrator/CLI/Web/chat surface 过大 | M62/M63 | facade ratchet、interaction split、chat runtime package、CLI command family、Web UI split 已落地 |
| TD-STRUCT-003 | scheduler-authority 命名可能高估 consensus 语义 | M65/M66 | 收敛为 `LocalSchedulerLeaseArbiter` local-first 语义 |
| TD-STRUCT-005 | capability health 缺少 runtime probe 支撑 | M64 | 加入 `CapabilityProbeResult` ledger 和 require-live probe |
| M67-SEC-001 | `OperatorActionReceipt` 缺少 request scope 绑定 | M67 P2 | 加入 `scope_hash` / `scope_payload` |
| M67-PROBE-001 | capability probe 可能误收 simulated/dry-run/fallback evidence | M67 P3 | 加入 provider-specific live-proof contract |
| M67-VAL-001 | offline validation 缺少 shard/freshness/timeout 报告 | M67 P4 | 加入 quick/full/shard、timeout trace、last-command 报告 |
| M67-WEB-001 | Web UI 依赖 inline CSP 例外和 `innerHTML` 路径 | M67 P5 | 静态化 operator CSS/JS，移除 CSP `unsafe-inline`，替换危险路径 |
| M67-SCHED-001 | scheduler 默认语义未完全 local lease 化 | M67 P6 | 改为 local scheduler lease arbiter 默认语义 |
| M73-MCP-001 | MCP include_mcp 可能暴露全部 profile | M73 | 加入 canonical tool id、selector、collision guard |
| M74-PIPE-001 | Pipeline 缺少正式 contract | M74 | 加入 `WorkflowPipeline` / `PipelineStage` |
| M75-PIPE-EXEC-001 | Pipeline 缺少最小执行入口 | M75 | 加入串行 `workflowctl pipeline run` |
| M77-PROVIDER-001 | Provider / Tool / Agent / Asset 边界混乱 | M80 | provider contract、verified-only health、route stats 已拆开 |
| M77-MMX-001 | MMX/MiniMax 缺真实 image/speech/music 资产生成主路径 | M81 | 加入 MiniMax wrappers、binary evidence、asset factory |
| M77-VERTEX-001 | Vertex/gcloud/GCP TTS 边界混乱 | M81 | 拆出 GCP TTS，Vertex Imagen/Gemini review 进入 live proof 和 QA |
| M77-PIPE-001 | Pipeline run 需要证明 stage 真实执行和失败短路 | M83 | 历史 `commercial_cocos_game` template 曾证明 asset factory、Cocos generation/build/playtest 和 readiness gate 可执行；2026-04-28 后该固定模板入口被 deprecation guard 阻断，真实游戏改走 `commercial_game_production` |
| M82-ACTIVE-TRUTH-001 | 活跃文档可能把已完成工作写成 planned/current/open | M82 | 加入 `workflowctl governance active-truth-check` |
| M84-CORE-PURITY-001 | Cocos/asset/business pipeline code 混入 core_domain | M90 | 垂直 Cocos/asset 实现移到 contributions/runtime_integrations，core_domain 边界恢复 |
| M84-PIPELINE-TRUTH-001 | Pipeline 可能把 placeholder/skipped/validation 失败误写成 completed | M90 | stage truth、安全 command runner、required dependency 和商业化三层 gate 已收敛 |
| M84-RATCHET-001 | 缺少 production/core/file ratchet | M90 | 加入 core purity、production LOC、业务文件大小和架构文档测试 |
| M85-LANGGRAPH-DUP-001 | workflow 编排与 LangGraph primitive 重叠 | M104 | 明确 LangGraph 承接图状态、checkpoint、人审暂停、subgraph 和 repair loop；workflow 保留安全、证据和 provider truth |
| M109-PIPELINE-COMPLETION-INFRA-001 | 商业 pipeline completion 暴露 route、receipt、watchdog、scheduler 和 evidence blocker | 2026-04-28 bug-first repair | Codex patch apply enforcement、receipt fail-fast/propagation、progress-aware watchdog、scheduler release/repair、remote callback idempotency 和 heartbeat evidence 已落地 |
| M109-SFX-MODALITY-001 | 短游戏 SFX 被错误归入 speech/TTS 或泛 audio 路线 | 2026-04-28 workflow task-card repair | `voice` / `music` / `sfx` 已拆分，`procedural_sfx_local` WAV artifact 加入 QA 元数据，Cocos SFX/voice/music binding 已覆盖 |
| M109-COMMERCIAL-GAME-EXTERNAL-001 | 早先 real run 因 Cocos autodiscovery 和 SFX provider 路线问题未能继续到 build/playtest | 2026-04-28 repair | Autodiscovery、SFX routing、source-path intake 和 evidence persistence bugs 已修；最终商业 GO 由 open gate v2 debt 跟踪 |
| M109-COCOS-ECOSYSTEM-001 | Cocos ecosystem bridge 缺少真实 Editor/API 报告 | 2026-04-29 local Cocos bridge smoke | `cocos_bridge_smoke_20260429_145028` 已证明 project-local Editor extension/runner、AssetDB import/query、Scene open/execute/save、node/component binding、Prefab instantiate、Build hook 和 license/cost manifest；Cocos Store/付费资产仍是显式 opt-in |

## 下一阶段建议

1. M108.5 先 review，决定停止、外部评估、人工试玩修复或新开 M109+。
2. 若新开 M109+，开发计划仍只写到 milestone 和 phase；task card 只在 active phase 生成。
3. 继续区分 technical smoke、production scaffold 和 commercial playable。
4. 保持 `state/` 生成态定期清理，避免 evidence 和构建产物再次膨胀到 GB 级。
## 2026-04-28 Commercial Pipeline Debt Update

- The workflow-infrastructure debt found during commercial pipeline completion is repaid: default patch-apply routing no longer falls to OpenCode, receipt mismatch fails fast, receipt ids propagate into orchestration children, Codex/OpenCode timeout evidence is progress-aware, scheduler leases release/repair correctly, remote callback duplicates are idempotent, and local-worker/pipeline heartbeat evidence exists for unattended runs.
- Commercial game readiness for “禅境方块” is not GO under no-degradation gate v2. `pipeline_a41e231c69a4` remains historical gate v1 evidence; `zero_degradation_cocos_worker_rerun4_20260429` is the current strict truth and is NO-GO.
- Short micro SFX now has an accepted local procedural route with QA metadata. Premium SFX/provider work remains future quality-tier work, while real commercial readiness still depends on a fresh full run with build/playtest/player-visible evidence.
- Detailed report: [commercial_game_pipeline_evaluation_2026_04_28.md](evaluations/commercial_game_pipeline_evaluation_2026_04_28.md).
