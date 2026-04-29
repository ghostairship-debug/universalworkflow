# 里程碑历史摘要

本文档只提供历史摘要，不作为活跃执行计划。当前判断以 README、当前开发工作流和技术债登记为准。

## 当前基线

- 日期：2026-04-27
- 最新接受实现基线：`M109`
- 当前活跃计划：M109 后 `commercial_game_production` 与 workflow-wide bug-first 修复；不自动生成 M110 task card
- 产品前提：个人自用、本地优先的 operator runtime
- 当前硬规则：workflow 共同开发、bug-first、scoped receipt、provider live proof、route/evidence/operator packet、plan/milestone/phase/task card 四层语义，active phase 才生成 task card

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
| M84-M90 | architecture discipline gate 与 LangGraph/workflow 收敛：core_domain 边界、pipeline truth、安全 command runner、ratchet、图模型权威、graph execution kernel、interrupt/receipt 融合、checkpoint、subgraph、Cocos pressure test | 已完成 |
| M91-M98 | LangGraph 与 Cocos 生态扩展：Studio graph、stream evidence、Cocos graph bridge、生态边界整理 | 已完成 |
| M99-M104 | LangGraph 本地能力补齐：SQLite checkpoint、interrupt/resume、repair loop、subgraph/supervisor 探针、Cocos-safe runtime 配置 | 已完成 |
| M105-M108 | Cocos 真实工程接入：command/config truth、project inspector v2、本地稳定资产、Prefab/Panel/交互契约、玩家视角 gate、graph evidence bridge、小目标样机 closeout | 已完成样机闭环；商业化可玩仍需真实玩家证据 |
| M108.5 | 复盘决策点：修复 self-development manifest evidence 读取、加严 Cocos 玩家视角 gate、处理过期 ratchet 例外、恢复 DB task card 权威源，并判断是否允许进入 M109 | M109 暂不自动开始 |

## M104/M105 关键结论

- 商业化 Cocos/H5 游戏生成仍是正式业务需求。
- 当前 pipeline 和代码保留，不从仓库删除。
- 最近一次真实生成质量不足：UI 原始、关卡浅层、面板不可用、音频突兀、HTML 双击不可玩。
- 不能再把状态变量覆盖、feature flag、HTML/APK 打包或浏览器事件覆盖当成商业化成品验收。
- LangGraph 底座已可用于后续开发：状态推进、checkpoint、人审暂停、subgraph、repair loop 和 stream evidence 可以优先走 graph-backed 路径。
- M105-M108 已完成到小目标样机闭环；M108.5 必须先 review，决定停止、外部评估、人工试玩修复或有预算上限地新开 M109+。

## 历史材料治理

已关闭材料不再保留为活跃 Markdown：

- 旧 `m*_phase_docs/`
- 旧 `docs/task_cards/`
- 根目录长期路线图、评估文档、恢复计划、重复执行报告
- 临时 workflow state evidence

需要逐字审计时使用 Git 历史。
# M109 Status Update (2026-04-27)

- Latest accepted baseline: `M109`.
- M109 completed the unified project brief, single-agent role pipeline, design/planning outputs, multimodal route truth table, DB-backed task-card quality gate, bounded Cocos technical-smoke trial, and cluster-upgrade review.
- Cocos trial result: technical smoke and production scaffold passed; commercial playable remains `NO-GO` because player-visible build/playtest evidence is still missing.
- Cluster decision: keep single-agent roles; do not revive legacy cluster runtime or auto-create M110 task cards.

## 2026-04-28 Correction

- The legacy `commercial_cocos_game` fixed-template pipeline is removed as an executable delivery path.
- `commercial_game_production` is now the required entry for real commercial game work.
- Old Cocos scaffold/E2E utilities remain diagnostic tools only; they cannot deliver or prove a commercial game by themselves.

## 2026-04-28 Commercial Pipeline Evaluation

- Bug-first workflow repairs closed the OpenCode/Codex route and timeout-evidence blockers from the commercial pipeline completion attempt.
- `from-task-card` patch apply defaults to Codex CLI enforcement for repo mutation; OpenCode is not the default pipeline-completion mutation route.
- Progress-aware Codex/OpenCode watchdog evidence, parent receipt propagation, scheduler lease terminal release/repair, duplicate remote callback idempotency, local worker heartbeat, and pipeline heartbeat were added for unattended execution.
- Asset modality repair split `voice` / `music` / `sfx`; local `procedural_sfx_local` WAV generation is accepted for micro SFX when artifact QA passes, and Cocos runtime bindings now preserve SFX/voice/music modalities.
- `commercial_game_production` evaluation produced honest NO-GO runs instead of silent or downgraded success. See [docs/evaluations/commercial_game_pipeline_evaluation_2026_04_28.md](evaluations/commercial_game_pipeline_evaluation_2026_04_28.md).
- Final real game attempt `pipeline_061e3703e442` remains `NO-GO`. A later correction verified Cocos Creator is installed and fixed pipeline autodiscovery when `--creator-exe` is omitted.
- Fresh post-repair run `pipeline_a41e231c69a4` is preserved as gate v1 automated scaffold/build/playtest evidence. Later no-degradation gate v2 rerun `zero_degradation_rerun_20260428_evidencefix` failed with `commercial_game_no_degradation_failed`; it must not be cited as final commercial playable proof until Cocos ecosystem bridge, same-project patch proof, product-depth features, audio runtime evidence, strict build-exit handling, and human player review pass.

## 2026-04-29 Zero-Degradation Cocos/Worker Checkpoint

- `cocos_ecosystem_bridge_evidence_v2` now installs a project-local Cocos Editor extension package, writes a license/cost manifest, and accepts only trusted Editor-extension or local-MCP reports for ecosystem GO; filesystem-only, CLI-build-only, playtest-only, or feature-flag-only reports are rejected.
- `commercial_game_production` no longer uses the deterministic Cocos E2E/scaffold generator as the DB task-card implementation worker. Same-project business cards are materialized, run through `workflowctl run from-task-card --execute` with scope-bound receipt, and summarized in `same_project_patch_ledger.json`.
- Bug-first repair added progress-aware child watchdog evidence for the task-card worker CLI. Idle and wall timeouts now preserve stdout/stderr previews, stream-event counts, failure class, and recovery guidance.
- Strict rerun `zero_degradation_cocos_worker_rerun4_20260429` is an honest `NO-GO`: real assets and live role proof passed, but the first same-project business card stopped with `provider_idle_timeout`, and true Cocos Editor/AssetDB/Scene/Prefab/Build report plus human review and product-depth proof are still missing.
- `commercial_playable_go` remains false. This checkpoint proves the no-degradation gate is blocking correctly; it is not final commercial game delivery.
