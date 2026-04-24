# Universal Agentic Workflow OS

这是一个个人自用的本地 agentic workflow runtime。当前目标不是公开产品、SaaS、多用户平台、开源 onboarding 或第三方插件市场；当前目标是让拥有者自己的代码、研究、交付、审查和自动化工作流可以长期稳定、可恢复、可审计地运行。

## 当前状态

- 当前基线：已接受 `M37`，没有打开任何 post-`M37` 的 bounded phase。
- 当前定位：`v1 core complete` personal-runtime baseline。
- 当前入口：CLI、API、Web operator console、TUI、natural-language workbench v1。
- 当前运行边界：SQLite 本地持久化、`RuntimeGateway`、多 adapter worker routing、review policy、capability registry、scheduler-authority local-only / quorum 双态。
- 当前自动化边界：generated profiles 和 watchdog automation 已存在，但高风险动作必须保持 review-gated。
- 当前最重要的结构债：`OrchestratorService` 仍然过大，后续应优先收缩。

## 活跃文档

后续开发只看这些文档：

- [当前开发工作流](docs/current_development_workflow.md)
- [技术债登记表](docs/tech-debt-registry.md)
- [里程碑历史摘要](docs/milestone_history.md)
- [M37 深度评估报告](PROJECT_DEEP_EVALUATION_M37.md)
- [结构化治理数据](docs/governance/tech_debt_registry.json)

历史 phase docs、task cards、freeze reviews、archive 和 M2M 交接文档已经合并到 [里程碑历史摘要](docs/milestone_history.md)。如果需要逐字历史细节，请通过 git 历史追溯，不再把旧材料保留在活跃工作树里。

## 快速启动

安装运行依赖：

```bash
pip install -e .
```

安装开发和测试依赖：

```bash
pip install -e ".[dev]"
```

如果需要 MCP pilot 支持：

```bash
pip install -e ".[mcp]"
```

初始化和 smoke：

```bash
python -m infra.scripts.manage --db-path state/workflow.db reset-db
python -m infra.scripts.manage --db-path state/workflow.db smoke
python -m infra.scripts.manage --db-path state/workflow.db demo
```

## 常用入口

CLI：

```powershell
workflowctl --db-path state/workflow.db run suggest-presets --goal "整理下一阶段计划"
workflowctl --db-path state/workflow.db run plan-graph --goal "交付一个受保护的开发切片"
workflowctl --db-path state/workflow.db run policy-preview --goal "交付一个受保护的开发切片"
workflowctl --db-path state/workflow.db run launch --goal "交付一个受保护的开发切片" --execute
workflowctl --db-path state/workflow.db run operator-packet <run_id>
```

Web operator console：

```powershell
uvicorn apps.orchestrator_api.main:app --host 127.0.0.1 --port 8000
```

打开：

- `http://127.0.0.1:8000/ui`
- `http://127.0.0.1:8000/ui/workbench`
- `http://127.0.0.1:8000/ui/config`

默认 scheduler-authority 是 local-only。只有需要测试 quorum 路径时才显式开启：

```powershell
$env:UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER="1"
workflow-scheduler-authority
```

## 验证命令

日常最小验证：

```powershell
python -m infra.scripts.check_doc_links
python -m infra.scripts.offline_validation --skip-offline-probe
pytest -q
```

M38 之前的基线门槛：

- `pytest -q` 至少保持当前主线规模，不因文档清理损坏测试集合。
- `python -m infra.scripts.check_doc_links` 必须通过。
- `python -m infra.scripts.offline_validation --skip-offline-probe` 必须通过。

## 下一阶段

下一阶段应打开 `M38 Phase 0`，主题建议是：

> 个人自用硬化、`OrchestratorService` 收缩、运行证据增强。

M38 不应该默认做公开产品化、外部用户 onboarding、插件市场或企业权限。只有当拥有者明确改变目标时，才重新评估这些方向。
