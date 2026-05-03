# Universal Agentic Workflow OS

## M109 Status Update (2026-04-27)

- Accepted baseline: `M109`.
- Completed: unified project brief, single-agent role pipeline, design/planning outputs, multimodal route truth table, DB-backed task-card gate, bounded Cocos technical-smoke trial, and cluster-upgrade review.
- Cocos trial result: `technical_smoke_go=true`, `production_scaffold_go=true`, `commercial_playable_go=false`.
- Current claim: pipeline technical trial completed; machine evidence for the current commercial build is ready for human review, but commercial playable game acceptance is still not proven.
- Cluster decision: keep single-agent roles for now; no automatic M110 task cards.

## Real Game Pipeline Correction (2026-04-28)

- The legacy `commercial_cocos_game` fixed-template pipeline is removed as an executable delivery path.
- Running that legacy template now returns the blocked deprecation guard `legacy_cocos_template_removed` instead of generating a template-based Cocos project.
- Real commercial game work must enter `commercial_game_production`: unified brief, role outputs, DB task cards, real asset generation, task-card implementation, player QA, supervisor decision, and final commercial readiness gate.
- Low-level Cocos E2E/scaffold commands may still exist for diagnostics, but they are not allowed to prove or deliver a commercial game by themselves.
- A Cocos engine empty project may be used only as technical bootstrapping; final content cannot be the old fixed game template.

## Commercial Pipeline Evaluation (2026-04-28)

