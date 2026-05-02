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
- 2026-05-02 `Provider Command Policy And Patch Generation Prompt Repair` repaid patch-only/no-shell provider command policy and Codex patch_apply user-config transport isolation. The revive prompt same-project card still blocked after three isolated fresh-receipt retries because Codex patch_apply reached `turn.started` but produced no acceptable diff before idle timeout; downstream build/playtest/audio/product-depth/human-review remains short-circuited.
- 2026-05-02 `Patch Worker Strategy Repair For Codex Turn-Start Stalls` repaid repo/project-rule contamination in Codex patch_apply by moving diff generation to a prompt-only broker workspace and adding `--ignore-rules`. `Revive Prompt Micro-Split Exact Context Repair` then completed the script-only revive prompt state patch. `Revive Prompt Layout Evidence Ultra-Split Repair` completed layout-only but exposed a no-diff feature-evidence stall. `Patch Generation No-Patch Diagnostic Repair` fixed the inner Codex idle budget mismatch and completed the feature-evidence patch; `Revive Feedback Feature Coverage Completion` then repaid explicit `failureReviveFeedback` player-visible coverage.
- 2026-05-02 `Trusted Cocos Build Browser Audio Runtime Evidence` initially reached machine-only `AWAITING_HUMAN_REVIEW`, but real human review then rejected the launched build as not being a completed game body. Strict pipeline `pipeline_ecf26665254e` is now `NO-GO`: `machine_evidence_go=false`, `human_player_review_go=false`, and `commercial_playable_go=false` because the gate over-accepted runtime hook / canvas / event coverage.
- 2026-05-02 post-review hardening 已完成 development-readiness loop：DB lifecycle execution eligibility、fresh same-project implementation proof、reference-only evidence reuse、gameplay semantic evidence、product-body evidence gate、source requirement matrix、task-card req_id coverage gate、独立 `commercial_game_development_readiness_go` 证据口径和非商业成品 Cocos product-body baseline bootstrap 已加入。DB active phase `product_body_runtime_semantic_trace_20260502` 已生成 3 张当前 phase task card 且 quality/lifecycle/req_id coverage 为 `GO`；这只表示可以开始真实商业游戏内容开发，不代表商业游戏本体已完成。
- 留存策略本轮暂不处理；大型生成态清理仍会持续发生。

## 当前未偿还或部分偿还债务

