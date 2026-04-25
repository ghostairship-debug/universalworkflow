# AGENTS.md

## 当前里程碑

当前 active milestone 是 `M67: Workflow-Dogfood 可信收口`。

本仓库是个人自用 / local-first agentic workflow runtime，不是公开 SaaS、多租户平台、插件市场、自动 PR 发布器或外部托管执行服务。

## M67 工作规则

- 优先读取 `README.md`、`docs/current_development_workflow.md`、`M67_ISSUE_REGISTER.md`、`M67_EXECUTION_REPORT.md` 和 `docs/governance/tech_debt_registry.json`。
- 每个 phase 先创建 task card，再执行，再记录 evidence、operator packet、checkpoint。
- Milestone / phase / task card 必须保持三层语义：一个 milestone 包含多个 phase；一个 phase 默认包含多个 task card；task card 才是最小可执行单元。
- 不要把“一个 phase = 一个 task card”作为默认模式。若某 phase 只有一个 task card，必须满足其确实是原子 bugfix / closeout gate / 单一验证切片，并在 task card 或 operator packet 中写明 `single_card_exception`；否则应拆成多个 task card，或并入相邻 phase。
- phase 级 operator packet 必须汇总本 phase 内所有 task card 的 write_set、test commands、evidence 和阻塞项；允许一个 phase 一个 commit，但 commit 应代表 phase 收口，而不是把 task card 粗暴升格为 phase。
- 简单低风险任务优先通过 `workflowctl run from-task-card ... --adapter opencode --execute` 走 workflow；复杂安全协议和架构切片可以使用 Codex 或本地补丁兜底。
- bug-first：workflow、receipt、probe、evidence、route、repo mutation、test matrix 任一路径出 bug，先修 workflow bug 并补测试，再继续原 phase。
- 从 M67 起恢复 1 phase 1 commit；不要把多个 phase 或多个 milestone 压成一个 commit。

## 高风险动作边界

高风险或状态变更动作必须由统一策略判断后才能执行。至少包括：

- `launch_execute`
- `resume_run`
- `approve_run`
- `reject_run`
- `cancel_run`
- `batch_resume_runs`
- repo mutation / patch apply
- watchdog auto-apply
- git commit / push / PR

M67 期间的目标是把 `OperatorActionReceipt` 升级为 scope-bound confirmation，并开始收敛 Command / PolicyEngine / AutomationLease 语义。`GET` 请求不得产生状态变更；`execute=true` 不得绕过 receipt 或 lease。

## 路由与 Provider 真实性

自适应路由和动态 cluster routing 是 M67 必测对象，不是文档假设。M67 closeout 至少需要：

- simple task 路由到 `opencode + minimax/MiniMax-M2.7`
- medium task 产生可审计 adaptive route evidence
- complex architecture/review task 产生 cluster route + fallback evidence
- 一次 `batch-resume --max-workers 2` 成功 evidence

capability readiness 只接受 provider-specific live proof。simulated、dry-run、generic greeting、fallback-only、非真实调用都不能标记为 `verified_ready`。
