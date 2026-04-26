# Universal Agentic Workflow OS

## Current Version: M72 Trusted Self-Development Baseline

- Package version: `0.66.0`.
- Accepted baseline: `M72`.
- Next recommended milestone: `M73` capability-layer development.
- Status: M67-M72 trusted closeout is complete. The project may resume capability work, but every new capability milestone must keep workflow dogfood, scoped receipts, live provider proof, evidence, and bug-first gates active.
- Current closeout entrypoint: [M72_EXECUTION_REPORT.md](M72_EXECUTION_REPORT.md).
- Machine-checkable self-development manifest: `workflowctl governance self-development-manifest`.
- Historical evaluations, old recovery plans, long-term roadmaps, and prior execution reports live under [docs/archive/evaluations/](docs/archive/evaluations/).
- Scheduler semantics are local-first: `LocalSchedulerLeaseArbiter` is the default local lease arbiter. `scheduler-authority` names remain only for legacy compatibility and explicit cluster-on surfaces.
- GitHub/PR boundary: the workflow can generate PR-ready summaries, but it does not commit, push, or open a pull request unless the operator explicitly runs those actions.

这是一个个人自用的本地 agentic workflow runtime。当前目标不是公开 SaaS、多用户平台、安装器、外部 onboarding 或插件市场，而是让拥有者自己的代码、研究、设计、审查和自动化工作流可以长期稳定、可恢复、可审计地运行。

## Active Truth Set

后续开发优先看这些文件：

- [当前开发工作流](docs/current_development_workflow.md)
- [里程碑历史摘要](docs/milestone_history.md)
- [技术债登记表](docs/tech-debt-registry.md)
- [结构化技术债 JSON](docs/governance/tech_debt_registry.json)
- [M72 执行报告](M72_EXECUTION_REPORT.md)

历史 phase docs、task cards、freeze reviews、archive、M2M 交接材料和旧根目录计划不再作为活跃真相源。需要逐字历史时查 git 历史或 [docs/archive/evaluations/](docs/archive/evaluations/)。

## Current State

- 主入口：CLI、API、Web operator console、`/ui/workbench` streaming chat workbench。
- provider 事实：已接入 Codex、OpenCode、Claude、MMX/MiniMax、Vertex、LangChain、Shell/Noop。
- Gemini CLI 暂未接入；Gemini-family 能力当前通过 Vertex/GCP 路径进入。
- `gcloud` 是 Vertex/GCP 凭据与环境工具，不是独立 worker adapter。
- OpenCode 默认 simple lane 可用 `minimax/MiniMax-M2.7`。
- medium lane 可用 `deepseek/deepseek-v4-flash`，失败时直接 fallback 到 Codex。
- capability readiness 只接受 provider-specific live proof；simulated、dry-run、generic greeting、fallback-only 都不能标记为 `verified_ready`。
- 动态 cluster routing 和 adaptive LLM routing 仍是 opt-in，不默认开启。

## Quick Start

```powershell
pip install -e ".[dev]"
python -m infra.scripts.manage --db-path state/workflow.db reset-db
python -m infra.scripts.manage --db-path state/workflow.db smoke
```

启动 Web operator console：

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
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" governance self-development-manifest
```

本地 task card 闭环：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run from-task-card examples/local_task_cards/01_safe_doc_patch.md --write-set README.md --test-command "python -m infra.scripts.check_doc_links" --execute
```

## Workflow Dogfood Rules

- 一个 milestone 应包含多个 phase；一个 phase 默认应拆成多张 task card；task card 是最小可执行单元。
- 单卡 phase 必须显式标记 `single_card_exception`，否则应拆分或合并到相邻 phase。
- 每个 phase 前运行 route preview：`plan-graph`、`policy-preview`、`goal-packet`。
- 简单低风险杂活优先交给 workflow + OpenCode/MiniMax；中等 review/validation 任务可走 DeepSeek V4 Flash；复杂架构、安全协议、repo mutation 由 Codex 或本地补丁兜底。
- artifact-only 和 disjoint write_set task card 可并发；write_set 冲突、dirty worktree、SQLite lock 或 repo mutation 异常时必须降级串行。
- workflow 自身 bug 优先级高于业务 phase：先登记、修复、补回归测试，再恢复原 phase。
- 成功 phase 可 1 phase 1 commit；失败 phase 不提交，只保留 evidence。

## Safety Boundaries

高风险动作必须通过 scope-bound `OperatorActionReceipt`：

- `launch_execute`
- `resume_run`
- `approve_run`
- `reject_run`
- `cancel_run`
- `batch_resume_runs`
- repo mutation / patch apply
- watchdog auto-apply
- git commit / push / PR

GET 请求不得产生状态变更。所有文件写入必须解析明确 workspace root；推荐始终传 `--workspace-root` 或设置 `WORKFLOW_WORKSPACE_ROOT`。

## Validation

日常文档/说明变更：

```powershell
python -m infra.scripts.check_doc_links
```

常规开发收口：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite unit
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite core
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite integration
```

Milestone closeout：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" validation run --suite full --skip-offline-probe
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider all --require-live --evidence-dir state/<milestone>/capability_probes
python -m pytest -q --run-slow
```
