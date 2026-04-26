# 当前开发工作流

## Current Version: M72 Trusted Self-Development Baseline

- Package version: `0.66.0`.
- Accepted baseline: `M72`.
- Next recommended milestone: `M73` capability-layer development.
- Active truth set: [README.md](../README.md), [M72_EXECUTION_REPORT.md](../M72_EXECUTION_REPORT.md), this workflow guide, [milestone history](milestone_history.md), and the governance debt registry.
- Historical evaluations, long-term roadmaps, old recovery plans, and prior duplicate root docs are archived under [docs/archive/evaluations/](archive/evaluations/).
- Scheduler semantics are local-first. `LocalSchedulerLeaseArbiter` is the default local lease arbiter; `scheduler-authority` names are legacy compatibility surfaces unless the cluster flag is explicitly enabled.
- PR publication remains manual. The workflow may produce PR-ready summaries, but commit, push, and pull-request creation require explicit operator action.

本文档是后续开发的最高优先级操作说明。项目仍然是个人自用的本地 operator runtime；所有计划、文档和验证都服务于“我能不能稳定继续使用它”，不服务于外部 SaaS、多租户、公开 onboarding 或第三方生态。

## M73+ Development Rules

- 新能力开发可以恢复，但必须继续使用 workflow 共同开发。
- 一个 milestone 应包含多个 phase；一个 phase 默认应包含多张 task card；task card 是最小可执行单元。
- 单卡 phase 必须显式写入 `single_card_exception`，并说明为什么不能拆分。
- 每个 phase 之前运行 `plan-graph`、`policy-preview`、`goal-packet` 并保存 evidence。
- 每个 phase 至少生成 task cards、route evidence、test evidence、operator packet 和 closeout summary。
- workflow/dogfood/receipt/probe/evidence/route/repo mutation/test matrix 任一路径出 bug，先修 workflow bug 并补回归测试，再继续原 phase。
- artifact-only 与 disjoint write_set 任务可以并发；patch apply 只有 write_set 不相交时才能并发，最多 `--max-workers 2`。
- SQLite lock、dirty worktree 命中 write_set、write_set conflict 或 repo mutation 异常时自动降级串行。
- 成功 phase 可 1 phase 1 commit；失败 phase 不提交，只保留 evidence 和恢复指针。

## Routing Defaults

- simple 杂活：OpenCode + `minimax/MiniMax-M2.7`，失败后可试 OpenCode + `deepseek/deepseek-v4-flash`，最终 fallback Codex。
- medium review / validation / security：优先 `deepseek/deepseek-v4-flash`，失败直接 fallback Codex。
- complex 架构、安全协议、repo mutation：Codex 或本地补丁兜底；workflow 仍负责 task card、route/evidence、operator packet。
- Gemini CLI 暂不接入；Gemini-family 能力短期通过 Vertex/GCP。
- `gcloud` 是 Vertex/GCP 凭据与环境工具，不是独立 worker adapter。

## Capability Truth

- Capability health 必须来自 runtime ledger / live probe，而不是 descriptor 自我声明。
- `verified_ready` 或 `recently_successful` 只能由真实 provider-specific live proof 产生。
- simulated、dry-run、generic greeting、fallback-only、非真实调用不能标记为 ready。
- `workflowctl capability probe --provider all --require-live` 是能力 closeout 的硬门禁。

## High-Risk Action Boundary

以下动作必须由 scope-bound `OperatorActionReceipt` 授权，并且消费时校验实际 request scope：

- `launch_execute`
- `resume_run`
- `approve_run`
- `reject_run`
- `cancel_run`
- `batch_resume_runs`
- repo mutation / patch apply
- watchdog auto-apply
- git commit / push / PR

GET 请求不得触发状态变更。所有文件写入必须解析明确 workspace root。

## Current Truth Sources

判断当前状态时只看：

1. [README.md](../README.md)
2. [docs/current_development_workflow.md](current_development_workflow.md)
3. [docs/milestone_history.md](milestone_history.md)
4. [docs/tech-debt-registry.md](tech-debt-registry.md)
5. [docs/governance/tech_debt_registry.json](governance/tech_debt_registry.json)
6. [M72_EXECUTION_REPORT.md](../M72_EXECUTION_REPORT.md)

关闭阶段的 phase docs、临时 task cards、freeze reviews、旧 roadmap、旧评估报告和重复根目录计划不再是活跃真相源。需要历史细节时查看 git 历史或 [archive](archive/evaluations/)。

## Validation Rules

文档或说明变更至少运行：

```powershell
python -m infra.scripts.check_doc_links
```

涉及运行路径、API、UI、验证脚本或活跃真相源时追加：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite unit
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite core
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite integration
```

每个 milestone closeout 运行：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" validation run --suite full --skip-offline-probe
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider all --require-live --evidence-dir state/<milestone>/capability_probes
python -m pytest -q --run-slow
```