- Bug-first repair completed for the known route/evidence blockers: default `from-task-card` patch apply is Codex CLI, not OpenCode; missing or scope-mismatched receipts fail fast; Codex/OpenCode watchdog evidence now preserves timeout type, `failure_class`, stdout/stderr summaries, mutation result, last-output context, and recovery guidance.
- Long unattended runs now have heartbeat evidence at both local-worker and pipeline-run layers. Pipeline heartbeat JSONL is written beside run evidence.
- Scheduler lease terminal release, stale lease repair, parent receipt propagation into orchestration children, and duplicate remote callback idempotency are covered by workflow regression tests.
- Asset modality repair split `voice` / `music` / `sfx`: `sfx_place` and `sfx_clear` use `procedural_sfx_local` WAV assets with sha256, duration, RMS/peak, non-silent, clipping, provenance, and QA gate metadata; `voice_reward` remains voice/TTS.
- Cocos commercial asset manifests and runtime bindings now preserve SFX/voice/music modalities through resource binding and audio runtime hooks.
- `commercial_game_production` was evaluated through real pipeline runs. The pipeline now records role, asset, worker, supervisor, and final-gate evidence honestly, including provider quota failures and operator-input blockers.
- The final real game attempt was `pipeline_061e3703e442` in `state/long_runs/commercial_game_attempt_20260428_054050`; it is `NO-GO`. A later correction verified Cocos Creator is installed at `C:\ProgramData\cocos\editors\Creator\3.8.8\CocosCreator.exe`; the failure exposed a pipeline autodiscovery bug when `--creator-exe` was omitted, and that bug is now fixed.
- Superseding no-degradation review: earlier run `pipeline_a41e231c69a4` is preserved as automated scaffold/build/playtest evidence, but it no longer proves final commercial readiness under gate v2. Strict rerun `zero_degradation_rerun_20260428_evidencefix` failed honestly with `commercial_game_no_degradation_failed`: live role provider proof passed, but Cocos ecosystem bridge, same-project worker patch proof, 8 distinct level goals, visible shop/skin ownership flow, audio runtime verification, build-exit strictness, and human player review are still blockers.
- 2026-04-29 zero-degradation repair checkpoint: Cocos ecosystem evidence now installs a project-local Editor bridge package, records a license/cost manifest, rejects filesystem-only bridge reports, and persists its own evidence path. Later the unattended bridge runner was added and verified against local Cocos Creator 3.8.8 with true Editor/AssetDB/Scene/Prefab/Build API report evidence at `state/long_runs/cocos_bridge_smoke_20260429_145028/cocos_ecosystem/cocos_ecosystem_bridge_evidence.json`. The commercial task-card worker no longer routes DB task cards into the deterministic Cocos E2E generator; it bootstraps one empty Cocos project shell, executes same-project task cards through `workflowctl run from-task-card --execute` with receipt-bound Codex patch apply, and writes `same_project_patch_ledger.json`. Strict rerun `zero_degradation_cocos_worker_rerun4_20260429` still failed correctly with `commercial_game_no_degradation_failed`: real assets and live role provider proof passed, but the first same-project task-card patch hit `provider_idle_timeout`, product-depth gates and human review were not present.
- Current evaluation report: [docs/evaluations/commercial_game_pipeline_evaluation_2026_04_28.md](docs/evaluations/commercial_game_pipeline_evaluation_2026_04_28.md).
- Commercial production v2 design blueprint: [COMMERCIAL_GAME_PRODUCTION_V2_PIPELINE_DESIGN.md](COMMERCIAL_GAME_PRODUCTION_V2_PIPELINE_DESIGN.md). It describes the stage-internal phase graph, asset graph, Cocos bridge workers, supervisor repair loops, and final gate contract; it is not an active task-card export.
- Post-M109 long-running repair plan: [POST_M109_LONG_RUNNING_DEVELOPMENT_PLAN_2026_05_02.md](POST_M109_LONG_RUNNING_DEVELOPMENT_PLAN_2026_05_02.md). It consolidates the latest root guidance/evaluation documents into milestone/phase-level work only; it does not create M110 or future task-card exports. Current hardening now includes DB lifecycle/fresh execution gates, `human_visible_cli_enforced` for high-risk commercial task cards, lossless single-agent role v2 preservation, compile/recompile protection for active commercial DB cards, gameplay semantic/product-body contracts, source requirement matrix plus task-card req_id coverage gating, an independent `commercial_game_development_readiness_go` evidence口径, and a non-commercial Cocos product-body runtime baseline for future same-project work.
- Universal game-production and AI surrogate playtest upgrade plan: [UNIVERSAL_GAME_PRODUCTION_AI_PLAYTEST_UPGRADE_PLAN_2026_05_03.md](UNIVERSAL_GAME_PRODUCTION_AI_PLAYTEST_UPGRADE_PLAN_2026_05_03.md). It generalizes beyond the current block-puzzle sample and defines a higher production vertical-slice floor, game-agnostic design IR, AI playtest lab, quality scorecard, and defect-to-repair loop.
- The first implementation rounds of that universal plan are now present in `packages/contributions/games/`, exposed through `workflowctl game`, and integrated into `commercial_game_production` current-phase task-card materialization: game-agnostic design IR, derived-only semantic enrichment, engine-native product-body contract, AI surrogate quality gate, AI findings-to-repair cards, AI playtest lab planning, GameDesignSpec-to-workflow-task-card generation, AI playtest runner/execution packet validation, AI quality gate execution, AI repair-card generation, AI NO-GO repair-loop entry generation, category-split current-phase game task cards, and commercial matrix coverage for the universal game / AI playtest regression set. `commercial_game_production` now treats AI surrogate playtest evidence as a default commercial machine gate. These are control-plane/product-quality capabilities, not a claim that a new commercial game is complete.
- Development readiness status: `commercial_game_development_readiness_go=true` means the control plane can safely start real commercial game content task cards; it is not a commercial playable claim. As of the 2026-05-03 asset/browser/audio proof phase, `machine_evidence_go=true` and the final gate is `AWAITING_HUMAN_REVIEW`, while `commercial_playable_go=false` remains the current truth until human review accepts the build.

## Commercial Runtime Evidence Closeout (2026-05-02)

