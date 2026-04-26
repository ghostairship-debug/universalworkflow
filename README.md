# Universal Agentic Workflow OS

## Current Version: M77 Provider Access Repair In Progress

- Package version: `0.66.0`.
- Accepted baseline: `M76`; active repair entry: [M77+ integrated repair and development plan](M77_PLUS_INTEGRATED_REPAIR_AND_DEVELOPMENT_PLAN.md).
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
- Cocos E2E 现在区分技术 smoke 和商业化验收；`--require-commercial` 缺真实美术/音效/UI/动画/粒子/皮肤/关卡闭环时会明确 NO-GO。

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
```

Pipeline 入口：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline preview --goal "交付一个商业化 H5 小游戏"
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline run --goal "交付一个商业化 H5 小游戏"
```

Cocos E2E 入口：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" game cocos-e2e --pdf-path "C:\Users\74755\Desktop\俄罗斯方块消除策划文档4.2.pdf" --output-dir state/m73_m76_autopilot/cocos_e2e/1010_block_puzzle_cocos --creator-exe "C:\ProgramData\cocos\editors\Creator\3.8.8\CocosCreator.exe" --require-build
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

## M77 Provider And Game Pipeline Update

- `vertex_imagen` and `vertex_gemini_review` now have Vertex AI REST wrappers and capability probes. They are only `verified_ready` after live probe success.
- `gcp_tts_api` is Google Cloud Text-to-Speech; legacy `vertex_tts` remains only as a compatibility alias.
- Local GCP probes prefer the active `gcloud auth print-access-token` user and fall back to ADC; set `WORKFLOW_GCP_AUTH_MODE=adc` to force ADC.
- `workflowctl game cocos-assets` generates a commercial asset manifest from MMX/MiniMax image, speech, music, GCP TTS voice, and optional Vertex Gemini visual review.
- `workflowctl game cocos-e2e --generate-commercial-assets --require-commercial` can feed generated assets into the commercial gate, but native Cocos UI nodes, animation timeline, and real level-switching UI remain future game-body work.

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider vertex_imagen --require-live --evidence-dir state/m77_integrated_repair/live_probes/vertex_imagen
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider vertex_gemini_review --require-live --evidence-dir state/m77_integrated_repair/live_probes/vertex_gemini_review
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" game cocos-assets --output-dir state/m77_integrated_repair/cocos_assets
```
