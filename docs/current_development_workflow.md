# 当前开发工作流

## Current Version: M67 Workflow-Dogfood Closeout

- Package version: `0.66.0`.
- Current accepted baseline: `M66`; active milestone: `M67`.
- M61-M66 planned closeout scope is retired, but M67 has reopened verified blocking debt. Do not claim project-wide zero debt until M67 closeout is green.
- Active truth set: [README.md](../README.md), [M67_ISSUE_REGISTER.md](../M67_ISSUE_REGISTER.md), [M67_EXECUTION_REPORT.md](../M67_EXECUTION_REPORT.md), this workflow guide, and the governance debt registry.
- Historical evaluations and older milestone plans/reports are archived under [docs/archive/evaluations/](archive/evaluations/); the root M66 evaluation files are temporary M67 inputs until closeout archival.
- Scheduler semantics are local-first. `LocalSchedulerLeaseArbiter` is the default local lease arbiter; `scheduler-authority` names are legacy compatibility surfaces unless the cluster flag is explicitly enabled.
- PR boundary is manual by default. The workflow may produce PR-ready summaries, but commit, push, and pull-request creation require explicit operator action.
- M67 maintainability ratchets are active: workflow dogfood evidence is required, high-risk authorization must be scope-bound, provider readiness must be live-proofed, and hot files must slim before feature expansion resumes.

## M67 Workflow-Dogfood Rules

- 每个 phase 都先写 task card 到 `state/m67_workflow_closeout/task_cards/`，再执行、记录 evidence、operator packet 和 checkpoint。
- 简单、低风险、边界清楚的任务优先用 `workflowctl run from-task-card ... --adapter opencode --execute`；复杂安全协议和架构变更允许 Codex 强模型或本地补丁兜底。
- 启用动态/自适应路由时，必须保存 route decision evidence；P8 closeout 需要 simple / medium / complex 三类真实任务和一次 `batch-resume --max-workers 2`。
- bug-first 优先级高于 phase 进度：workflow、receipt、probe、evidence、route、repo mutation 任一自身出 bug，先登记并修复 workflow bug，再恢复原 phase。
- 从 M67 起恢复 1 phase 1 commit；不要再用单个 commit 压缩多个 milestone 或 phase。

## M48-M51 Recovery Rules

- `M48_M51_RECOVERY_PLAN.md` has been absorbed into the M61-M66 issue register and archived as historical recovery evidence.
- `pyproject.toml` no longer pins a shared pytest basetemp. Use `make test-fast`, `make test-core`, or `make test-full` for unique temp directories.
- `workflowctl --db-path state/workflow.db doctor --strict` is the strict preflight form; any issue returns a non-zero exit code.
- File mutation must resolve an explicit workspace root from `--workspace-root`, `WORKFLOW_WORKSPACE_ROOT`, config, or cwd fallback in that order.
- High-risk API actions require `OperatorActionReceipt`; receipts must match action/workspace, be unexpired, and be consumed once.
- Capability health reads the `capability_invocations` runtime ledger, so recent success/failure counts reflect real executions rather than descriptor-only readiness.

## M52-M60 Bug-First Carry-Forward

- Scheduler flag-off construction must stay local-only: `packages.core_domain.scheduler_authority` is not imported unless `WORKFLOW_SCHEDULER_AUTHORITY_CLUSTER_ENABLED=1`.
- Orchestrator facade ratchets are active: `OrchestratorService` direct methods must stay at or below 140, with scheduler and worker-callback logic owned by dedicated mixins.
- Web/API local security boundaries include CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and receipt gates for high-risk actions.
- Remote worker callback origins are allowlisted. Without an explicit allowlist, only loopback/private callback hosts are accepted; public callback origins are rejected before execution/callback dispatch.
- Capability health now exposes `readiness_state`, `runtime_ledger_summary`, `provider_route`, and `fallback_route`; `status=ready` alone is not enough to claim a capability was recently verified.
- Cluster route markers live in `infra/seeds/cluster_route_markers.json`; dynamic cluster routing remains opt-in through `WORKFLOW_DYNAMIC_CLUSTER_ROUTING_ENABLED=1`.
- Preferred local validation entrypoints are `make test-unit`, `make test-core`, `make test-integration`, and `make test-full`; on Windows shells without `make`, run the equivalent `python -m pytest ...` commands from `Makefile`.

本文档是后续开发的最高优先级操作说明。项目当前仍然是个人自用的本地 operator runtime；所有计划、文档和验证都服务于“我能不能稳定继续使用它”，而不是服务外部用户、公开 SaaS、开源 onboarding 或第三方生态。

