# 当前开发工作流

## Current Version: M76 Workflow Pipeline And Cocos E2E Closeout

- Package version: `0.66.0`.
- Accepted baseline: `M76`.
- Active truth set: [README.md](../README.md), this workflow guide, [milestone history](milestone_history.md), [tech debt registry](tech-debt-registry.md), and [structured governance registry](governance/tech_debt_registry.json).
- Historical evaluations, long-term roadmaps, old recovery plans, stage reports, and duplicate root docs are removed from the active worktree. Use git history for exact archival text.
- Scheduler semantics are local-first. `LocalSchedulerLeaseArbiter` is the default local lease arbiter; `scheduler-authority` names are legacy compatibility surfaces unless the cluster flag is explicitly enabled.
- PR publication remains manual unless the operator explicitly asks for commit, push, or PR creation.

本文档是后续开发的最高优先级操作说明。项目当前仍是个人自用、本地优先的 operator runtime；所有计划、文档和验证都服务于“能否稳定继续使用它”，不服务于外部 SaaS、多租户、公开 onboarding 或第三方生态。

## M76+ Development Rules

- 新能力开发可以恢复，但必须继续使用 workflow 共同开发。
- 一个 milestone 应包含多个 phase；一个 phase 默认应包含多张 task card，task card 是最小可执行单元。
- 单卡 phase 必须显式写入 `single_card_exception`，并说明为什么不能拆分。
- 每个 phase 前运行 `plan-graph`、`policy-preview`、`goal-packet` 并保存 evidence。
- 每个 phase 至少输出 task cards、route evidence、test evidence、operator packet 和 closeout summary。
- workflow、dogfood、receipt、probe、evidence、route、repo mutation、test matrix 任一路径出现 bug，先修 workflow bug 并补回归测试，再继续原 phase。
- artifact-only 与 disjoint write_set 任务可以并发；patch apply 只有 write_set 不相交时才能并发，最多 `--max-workers 2`。
- SQLite lock、dirty worktree 命中 write_set、write_set conflict 或 repo mutation 异常时自动降级串行。
- 成功 phase 可以 1 phase 1 commit；失败 phase 不提交，只保留 evidence 和恢复指针。

## Routing Defaults

- simple 杂活：OpenCode + `minimax/MiniMax-M2.7`；失败后可试 OpenCode + `deepseek/deepseek-v4-flash`；最终 fallback Codex。
- medium review / validation / security：优先 `deepseek/deepseek-v4-flash`；失败直接 fallback Codex。
- complex 架构、安全协议、repo mutation：Codex 或本地补丁兜底；workflow 仍负责 task card、route evidence 和 operator packet。
- Gemini CLI 暂不接入；Gemini-family 能力短期通过 Vertex/GCP。
- `gcloud` 是 Vertex/GCP 凭据与环境工具，不是独立 worker adapter。

## Capability Truth

- Capability health 必须来自 runtime ledger / live probe，而不是 descriptor 自我声明。
- `verified_ready` 或 `recently_successful` 只能由真实 provider-specific live proof 产生。
- simulated、dry-run、generic greeting、fallback-only、非真实调用不能标记为 ready。
- `workflowctl capability probe --provider all --require-live` 是能力 closeout 的硬门禁。

## High-Risk Action Boundary

以下动作必须由 scope-bound `OperatorActionReceipt` 或明确的 `AutomationLease` 授权，并且消费时校验实际 request scope：

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

## Pipeline Rules

- `WorkflowPipeline` 是 `OrchestrationPlan` 之上的 plan-of-plans，不是 cluster 的别名。
- Pipeline stage 类型固定为 `agent_role | cluster | capability | human_checkpoint | sub_pipeline | validation_gate | external_worker`。
- Pipeline preview 不直接 mutation；execution 当前只支持受控串行 stage，复杂写入仍走既有 run/control-plane。
- H5 游戏商业化是正式业务需求，应作为 pipeline 场景承载，而不是新增一堆 `game_*_cluster`。

## Validation Rules

文档变更至少运行：

```powershell
python -m infra.scripts.check_doc_links
```

涉及运行路径、API、UI、验证脚本或活跃真相源时追加：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite unit
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite core
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite integration
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" validation run --suite full --skip-offline-probe
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider all --require-live --evidence-dir state/<milestone>/capability_probes
python -m pytest -q --run-slow
```