- Strict pipeline `pipeline_ecf26665254e` produced real asset generation, same-project implementation evidence, trusted Cocos bridge evidence, Cocos Creator 3.8.8 Web Mobile build ledger, HTTP/browser playtest ledger, screenshots, and audio/BGM/SFX/volume runtime proof, but the subsequent real human review rejected the launched build.
- Current final gate is `AWAITING_HUMAN_REVIEW`: `machine_evidence_go=true`, `human_player_review_go=false`, and `commercial_playable_go=false`.
- The 2026-05-02 reviewed URL did point at the then-current pipeline `build/web-mobile`; that failure was product-level, not a wrong launch path. The repaired machine gate now rejects runtime hook / canvas / event coverage as completed game-body proof.
- Next commercial-game handoff is real human player review of the machine-ready build. Unattended automation must not convert event-only, canvas-only, scaffold, build-only, baseline-only, browser-event, or machine-only evidence into commercial GO.
- 2026-05-03 hardening completes the pre-commercial control-plane repair: high-risk commercial cards cannot pass headlessly, single-agent roles cannot omit or rewrite input requirements, ordinary compile/recompile cannot overwrite active commercial DB task cards, and runtime semantic/product-body evidence must come from model transitions and Cocos component bindings.
- 2026-05-03 machine-evidence narrowing completed `Commercial Machine Evidence And Player Visible Completion` with exactly three visible-CLI DB task cards. Product-body, gameplay semantic, product-depth, and Cocos build evidence became GO.
- 2026-05-03 asset/browser/audio proof completed `Commercial Asset And Browser Runtime Proof Implementation` with exactly three visible-CLI DB task cards. Non-placeholder asset graph, browser interaction playtest, and browser audio/BGM/SFX/volume runtime evidence are now GO; the only remaining blocker is `awaiting_human_player_review`.
- 2026-05-03 user review then rejected the launched build as not genuinely playable. Current truth is again product-level `NO-GO` for acceptance: `human_player_review_go=false` and `commercial_playable_go=false`. The active repair loop replaces the proof-only browser bridge with `packages/contributions/games/cocos/browser_runtime_bridge.js`, a player-visible 10x10 runtime that is being verified with Playwright screenshots and interaction evidence, but agent QA is not human acceptance.
- 2026-05-03 second user review rejected the first repair slice for missing BGM, incomplete functions, missing Chinese UI, drag stutter, and coordinate mismatch. The latest repair slice adds Chinese UI, procedural Web Audio BGM/SFX, immediate drag-follow placement preview, aligned coordinate mapping, shop/gallery/level/revive/pause panels, and BGM state screenshots. Agent QA evidence passes, but `commercial_playable_go=false` remains until explicit human acceptance.
- 2026-05-04 PDF-only workflow run `commercial_game_pdf_only_20260503` supersedes the old `state/pipeline_runs/commercial_game_core_content_20260503` snapshot for current review. Using only `C:\Users\74755\Desktop\俄罗斯方块消除策划文档4.2.pdf` as product input, workflow task cards repaired build import/syntax blockers, browser runtime bridge sources, BGM/SFX/volume, Chinese UI, drag alignment, panels, and missing-feature gates. Current machine evidence has `build_ledger.go=true`, `browser_playtest_ledger.go=true`, `product_depth_evidence.go=true`, and no commercial machine blockers; `commercial_playable_go=false` remains until explicit human acceptance.
- 2026-05-04 provider visibility ratchet: `human_visible_cli_enforced` commercial task-card execution now runs as resident control-plane + direct visible `codex` / `opencode` provider subprocesses. The outer workflow process stays in the resident control plane instead of opening a new visible `workflowctl` window per card; the provider console is human-readable, while control-plane and provider-level `stdout.log`, `stderr.log`, `stream.jsonl`, and `visible_cli_session.json` are recorded for machine evidence.
- 2026-05-04 fresh D-root regeneration `D:\WorkflowCommercialGameFresh_20260504_R5\cocos_project` used the same desktop PDF as the only product source and removed earlier failed D-root regeneration folders from this loop. The rebuilt Web Mobile output passes browser playtest and commercial feature gates with empty console/page errors; generated background, block-skin, and clear-particle assets are now loaded from `commercial_asset_bindings.json` and drawn in the player-visible runtime. This is machine-ready for review, not an unattended `commercial_playable_go=true` claim.

## 当前状态：M109 Pipeline / Technical-Smoke Baseline

- 包版本：`0.66.0`。
- 当前接受实现基线：M109 已完成统一资料包、单 agent 角色管线、设计/方案输出、多模态路由真相表、DB task-card quality gate、有限 Cocos technical-smoke trial 和 cluster-upgrade review。
- 当前质量结论：M108 Cocos 小目标样机闭环是历史基线；M109 只证明 pipeline / technical-smoke；当前商业构建的机器证据已到 `AWAITING_HUMAN_REVIEW`，但 `commercial_playable_go` 仍为 false，不能宣称商业化可玩成品。
- 当前工作重点：M109 后 `commercial_game_production` 无降级修复；不自动进入 M110，不提前生成未来 phase task card。
- task card 规则：数据库是权威来源，Markdown 只是自动导出的人工快照；每张卡必须包含目标、读写范围、测试、证据、阻塞条件和模型执行提示。
- M108.5 决策记录：[docs/evaluations/m108_5_review_decision.md](docs/evaluations/m108_5_review_decision.md)。
- 活跃开发方案见：[CURRENT_DEVELOPMENT_WORKFLOW.md](CURRENT_DEVELOPMENT_WORKFLOW.md)。
- 历史收敛方案已压缩进里程碑历史和架构笔记，不再在根目录保留散装计划书。
- 治理真相源：[docs/governance/tech_debt_registry.json](docs/governance/tech_debt_registry.json)。

