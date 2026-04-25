# Universal Agentic Workflow OS

## Current Version: M67 Workflow-Dogfood Closeout

- Package version: `0.66.0`.
- Current accepted baseline: `M66`; active milestone: `M67`.
- Status: M67 is an active bug-first trusted-closeout milestone. The M61-M66 planned scope closed, but current verified debt is not zero.
- Current closeout entrypoints: [M67_ISSUE_REGISTER.md](M67_ISSUE_REGISTER.md) and [M67_EXECUTION_REPORT.md](M67_EXECUTION_REPORT.md).
- Historical evaluations, old recovery plans, and prior execution reports live under [docs/archive/evaluations/](docs/archive/evaluations/). The two root M66 evaluation files remain active M67 inputs until closeout archival.
- Scheduler semantics are local-first: `LocalSchedulerLeaseArbiter` is the default local lease arbiter. `scheduler-authority` names remain only for legacy compatibility and cluster-on surfaces, not as a claim of distributed consensus.
- GitHub/PR boundary: the workflow can generate PR-ready summaries, but it does not commit, push, or open a pull request unless the operator explicitly runs those actions.

这是一个个人自用的本地 agentic workflow runtime。当前目标不是公开 SaaS、多用户平台、安装器、外部 onboarding 或插件市场，而是让拥有者自己的代码、研究、设计、审查和自动化工作流可以长期稳定、可恢复、可审计地运行。

## 当前状态

- 最新接受基线：`M66`；当前工作里程碑：`M67`
- 产品前提：个人自用 / 本地 operator runtime
- 主入口：CLI、API、Web operator console、`/ui/workbench` 流式聊天工作台
- 当前 M67 目标：用 workflow 自身参与开发，修复 receipt scope、capability live-proof、validation/CI、Web/CSP、scheduler 语义和热点瘦身问题后，再恢复能力层开发。
- M40 已完成：LLM-assisted chat runtime、assistant delta/final 流式输出、LangGraph chat control graph、SSE 去重和聊天/状态事件分离
- M41 已完成：Codex CLI 强 dogfood 后端、MiniMax/DeepSeek LangChain 控制层、MMX/Vertex/Claude artifact-only 能力骨架、`architecture_delivery_cluster` 真机 dogfood
- M42 已完成：补齐 `search_cluster`、`design_cluster`、`multimodal_cluster`、`review_cluster`、`management_cluster`，并把这些核心 agent 角色接入强 dogfood Codex CLI 路由
- M43-M47 已完成：用俄罗斯方块消除 PDF 跑通真实 artifact 闭环，生成商业化 block puzzle 示例；新增自适应 LLM 路由、动态多集群编排和 operator 可见性
- 安全边界：聊天可以触发 workflow，但 `resume`、`approve`、`reject`、`cancel`、`launch_execute`、repo mutation、git commit/push/PR 必须先确认
- 慢测试规则：完整 `pytest -q --run-slow` 只在每个 M 收口时运行一次

## 活跃文档

后续开发优先看这些文件：

- [当前开发工作流](docs/current_development_workflow.md)
- [里程碑历史摘要](docs/milestone_history.md)
- [技术债登记表](docs/tech-debt-registry.md)
- [结构化技术债 JSON](docs/governance/tech_debt_registry.json)
- [M67 问题登记表](M67_ISSUE_REGISTER.md)
- [M67 执行报告](M67_EXECUTION_REPORT.md)
- [M61-M66 问题登记表](M61_M66_ISSUE_REGISTER.md)
- [M61-M66 执行报告](M61_M66_EXECUTION_REPORT.md)

历史 phase docs、task cards、freeze reviews、archive 和 M2M 交接材料不再作为活跃真相源。需要逐字历史时查 git 历史，不恢复到工作树。

## 快速启动

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

## 常用入口

CLI：

