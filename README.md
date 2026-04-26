# Universal Agentic Workflow OS

## Current Version: M82 Workflow Self-Development Loop

- Package version: `0.66.0`.
- Accepted implementation baseline: `M82` active truth and workflow self-development proof.
- Active repair entry: M80-M83 capability-layer recovery. M80 provider runtime truth, M81 reusable asset factory, and M82 active truth/workflow dogfood proof are implemented; M83 continues with templated commercial Cocos pipeline.
- Beginner overview: [项目全景介绍](PROJECT_OVERVIEW_FOR_BEGINNERS.md).
- Governance source of truth: [structured tech debt registry](docs/governance/tech_debt_registry.json).

Universal Agentic Workflow 是一个本地优先的 agentic workflow runtime。它的目标不是公开 SaaS、多租户平台或插件市场，而是让个人开发者可以把 AI、CLI、代码仓库、测试、审查、证据和自动化任务组织成可恢复、可审计、可长期推进的工作流。

## Active Truth Set

后续开发优先参考这些文件：

- [当前开发工作流](docs/current_development_workflow.md)
- [M77 Issue Register](M77_ISSUE_REGISTER.md)
- [里程碑历史](docs/milestone_history.md)
- [技术债登记表](docs/tech-debt-registry.md)
- [结构化技术债 JSON](docs/governance/tech_debt_registry.json)

历史评估、旧恢复计划、旧路线图、阶段报告和重复根目录材料不再保留为工作树文档。需要逐字历史时看 git 历史；当前判断以 Active Truth Set 为准。

## Current State

- 入口：CLI、API、Web operator console、`/ui/workbench` streaming chat workbench。
- 已接入 provider/adapter：Codex CLI、OpenCode CLI、Claude CLI、MMX/MiniMax、Vertex、LangChain、Shell/Noop。
- OpenAI API 当前不作为已配置真实能力；OpenAI-family coding 主路径是 Codex CLI。
- MiniMax / DeepSeek API 现在支持 direct coding proposal，并可通过 `workflowctl capability coding-apply` 在 `AutomationLease(coding_patch_apply)` 授权下受控应用 unified diff。
- MMX/MiniMax 的多模态生成能力是 M77 修复重点：image / speech / music 资产生成必须和文本 evidence 通道分离。
- Vertex 生成能力是 M77 修复重点：Imagen/Gemini image/visual review 走 Vertex AI API/SDK；Cloud Text-to-Speech 已拆为 `gcp_tts_api`，`gcloud` 只做认证和环境。
- Gemini CLI 暂未接入；Gemini-family 能力当前通过 Vertex/GCP 路径进入。
- `gcloud` 是 Vertex/GCP 凭据与环境工具，不是独立 worker adapter。
- OpenCode simple lane 默认使用 `minimax/MiniMax-M2.7`；当前不宣称 OMO / OpenCode 插件生态已集成。
- medium lane 可使用 `deepseek/deepseek-v4-flash`，失败时直接 fallback 到 Codex。
- LangChain 当前是 experimental / opt-in agent framework，不是默认 provider control plane。
- capability readiness 只接受 provider-specific live proof；simulated、dry-run、generic greeting、fallback-only 都不能标记为 `verified_ready`。
- Dynamic cluster routing 和 adaptive LLM routing 仍是 opt-in，不默认开启。
- Pipeline 是 `OrchestrationPlan` 之上的 plan-of-plans 产品层；当前执行器已禁止伪完成 capability stage，未真实执行会明确 `blocked`，复杂 mutation 仍通过既有 run/control-plane 语义落地。
- M79 已把 Cocos E2E 从 scaffold 推进到商业化 v1：生成真实 Cocos Creator 3.8 工程、编辑器可见 Scene/Node/Component/UI、SpriteFrame/AudioClip 绑定、动画/粒子/皮肤/关卡/道具入口，并完成 Web Mobile build 与浏览器 playtest。
- M80 已把 provider runtime truth 固化为可查询事实：`capability health --verified-only` 只展示 live proof 或真实成功调用支撑的能力，route stats 提供 30 天成功率、失败类型、延迟、fallback 和成本提示。
- M81 已新增通用 asset factory：style guide、prompt manifest、provenance、hash 去重、批量生成、失败重试、required asset NO-GO 和 Vertex visual QA。Cocos asset pipeline 现在消费 asset factory manifest。
- M82 已新增 active truth check，用于检查 README、issue register、tech debt 和 milestone history 是否与 evidence/commit 状态矛盾；本轮 dogfood 还修复了 DeepSeek direct API 对 `deepseek/...` 路由模型名的兼容问题。
- M83 的当前主线是可复用 `commercial_cocos_game` pipeline 模板。

## Architecture Map