Universal Agentic Workflow 是一个本地优先的 agentic workflow runtime。它的目标不是公开 SaaS、多租户平台或插件市场，而是让个人开发者把 AI、CLI、代码仓库、测试、审查、证据和自动化任务组织成可恢复、可审计、可长期推进的工作流。

## 项目全景

一句话说，它是一个本地优先的“AI 工作流控制台”。它不是单纯聊天机器人，而是把 AI、命令行工具、代码仓库、测试、审查、文档、证据记录和自动化执行组织成一套可追踪、可恢复、可审计的工作流。

它适合个人开发者、研究型项目维护者和需要长期迭代复杂代码库的人；当前不适合作为公开 SaaS、多租户团队平台、外部托管执行服务或一键自动发布平台。

核心设计原则：

- 本地优先：默认使用本地仓库、本地数据库、本地 CLI 和本地 Web console。
- 证据优先：重要动作需要 task card、route preview、测试输出、capability probe、operator packet 或恢复指针。
- 安全边界优先：高风险动作需要 receipt 或 lease，provider ready 需要真实 live proof。
- 长程任务优先：plan、milestone、phase、task card、checkpoint、评估与修复循环都必须可恢复。

项目主要由 `workflowctl` CLI、本地 FastAPI/Web operator console、core domain、adapter/provider、pipeline 和治理文档组成。Pipeline 是“计划之上的计划”，用于把需求解析、资产生成、代码实现、构建、浏览器测试和 GO/NO-GO 串成可审计流程。

## 活跃真相集

后续开发优先参考这些文件：

- [当前开发工作流](CURRENT_DEVELOPMENT_WORKFLOW.md)
- [里程碑历史](docs/milestone_history.md)
- [技术债登记表](docs/tech-debt-registry.md)
- [结构化技术债 JSON](docs/governance/tech_debt_registry.json)

历史评估、旧恢复计划、旧路线图、重复阶段报告和临时 evidence 不再作为当前判断来源。需要逐字审计时使用 Git 历史。

## 当前能力

- 本地 CLI：`workflowctl`
- 本地 API：FastAPI orchestrator API
- 本地 Web operator console：`/ui`、`/ui/workbench`、`/ui/reviews`、`/ui/config`
- 核心能力：run 生命周期、task card、route preview、evidence、operator packet、receipt/lease 高风险门禁、repo mutation、test matrix、offline validation、pipeline preview/run
- LangGraph 本地能力：SQLite checkpoint、interrupt/resume、repair loop、subgraph/supervisor 探针、stream evidence、Studio graph 配置和 Cocos graph pressure test
- 已接入 provider/adapter：Codex CLI、OpenCode CLI、Claude CLI、MMX/MiniMax、Vertex/GCP、LangChain、Shell/Noop
- OpenAI API 当前不声明 ready；OpenAI-family coding 主路径是 Codex CLI
- Gemini CLI 暂未接入；Gemini-family 能力短期通过 Vertex/GCP
- `gcloud` 是 Vertex/GCP 认证与环境工具，不是独立 worker adapter
- LangChain 是 experimental / opt-in agent framework，不是默认主路由

## 商业化游戏生产线真实状态

商业化 H5/Cocos 游戏生成仍然是正式业务方向，但必须诚实区分三层结果：

1. **技术 smoke**：工程能生成、能构建、浏览器能打开。
2. **E2E scaffold**：有 Cocos 工程、资产绑定、自动试玩和 feature coverage。
3. **商业化可玩成品**：有完整 UI、美术统筹、可用面板、真实关卡流程、音频设计、动效反馈、可玩性和移动端体验。

当前代码已经具备前两层和小目标样机 closeout 能力，并加入了结构化玩家视角 gate。按 2026-04-28 no-degradation gate v2，第三层仍为 NO-GO，直到所有硬证据都齐全：

- UI 仍像调试面板，缺少成品级界面设计。
- 关卡切换、皮肤、画廊、复活等功能更多是事件标记或浅交互。
- 自动化测试过度依赖状态变量，未严格验证玩家视角的可用性和美观度。
- 音频和配音缺少已验证的 runtime 播放、触发策略和混音/音量控制。
- Cocos ecosystem collector now has a project-local Editor extension, unattended bridge runner, license/cost manifest, and trusted report validation. Local smoke `cocos_bridge_smoke_20260429_145028` proved Editor version/project open, AssetDB import/query, Scene open/execute/save, node/component binding, Prefab instantiate, and Build hook evidence. This satisfies `ecosystem_integration_go` for the local Editor bridge only; it does not make the commercial game body playable.
- Web Mobile 构建需要 HTTP 服务运行，不能保证解压后双击 `index.html` 即可游玩。

