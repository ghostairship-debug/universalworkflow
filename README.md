# Universal Agentic Workflow OS

这是一个个人自用的本地 agentic workflow runtime。当前目标不是公开 SaaS、多用户平台、安装器、外部 onboarding 或插件市场，而是让拥有者自己的代码、研究、设计、审查和自动化工作流可以长期稳定、可恢复、可审计地运行。

## 当前状态

- 最新接受基线：`M42`
- 产品前提：个人自用 / 本地 operator runtime
- 主入口：CLI、API、Web operator console、`/ui/workbench` 流式聊天工作台
- M40 已完成：LLM-assisted chat runtime、assistant delta/final 流式输出、LangGraph chat control graph、SSE 去重和聊天/状态事件分离
- M41 已完成：Codex CLI 强 dogfood 后端、MiniMax/DeepSeek LangChain 控制层、MMX/Vertex/Claude artifact-only 能力骨架、`architecture_delivery_cluster` 真机 dogfood
- M42 已完成：补齐 `search_cluster`、`design_cluster`、`multimodal_cluster`、`review_cluster`、`management_cluster`，并把这些核心 agent 角色接入强 dogfood Codex CLI 路由
- 安全边界：聊天可以触发 workflow，但 `resume`、`approve`、`reject`、`cancel`、`launch_execute`、repo mutation、git commit/push/PR 必须先确认
- 慢测试规则：完整 `pytest -q --run-slow` 只在每个 M 收口时运行一次

## 活跃文档

后续开发优先看这些文件：

- [当前开发工作流](docs/current_development_workflow.md)
- [里程碑历史摘要](docs/milestone_history.md)
- [技术债登记表](docs/tech-debt-registry.md)
- [结构化技术债 JSON](docs/governance/tech_debt_registry.json)
- [M38 修复与开发计划](M38_REPAIR_AND_DEVELOPMENT_PLAN.md)
- [M37 深度评估报告](PROJECT_DEEP_EVALUATION_M37.md)

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
workflowctl doctor --db-path state/workflow.db
```

本地 task card 闭环：

```powershell
workflowctl --db-path state/workflow.db run from-task-card examples/local_task_cards/01_safe_doc_patch.md --write-set README.md --test-command "python -m infra.scripts.check_doc_links" --execute
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

## 验证

日常快速验证：

```powershell
python -m infra.scripts.check_doc_links
python -m infra.scripts.offline_validation --skip-offline-probe
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
