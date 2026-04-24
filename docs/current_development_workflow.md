# 当前开发工作流

本文档是后续开发的最高优先级操作说明。项目当前仍然是个人自用的本地 operator runtime；所有计划、文档和验证都服务于“我能不能稳定继续使用它”，而不是服务外部用户、公开 SaaS、开源 onboarding 或第三方生态。

## 活跃真相源

判断当前状态时只看以下文件：

1. [README.md](../README.md)
2. [docs/current_development_workflow.md](current_development_workflow.md)
3. [docs/milestone_history.md](milestone_history.md)
4. [docs/tech-debt-registry.md](tech-debt-registry.md)
5. [docs/governance/tech_debt_registry.json](governance/tech_debt_registry.json)
6. [M38_REPAIR_AND_DEVELOPMENT_PLAN.md](../M38_REPAIR_AND_DEVELOPMENT_PLAN.md)
7. [PROJECT_DEEP_EVALUATION_M37.md](../PROJECT_DEEP_EVALUATION_M37.md)

关闭阶段的 phase docs、task cards、freeze reviews、archive、M2M 交接计划和重复根目录计划不再是活跃真相源。需要历史细节时从 git 历史查看，不恢复到工作树。

## 当前仓库状态

- 最新接受基线：`M42`
- 当前产品前提：个人自用 / 本地 operator runtime
- 当前主入口：CLI、API、Web operator console、`/ui/workbench`
- 当前 workbench 形态：LLM-assisted streaming chat workbench，主区域只显示真实对话、assistant delta/final 和确认卡；右侧显示 session、active run、graph node、evidence、review 和 PR-ready summary
- 当前 stream 形态：SSE chat event stream，聊天 transcript 使用 `user_message`、`assistant_delta`、`assistant_final`、`confirmation_required`、`confirmation_result`、`error`；状态卡使用 `graph_update`、`run_update`、`status_patch`、`timeline_event`、`review_required`、`test_evidence`、`pr_ready_summary`、`heartbeat`
- 当前确认规则：`resume_run`、`approve_run`、`reject_run`、`cancel_run`、`launch_execute`、repo mutation、git commit/push/PR 必须通过确认卡
- 当前测试分层：默认 `pytest -q` 是快速核心回归；完整 `pytest -q --run-slow` 只在每个 M 收口运行一次

## Phase / Task 协议

每个新 M 或 active phase 按 task-card 协议推进：

1. 先写当前 phase doc。
2. 再写当前 phase task-card index。
3. 再写必要的 detailed task cards。
4. 执行时同步记录真实结果、run id、artifact path 和失败/fallback 证据。
5. 收口时把结论吸收到 README、当前工作流、里程碑历史和技术债文档。
6. 关闭阶段的详细 phase/task 临时材料默认删除或不再作为活跃真相源。

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