## 活跃真相源

判断当前状态时只看以下文件：

1. [README.md](../README.md)
2. [docs/current_development_workflow.md](current_development_workflow.md)
3. [docs/milestone_history.md](milestone_history.md)
4. [docs/tech-debt-registry.md](tech-debt-registry.md)
5. [docs/governance/tech_debt_registry.json](governance/tech_debt_registry.json)
6. [M67_ISSUE_REGISTER.md](../M67_ISSUE_REGISTER.md)
7. [M67_EXECUTION_REPORT.md](../M67_EXECUTION_REPORT.md)
8. [M61_M66_ISSUE_REGISTER.md](../M61_M66_ISSUE_REGISTER.md)
9. [M61_M66_EXECUTION_REPORT.md](../M61_M66_EXECUTION_REPORT.md)

关闭阶段的 phase docs、task cards、freeze reviews、archive、M2M 交接计划和重复根目录计划不再是活跃真相源。需要历史细节时从 git 历史查看，不恢复到工作树。

## 当前仓库状态

- 最新接受基线：`M66`
- 当前工作里程碑：`M67`
- 当前产品前提：个人自用 / 本地 operator runtime
- 当前主入口：CLI、API、Web operator console、`/ui/workbench`
- 当前 workbench 形态：LLM-assisted streaming chat workbench，主区域只显示真实对话、assistant delta/final 和确认卡；右侧显示 session、active run、graph node、evidence、review 和 PR-ready summary
- 当前 stream 形态：SSE chat event stream，聊天 transcript 使用 `user_message`、`assistant_delta`、`assistant_final`、`confirmation_required`、`confirmation_result`、`error`；状态卡使用 `graph_update`、`run_update`、`status_patch`、`timeline_event`、`review_required`、`test_evidence`、`pr_ready_summary`、`heartbeat`
- 当前确认规则：`resume_run`、`approve_run`、`reject_run`、`cancel_run`、`launch_execute`、repo mutation、git commit/push/PR 必须通过确认卡
- 当前测试分层：默认 `pytest -q` 是快速核心回归；完整 `pytest -q --run-slow` 只在每个 M 收口运行一次
- 当前自适应路由：默认关闭；开启 `WORKFLOW_ADAPTIVE_LLM_ROUTING_ENABLED=1` 后，简单角色优先 MiniMax，中等 review/planning 优先 DeepSeek V4 Flash，复杂 coder 优先 OpenCode + MiniMax
- 当前动态编排：默认关闭；开启 `WORKFLOW_DYNAMIC_CLUSTER_ROUTING_ENABLED=1` 后，复杂目标可组合多模态、搜索、设计、开发和 review 集群

## Phase / Task 协议

日常 plan / phase / task 以 `state/workflow.db` 中的 `runs`、`phases`、`task_cards`、`runtime_tasks`、`run_events` 和 evidence 为主记录。Markdown 只保留三类用途：`examples/local_task_cards/` 的手工导入示例、阶段收口后的摘要、以及需要人工审阅的少量活跃文档。

1. 新 M 或 active phase 优先创建 DB run / phase / task-card 记录。
2. 执行时同步记录真实结果、run id、artifact path 和失败/fallback 证据。
3. 需要人工交接时从 DB 导出临时 Markdown，不作为长期事实源。
4. 收口时只把结论吸收到 README、当前工作流、里程碑历史和技术债文档。
5. 关闭阶段的详细 phase/task 临时材料默认删除或保留在 git 历史中，不恢复到工作树。

DB 保留策略：当前 `state/workflow.db` 体量很小，日常开发不需要按天清理。后续只在 DB 超过约 200MB、run 数明显堆积、或 chat stream / run event 查询变慢时做归档式清理；保留最近活跃 session、已接受 M 的摘要证据和 release-ready 结果，优先清理旧的 failed/superseded attempt、重复 stream event 和临时 artifact 引用。

## Agent / Cluster 现状

M42 后，系统具备以下可路由角色集群：

- `dev_cluster`：软件交付默认集群，覆盖 planner、coder、risk mapper、quality gate、launch guard。
- `research_cluster`：研究与证据集群，覆盖 research analyst、citation checker、launch guard。
- `architecture_delivery_cluster`：M41 dogfood 主链路，顺序为 `multimodal_evidence -> planner_design -> claude_architect_gate -> phase_designer -> implementer -> quality_gate -> doc_curator -> launch_guard`。
- `search_cluster`：资料检索、来源追踪、证据综合和引用核验。
- `design_cluster`：产品方向、交互/视觉方案和设计审查。
- `multimodal_cluster`：PDF、图片、截图、设计稿等多模态 evidence 入口，MMX 优先，Vertex 作为未来 fallback。
- `review_cluster`：质量门、测试哨兵、治理哨兵和中文文档收口。
- `management_cluster`：roadmap、phase/task、治理和 closeout 管理。