```text
Operator
  |
  +-- CLI / API / Web UI
        |
        +-- OrchestratorService facade
              |
              +-- Core domain services
              |     +-- run lifecycle / review / evidence
              |     +-- operator action guard / scoped receipt
              |     +-- capability control plane
              |     +-- pipeline preview/run contracts
              |     +-- local scheduler lease arbiter
              |
              +-- Runtime and adapters
              |     +-- Shell / Codex / OpenCode / Claude
              |     +-- MMX-MiniMax / Vertex / LangChain
              |
              +-- Persistence and governance
                    +-- SQLite repositories
                    +-- task cards / evidence / operator packets
                    +-- tech debt registry / self-development manifest
```

## Quick Start

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

## Common CLI

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" doctor --strict
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run suggest-presets --goal "整理下一阶段计划"
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run plan-graph --goal "实现一个受控能力切片" --preset project_delivery
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run policy-preview --goal "实现一个受控能力切片" --preset project_delivery
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run goal-packet --goal "实现一个受控能力切片" --preset project_delivery
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider all --require-live --evidence-dir state/capability_probes
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability health --verified-only
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability routes stats --days 30
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" asset factory run --style-guide "premium neon casual puzzle" --manifest state/asset_factory/prompt_manifest.json --output-dir state/asset_factory/run
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" asset factory qa --asset-manifest state/asset_factory/run/asset_factory_manifest.json --evidence-dir state/asset_factory/qa
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" governance active-truth-check --strict --output-path state/governance/active_truth_check.json
```

Pipeline 入口：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline preview --goal "交付一个商业化 H5 小游戏"
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline run --goal "交付一个商业化 H5 小游戏" --execute-capabilities --pdf-path "C:\Users\74755\Desktop\俄罗斯方块消除策划文档4.2.pdf" --creator-exe "C:\ProgramData\cocos\editors\Creator\3.8.8\CocosCreator.exe" --require-build
```

Cocos E2E 入口：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" game cocos-e2e --pdf-path "C:\Users\74755\Desktop\俄罗斯方块消除策划文档4.2.pdf" --output-dir state/m79_cocos_commercial_pipeline/1010_block_puzzle_cocos_production --creator-exe "C:\ProgramData\cocos\editors\Creator\3.8.8\CocosCreator.exe" --require-build --generate-commercial-assets --require-commercial
```

## Workflow Dogfood Rules

- 一个 milestone 应包含多个 phase；一个 phase 默认包含多张 task card。
- task card 是最小可执行单元；单卡 phase 必须显式标记 `single_card_exception` 并说明理由。
- 每个 phase 前运行并保存 `plan-graph`、`policy-preview`、`goal-packet`。
- 简单低风险杂活优先交给 workflow + OpenCode/MiniMax；中等 review/validation 可走 DeepSeek V4 Flash；复杂架构、安全协议、repo mutation 使用 Codex 或本地补丁兜底。
- artifact-only 和 disjoint write_set task card 可以并发；write_set 冲突、dirty worktree、SQLite lock 或 repo mutation 异常时必须降级串行。
- workflow 自身 bug 优先级高于业务 phase：先登记、修复、补回归测试，再恢复原 phase。
- 成功 phase 可以 1 phase 1 commit；失败 phase 不提交，只保留 evidence 和恢复指针。

## Safety Boundaries

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

GET 请求不得产生状态变更。所有文件写入必须解析明确 workspace root；建议始终传 `--workspace-root` 或设置 `WORKFLOW_WORKSPACE_ROOT`。

## Validation

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
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider all --require-live --evidence-dir state/capability_probes
python -m pytest -q --run-slow
```

## M77-M80 Provider And Game Pipeline Update

- `vertex_imagen` and `vertex_gemini_review` now have Vertex AI REST wrappers and capability probes. They are only `verified_ready` after live probe success.
- `gcp_tts_api` is Google Cloud Text-to-Speech; legacy `vertex_tts` remains only as a compatibility alias.
- Local GCP probes prefer the active `gcloud auth print-access-token` user and fall back to ADC; set `WORKFLOW_GCP_AUTH_MODE=adc` to force ADC.
- `workflowctl game cocos-assets` generates a commercial asset manifest from MMX/MiniMax image, speech, music, GCP TTS voice, and optional Vertex Gemini visual review.
- M79 replaced the old scaffold with editor-visible Cocos production structure and strict commercial checks. M80 added provider route truth, M81 added the reusable asset factory used by the Cocos asset wrapper, and M82 adds `governance active-truth-check`. M83 turns the delivery path into a reusable pipeline template.
- `workflowctl capability health --verified-only` filters out descriptor-only readiness; `workflowctl capability routes stats --days 30` summarizes provider probe/runtime success, latency, failure classes, fallback policy, and cost hint.

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider vertex_imagen --require-live --evidence-dir state/m77_integrated_repair/live_probes/vertex_imagen
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider vertex_gemini_review --require-live --evidence-dir state/m77_integrated_repair/live_probes/vertex_gemini_review
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" game cocos-assets --output-dir state/m77_integrated_repair/cocos_assets
```