| ID | 描述 | 当前状态 | 阻塞影响 |
| --- | --- | --- | --- |
| M77-COCOS-001 | Cocos pipeline 已有 CLI/E2E/build/playtest、trusted Editor bridge、same-project task-card worker、真实资产链路、非商业成品 product-body baseline 和 development-readiness gate，但最新人审确认当前 build 不是合格游戏本体 | development_ready_product_body_active_phase_opened | 阻塞声明 `commercial_playable_go` 为 true；final gate 已新增 semantic/product-body/baseline-only 约束，task card 已新增 req_id coverage gate，下一阶段可开始真实商业游戏内容开发 |
| M84-GAME-QA-001 | 商业化验收 gate 曾误收 runtime hook / canvas / event coverage；最新人审证明 gate v2 没有真正挡住“非游戏本体”的机器假阳性 | development_gate_repaired_commercial_go_still_blocked | 阻塞任何商业 GO；当前已新增 runtime-hook/event-only/canvas-only/feature-flag-only/baseline-only 负例 gate 和 requirement coverage gate，后续还需真实产品证据 |
| M109-NO-DEGRADATION-COMMERCIAL-001 | `pipeline_ecf26665254e` 曾被机器证据接受，但真实人审判定产物不是完整游戏本体；同项目实现、playtest 和 product-depth 证据需要重新定义为玩家可见、非 runtime-hook 的硬证据 | development_ready_final_gate_no_go | 直接阻塞 `commercial_playable_go=true`；development readiness 已 GO，但产品本体重建和新 final-gate attempt 仍未完成 |
| M109-PROVIDER-WATCHDOG-001 | latest same-project worker evidence showed child workflow DB heartbeat while stdout/stderr stayed silent, so the outer task-card wrapper can misclassify child stdout silence as provider idle timeout and leave child runs/attempts running | repaid | 已由 `Provider Watchdog And Upstream Short-Circuit Repair` 修复；后续同项目实现恢复必须继续使用 DB heartbeat-aware watchdog 和 fresh receipt 续跑 |
| M109-UPSTREAM-SHORT-CIRCUIT-001 | same-project implementation failure currently allows downstream build/playtest/product-depth evidence collection to continue and produce noisy derived blockers | repaid | 已由 `Provider Watchdog And Upstream Short-Circuit Repair` 修复；上游实现失败时下游必须 `blocked_by_same_project_worker` 或 `skipped_due_to_upstream_failure` |
| M109-TASK-CARD-RETRY-001 | 同项目 task-card worker 对 provider output idle、无实质进展、provider timeout、child stalled、零补丁和测试失败缺少“三次 fresh receipt 重试后再阻塞”的统一 ledger 规则 | repaid | `Task Card Three-Attempt Retry And Output Idle Restart Repair` 已补充 `attempts[]`、`blocked_after_three_attempts`、provider/control/material watchdog 计数和 fail-fast 前置条件；未重新开启产品实现卡 |
| M109-TASK-CARD-DIRECT-OBSERVABILITY-001 | `from-task-card` patch apply 误入 `project_delivery` orchestration，且 Codex adapter 输出未桥接为 DB provider stream evidence，导致外层 watchdog 只能看到 control heartbeat | repaid | `Task Card Direct Execution And Provider Stream Observability Repair` 已改为 direct feature_delivery task-card patch path、DB `provider_stream_observed` metadata、runtime provider/material progress probe 和完整 child closure；不记录 raw text 或 chain-of-thought |
| M109-ADAPTIVE-WALL-TIMEOUT-001 | 同项目 task-card worker 对复杂任务使用固定 900 秒 wall timeout，即使 provider 仍有输出且有 material progress 也会被硬截断 | repaid | `Adaptive Wall Timeout For Active Provider Progress Repair` 已支持 bounded adaptive wall timeout：有 provider output 和 material progress 时可延长，默认 900 秒 + 900 秒、最多 1 次；延长耗尽后标记 `task_scope_too_large_after_adaptive_wall_timeout` 并要求拆分或收窄 task card |
| M109-SAME-PROJECT-PRODUCT-001 | 同项目商业玩法实现曾被机器证据标记完成，但真实人审确认 build 不是完整游戏本体，说明 product-depth 证据仍被 runtime hook / event coverage 污染 | reopened_by_human_review | 重新阻塞机器证据和商业 GO；下一阶段必须重建玩家可见游戏本体，不能用事件标记代替功能完成 |
| M109-CODEX-PATCH-APPLY-TURN-STALL-001 | isolated Codex patch_apply 可到达 `turn.started`/provider stream observation，但未在 idle 窗口内返回可接受 unified diff | repaid | `Patch Worker Strategy Repair For Codex Turn-Start Stalls` 已改为 prompt-only broker workspace + `--ignore-rules`，并保留 provider/receipt/write_set evidence；剩余 blocker 转入 revive prompt micro-split |
| M109-REVIVE-PROMPT-MICRO-SPLIT-001 | revive prompt 同项目产品卡在上述 worker 修复后仍无法生成 accepted patch，说明 broad card 仍过宽或缺 exact file-level diff context | partially_repaid | script-only exact-context 微卡已完成，合并 layout/evidence 微卡仍失败；下一步必须拆成 layout-only 与 feature-evidence-only |
| M109-REVIVE-LAYOUT-EVIDENCE-ULTRA-SPLIT-001 | revive prompt 的 layout/evidence JSON 合并卡在 script 状态已完成后仍三次 fresh receipt 失败，说明 JSON 更新仍需更小写集和更小上下文 | repaid | layout-only 已完成；feature-evidence no-diff stall 转由 `Patch Generation No-Patch Diagnostic Repair` 修复 |
| M109-PATCH-NO-DIFF-IDLE-BUDGET-001 | feature-evidence 卡三次 child run 只到 `thread.started`/`turn.started`，无 patch artifact；wrapper 内层 `WORKFLOW_CODEX_IDLE_TIMEOUT_SECONDS=240` 早于外层 provider-output idle 480 秒切断 Codex turn | repaid | `Patch Generation No-Patch Diagnostic Repair` 已把内层 Codex/provider idle budget 对齐到 480 秒，`run_f41c5b586681` 以 fresh receipt 完成 feature-evidence patch |
| M109-REVIVE-FEEDBACK-COVERAGE-001 | revive prompt evidence 已写入，但 `commercial_feature_coverage` / `player_visible_checks` 仍缺显式 `failureReviveFeedback=true`，`current_task_card_id` 和 `covered_task_cards` 仍停在上一张失败弹窗卡 | repaid | `Revive Feedback Feature Coverage Completion` 已完成：Codex 三次 fresh receipt 后 blocked，OpenCode 以当前 phase live proof 作为真实 fallback 完成同一卡，`failureReviveFeedback=true` 已写入 feature/player-visible coverage |
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

1. 下一步不能继续等待人审，也不能继续声明 machine evidence complete；真实 human/player review 已给出 `NO-GO`。
2. push 成功后按 active-phase-only 原则开启 `Commercial Game Core Content Implementation`，只为该 phase 生成 DB task cards；开发计划仍只写到 milestone 和 phase。
3. 继续区分 technical smoke、pipeline/build/browser runtime、machine gate 和 commercial playable；runtime hook / canvas / event-only evidence 不能满足产品本体 gate。
4. 保持 `state/` 生成态定期清理，避免 evidence 和构建产物再次膨胀到 GB 级。
## 2026-04-28 Commercial Pipeline Debt Update

- The workflow-infrastructure debt found during commercial pipeline completion is repaid: default patch-apply routing no longer falls to OpenCode, receipt mismatch fails fast, receipt ids propagate into orchestration children, Codex/OpenCode timeout evidence is progress-aware, scheduler leases release/repair correctly, remote callback duplicates are idempotent, and local-worker/pipeline heartbeat evidence exists for unattended runs.
- Commercial game readiness for “禅境方块” is `NO-GO`: human review superseded `pipeline_ecf26665254e` machine evidence and identified the launched build as not being a completed game body.
- Short micro SFX has an accepted local procedural route with QA metadata, and runtime browser evidence can still be useful as technical evidence, but it cannot prove product-body completion without player-visible game functionality and human review acceptance.
- Detailed report: [commercial_game_pipeline_evaluation_2026_04_28.md](evaluations/commercial_game_pipeline_evaluation_2026_04_28.md).