强 dogfood 模式下，M42 专用集群里的核心 `agent` 角色默认解析为 Codex CLI：

```powershell
$env:WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED="1"
$env:WORKFLOW_DOGFOOD_EXECUTION_BACKEND="codex_cli"
$env:WORKFLOW_DOGFOOD_MODEL="gpt-5.5"
$env:WORKFLOW_DOGFOOD_REASONING_EFFORT="xhigh"
```

外部 artifact-only 能力保持单独角色：`mmx_multimodal`、`vertex_multimodal`、`claude_architect`。这些能力失败时必须记录 degraded/fallback 证据，不允许静默成功。

## M42 收口结论

M42 已完成以下能力补全：

- 新增并注册 `search_cluster`、`design_cluster`、`multimodal_cluster`、`review_cluster`、`management_cluster`。
- 扩展 router，使中文/英文目标可以推荐对应专用集群，同时保留 `architecture_delivery_cluster` 的最高优先级。
- 扩展 dogfood execution resolution，使 M42 专用集群的核心 agent roles 在强 dogfood + `codex_cli` 后端下投影为 `dogfood_strong_codex_cli`。
- 修复 Codex CLI 在 Windows 上可能遗留 node/native 子进程的问题：真实 Codex 执行现在使用进程树 timeout 清理。
- 完成一次真实 `management_cluster` dogfood smoke：`run_665006c2016d`，根 run `completed`；Codex 子 run 在 8 秒左右硬超时后被标记 failed，再由 shell fallback 完成，且无残留 `codex.exe`。

仍需后续关注：

- MMX/Vertex 多模态真实提取还需要用真实 PDF/图片输入继续验收。
- Claude architect gate 目前仍以 quota-guarded / artifact-only 骨架为主，不能高频使用。
- Codex artifact-only reviewer/doc curator 仍可能偏慢，进程树 timeout 已降低卡死风险，但 prompt 还可以继续收缩。
- `OrchestratorService` 仍偏大，后续 M 应继续抽离 interaction/chat/projection/lifecycle glue。

## M43-M47 收口结论

M43-M47 已完成一次新的长程闭环：

- M43：读取 `C:\Users\74755\Desktop\俄罗斯方块消除策划文档4.2.pdf`，通过 workflow artifact 路径生成 [方块艺境示例](../examples/block_puzzle_shop/index.html)，覆盖真实拖拽、触控拖动、防遮挡 ghost、放置预览、广告复活、三类道具、皮肤/背景/棋盘装饰、拼图收集、经典模式和前 7 关闯关。
- M44：新增自适应 LLM 路由配置和投影字段，默认关闭；启用后按 simple/medium/complex 路由到 MiniMax、DeepSeek V4 Flash 和 OpenCode。
- M45：新增动态多集群 opt-in 路由，复杂 PDF 游戏目标可组合 `multimodal_cluster -> search_cluster -> design_cluster -> dev_cluster -> review_cluster`。
- M46：扩展 doctor/status 可见性，并修复动态 route 在 status detail 中只显示第一个 cluster graph 的问题。
- M47：更新中文文档、回归验证、git 推送后停止。

M43 真实 evidence：

- PDF trace：[examples/block_puzzle_shop/design_trace.md](../examples/block_puzzle_shop/design_trace.md)
- 浏览器 smoke：`state/m43_block_puzzle_e2e/block_puzzle_shop_smoke.png`
- 动态编排 smoke：`state/m46_dynamic_adaptive_smoke/summary.json`

保留边界：

- M43 的“多模态”先以本地 PDF text extraction 跑通，不声称 MMX/Vertex 已承担主路径。
- 自适应路由与动态编排都是 opt-in；默认路径继续保持稳定优先。
- 静态 HTML 游戏是 vertical slice，不是完整上线工程。

## 验证规则

文档或代码变更后至少运行：

```powershell
python -m infra.scripts.check_doc_links
```

涉及运行路径、API、UI、验证脚本或活跃真相源时再运行：

```powershell
python -m infra.scripts.offline_validation --skip-offline-probe
pytest -q
```

每个 M 收口时运行一次完整慢测试：

```powershell
pytest -q --run-slow
```

普通 phase closeout 或 CLI/API/Web 改动只跑相关定点 slow 用例，避免每个小阶段都压全量慢测。