```powershell
workflowctl --db-path state/workflow.db run suggest-presets --goal "整理下一阶段计划"
workflowctl --db-path state/workflow.db run launch --goal "交付一个受保护的开发切片" --execute
workflowctl --db-path state/workflow.db run operator-packet <run_id>
workflowctl --db-path state/workflow.db run pr-ready-summary <run_id>
workflowctl --db-path state/workflow.db doctor
workflowctl --db-path state/workflow.db doctor --strict
```

本地 task card 闭环：

```powershell
workflowctl --db-path state/workflow.db run from-task-card examples/local_task_cards/01_safe_doc_patch.md --write-set README.md --test-command "python -m infra.scripts.check_doc_links" --execute
```

## Historical Recovery Notes

- Historical recovery plan: [M48_M51_RECOVERY_PLAN.md](docs/archive/evaluations/M48_M51_RECOVERY_PLAN.md). Current closeout truth is the M61-M66 issue register/report above.
- Prefer `make test-fast`, `make test-core`, and `make test-full`; these targets create a unique pytest basetemp under `state/.pytest-tmp-workflow/`.
- High-risk API actions require a single-use, scope-bound `OperatorActionReceipt` in the `X-Operator-Action-Receipt` header. Workbench confirmation cards create and consume receipts automatically.
- Use `--workspace-root` or `WORKFLOW_WORKSPACE_ROOT` for file-mutating work; implicit cwd is only a fallback.

```powershell
$receipt = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/operator-action-receipts -ContentType "application/json" -Body '{"action_type":"resume_run","scope_payload":{"run_id":"<run_id>"}}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/runs/<run_id>/resume" -Headers @{"X-Operator-Action-Receipt"=$receipt.receipt_id}
```

聊天工作台建议配置：

```powershell
$env:WORKFLOW_CHAT_LLM_PROVIDER="minimax"
$env:WORKFLOW_CHAT_LLM_MODEL="MiniMax-M2.7"
$env:MINIMAX_BASE_URL="https://api.minimaxi.com/v1"
$env:MINIMAX_API_KEY="<本机环境变量，不写入仓库>"
$env:DEEPSEEK_API_KEY="<可选 fallback，本机环境变量>"
```

M42 dogfood 建议配置：

```powershell
$env:WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED="1"
$env:WORKFLOW_DOGFOOD_EXECUTION_BACKEND="codex_cli"
$env:WORKFLOW_DOGFOOD_MODEL="gpt-5.5"
$env:WORKFLOW_DOGFOOD_REASONING_EFFORT="xhigh"
$env:WORKFLOW_CODEX_TIMEOUT_SECONDS="60"
```

M44/M45 自适应与动态编排试用配置：

```powershell
$env:WORKFLOW_ADAPTIVE_LLM_ROUTING_ENABLED="1"
$env:WORKFLOW_ADAPTIVE_SIMPLE_MODEL="minimax/MiniMax-M2.7"
$env:WORKFLOW_ADAPTIVE_MEDIUM_MODEL="deepseek/deepseek-v4-flash"
$env:WORKFLOW_ADAPTIVE_COMPLEX_MODEL="minimax/MiniMax-M2.7"
$env:WORKFLOW_ADAPTIVE_CODING_ADAPTER="opencode"
$env:WORKFLOW_DYNAMIC_CLUSTER_ROUTING_ENABLED="1"
```

M43 生成的本地小游戏示例：

- [方块艺境 HTML](examples/block_puzzle_shop/index.html)
- [PDF 映射说明](examples/block_puzzle_shop/design_trace.md)

## 验证

日常快速验证：

```powershell
python -m infra.scripts.check_doc_links
python -m infra.scripts.offline_validation --suite full --skip-offline-probe
pytest -q
```

每个 M 收口时再跑完整慢测试：

```powershell
pytest -q --run-slow
```

覆盖率不挂在默认 `pytest` 上；需要时显式运行：

```powershell
pytest -q --run-slow --cov=packages --cov=apps --cov-report=term-missing --cov-fail-under=70
```