因此，后续不得把 `commercial_go_no_go=GO`、feature flag、canvas 非空、事件覆盖、APK/HTML 打包成功写成“完整商业化游戏已生成”。商业化 pipeline 需要继续优化，而不是删除。

## 快速开始

```powershell
pip install -e ".[dev]"
python -m infra.scripts.manage --db-path state/workflow.db reset-db
python -m infra.scripts.manage --db-path state/workflow.db smoke
```

启动本地 Web operator console：

```powershell
uvicorn apps.orchestrator_api.main:app --host 127.0.0.1 --port 8000
```

常用页面：

- `http://127.0.0.1:8000/ui`
- `http://127.0.0.1:8000/ui/workbench`
- `http://127.0.0.1:8000/ui/reviews`
- `http://127.0.0.1:8000/ui/config`

## 常用命令

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" doctor --strict
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run plan-graph --goal "实现一个受控能力切片" --preset project_delivery
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run policy-preview --goal "实现一个受控能力切片" --preset project_delivery
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run goal-packet --goal "实现一个受控能力切片" --preset project_delivery
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider all --require-live --evidence-dir state/capability_probes
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability health --verified-only
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability routes stats --days 30
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" governance active-truth-check --strict --output-path state/governance/active_truth_check.json
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline truth-report --template commercial_game_production
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline preview --goal "完整中文版商业化小游戏"
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" intake package --input docs --output-dir state/intake/example_bundle
```

通用资产工厂：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" asset factory run --style-guide "premium neon casual puzzle" --manifest state/asset_factory/prompt_manifest.json --output-dir state/asset_factory/run
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" asset factory qa --asset-manifest state/asset_factory/run/asset_factory_manifest.json --evidence-dir state/asset_factory/qa
```

Cocos fixed-template delivery entry is removed. Use the real production pipeline:

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline preview --template commercial_game_production
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline run --template commercial_game_production --execute-agent-roles --live-agent-roles --execute-capabilities --repair-loop --require-real-assets --require-build --require-playtest --require-commercial --require-cocos-ecosystem --require-human-player-review --source-path "C:\Users\74755\Desktop\游戏策划.md"
```

## Workflow Dogfood 规则

- 一个 plan 应包含多个 milestone。
- 一个 milestone 应包含多个 phase。
- 开发计划文档只写到 milestone 和 phase，不提前生成 task card。
- 只有 active phase 才生成 task card。
- 一个 phase 默认应包含多张 task card；单卡 phase 必须标记 `single_card_exception`。
- task card 权威记录写入数据库，Markdown 只做快照导出。
- task card 必须足够详细，不能只是任务清单。
- phase 前运行并保存 `plan-graph`、`policy-preview`、`goal-packet`。
- 简单低风险任务优先交给 workflow + OpenCode/MiniMax。
- 中等 review/validation 可走 DeepSeek V4 Flash，失败直接 fallback Codex。
- 复杂架构、安全协议、repo mutation 使用 Codex 或本地补丁兜底。
- artifact-only 和 disjoint write_set task card 可以并发；write_set 冲突、dirty worktree、SQLite lock 或 repo mutation 异常时降级串行。
- workflow 自身 bug 优先级高于业务 phase：先登记、修复、补回归测试，再恢复原 phase。

## 安全边界

高风险动作必须通过 scope-bound `OperatorActionReceipt` 或明确的 `AutomationLease`：

- `launch_execute`
- `resume_run`
- `approve_run`
- `reject_run`
- `cancel_run`
- `batch_resume_runs`
- repo mutation / patch apply
- watchdog auto-apply
- git commit / push / PR

GET 请求不得产生状态变更。所有文件写入必须解析明确 workspace root。

## 验证

文档变更至少运行：

```powershell
python -m infra.scripts.check_doc_links
```

常规开发收口：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite unit
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite core
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite integration
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" validation run --suite full --skip-offline-probe
python -m pytest -q
```

`workflowctl test matrix` 会把 pytest 临时目录放到 `state/.pytest-tmp-workflow/`。测试成功后自动清掉本次临时目录；测试失败时保留现场。需要临时禁止清理时设置 `WORKFLOW_KEEP_TEST_TEMP=1`。
