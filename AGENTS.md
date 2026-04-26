# AGENTS.md

## 当前里程碑

当前接受基线是 `M72: Trusted Self-Development Baseline`。下一阶段建议进入 `M73` 能力层开发。

本仓库是个人自用 / local-first agentic workflow runtime，不是公开 SaaS、多租户平台、插件市场、自动 PR 发布器或外部托管执行服务。

## 开发规则

- 优先读取 `README.md`、`docs/current_development_workflow.md`、`M72_EXECUTION_REPORT.md` 和 `docs/governance/tech_debt_registry.json`。
- Milestone / phase / task card 必须保持三层语义：一个 milestone 包含多个 phase；一个 phase 默认包含多个 task card；task card 是最小可执行单元。
- 不要把“一 phase = 一 task card”作为默认模式。若某 phase 只有一张 task card，必须在 task card 或 operator packet 中写明 `single_card_exception`。
- phase 级 operator packet 必须汇总该 phase 内所有 task card 的 write_set、test commands、evidence 和阻塞项。
- 简单低风险任务优先通过 `workflowctl run from-task-card ... --adapter opencode --execute` 走 workflow；复杂安全协议和架构切片可以使用 Codex 或本地补丁兜底。
- bug-first：workflow、receipt、probe、evidence、route、repo mutation、test matrix 任一路径出 bug，先修 workflow bug 并补测试，再继续原 phase。
- 成功 phase 可 1 phase 1 commit；不要把多个 phase 或多个 milestone 压成一个 commit。

## 高风险动作边界

以下动作必须由统一策略判断后才能执行：

- `launch_execute`
- `resume_run`
- `approve_run`
- `reject_run`
- `cancel_run`
- `batch_resume_runs`
- repo mutation / patch apply
- watchdog auto-apply
- git commit / push / PR

高风险动作必须使用 scope-bound `OperatorActionReceipt`。GET 请求不得产生状态变更；`execute=true` 不得绕过 receipt 或 lease。

## 路由与 Provider 真实性

- 已接入：Codex、OpenCode、Claude、MMX/MiniMax、Vertex、LangChain、Shell/Noop。
- OpenCode 默认 simple lane 使用 `minimax/MiniMax-M2.7`。
- medium lane 可使用 `deepseek/deepseek-v4-flash`，失败时直接 fallback Codex。
- Gemini CLI 暂未接入；Gemini-family 能力当前通过 Vertex/GCP。
- `gcloud` 是 Vertex/GCP 凭据与环境工具，不是独立 worker adapter。
- capability readiness 只接受 provider-specific live proof。simulated、dry-run、generic greeting、fallback-only、非真实调用都不能标记为 `verified_ready`。

## 并发与编排

- 每个 phase 前运行 `plan-graph`、`policy-preview`、`goal-packet`。
- artifact-only 和 disjoint write_set task card 可以并发，最多 `batch-resume --max-workers 2`。
- write_set conflict、dirty write_set、SQLite lock 或 repo mutation 异常时必须降级串行。
- 复杂能力开发仍要保留 workflow route/evidence/operator-packet，即使实现由 Codex 或本地补丁完成。
