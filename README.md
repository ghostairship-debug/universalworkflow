# Universal Agentic Workflow OS

## Current Version: M76 Workflow Pipeline And Cocos E2E Closeout

- Package version: `0.66.0`.
- Accepted baseline: `M76`.
- Current closeout entrypoint: [M73-M76 执行报告](M73_M76_EXECUTION_REPORT.md).
- Current development plan: [M73-M76 最终开发方案](FINAL_DEVELOPMENT_PLAN_M73_M76.md).
- Beginner overview: [项目全景介绍](PROJECT_OVERVIEW_FOR_BEGINNERS.md).
- Governance source of truth: [structured tech debt registry](docs/governance/tech_debt_registry.json).

Universal Agentic Workflow 是一个本地优先的 agentic workflow runtime。它的目标不是公开 SaaS、多租户平台或插件市场，而是让个人开发者可以把 AI、CLI、代码仓库、测试、审查、证据和自动化任务组织成可恢复、可审计、可长期推进的工作流。

## Active Truth Set

后续开发优先参考这些文件：

- [当前开发工作流](docs/current_development_workflow.md)
- [里程碑历史](docs/milestone_history.md)
- [技术债登记表](docs/tech-debt-registry.md)
- [结构化技术债 JSON](docs/governance/tech_debt_registry.json)
- [M73-M76 执行报告](M73_M76_EXECUTION_REPORT.md)
- [M76 后深度评估 R1](M76_POST_CLOSEOUT_DEEP_EVALUATION_R1.md)
- [M76 后深度评估 R2](M76_POST_CLOSEOUT_DEEP_EVALUATION_R2.md)

历史评估、旧恢复计划、旧路线图和重复根目录材料应归档到 [docs/archive/evaluations/](docs/archive/evaluations/)。需要逐字历史时看 git 历史；当前判断以 Active Truth Set 为准。

## Current State

- 入口：CLI、API、Web operator console、`/ui/workbench` streaming chat workbench。
- 已接入 provider/adapter：Codex、OpenCode、Claude、MMX/MiniMax、Vertex、LangChain、Shell/Noop。
- Gemini CLI 暂未接入；Gemini-family 能力当前通过 Vertex/GCP 路径进入。
- `gcloud` 是 Vertex/GCP 凭据与环境工具，不是独立 worker adapter。
- OpenCode simple lane 默认使用 `minimax/MiniMax-M2.7`。
- medium lane 可使用 `deepseek/deepseek-v4-flash`，失败时直接 fallback 到 Codex。
- capability readiness 只接受 provider-specific live proof；simulated、dry-run、generic greeting、fallback-only 都不能标记为 `verified_ready`。
- Dynamic cluster routing 和 adaptive LLM routing 仍是 opt-in，不默认开启。
- Pipeline 是 `OrchestrationPlan` 之上的 plan-of-plans 产品层；当前最小执行支持串行 stage，复杂 mutation 仍通过既有 run/control-plane 语义落地。

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
