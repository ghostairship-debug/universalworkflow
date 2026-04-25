# M67 Workflow-Dogfood 可信收口执行报告

生成日期：2026-04-26

## 当前状态

M67 正在执行中。当前接受基线仍是 `M66` / package `0.66.0`，但 active milestone 已切换为 `M67`。M61-M66 计划内债务已收口；M67 重新登记了当前阻塞能力层开发的可证实问题，因此项目不再声明“zero open debt”。

## P0: Workflow Harness Rehearsal

状态：`completed`

已完成动作：

- 创建 task card：`state/m67_workflow_closeout/task_cards/P0_workflow_harness_rehearsal.md`
- 使用 M67 动态/自适应路由环境运行：
  - `workflowctl ... run plan-graph`
  - `workflowctl ... run policy-preview`
  - `workflowctl ... run goal-packet`
- P0 evidence 输出到：
  - `state/m67_workflow_closeout/evidence/p0_plan_graph.json`
  - `state/m67_workflow_closeout/evidence/p0_policy_preview.json`
  - `state/m67_workflow_closeout/evidence/p0_goal_packet.json`

观察结论：

- `plan-graph` 为 M67 总目标选择 `dev_cluster`，并生成带 parallel barrier 的执行图。
- planner/coder/researcher/reviewer 节点均经 adaptive router 解析为 `opencode`，模型为 `minimax/MiniMax-M2.7`。
- route metadata 中包含 `adaptive_llm_router`、`tier=complex`、`coding_adapter=opencode` 等字段，说明动态/自适应配置被真实读取。
- P0 只证明 route 预演，不等于 P8 的真实 E2E 完成；simple/medium/complex workflow task 与 `batch-resume --max-workers 2` 仍是 blocking gate。

## P1: Governance Truth Reset

状态：`completed`

已完成动作：

- 新建 `M67_ISSUE_REGISTER.md`。
- 新建本执行报告 `M67_EXECUTION_REPORT.md`。
- 将两份根目录 M66 评估与 `AGENTS_M67_universalworkflow.md` 吸收到 M67 issue register。
- 更新 `docs/governance/tech_debt_registry.json`：重新登记 M67 blocking/carry-forward debt。
- 更新治理代码，使 tech-debt report 区分 `blocking_open` 与 `carry_forward`，并保留旧 `open_items` 兼容。
- 更新 README、当前开发工作流、里程碑历史、M61-M66 历史报告和人类可读技术债摘要，取消“项目零债”的误导表达。

验证：

- `python -m pytest tests/test_governance.py -q --basetemp state/.pytest-tmp-current/p1-governance`：11 passed。
- `python -m pytest --run-slow tests/test_cli.py::test_cli_governance_tech_debt_report tests/test_cli.py::test_cli_governance_release_readiness_report tests/test_cli.py::test_cli_governance_metrics_and_alerts_reports tests/test_cli.py::test_cli_governance_release_readiness_report_works_without_bootstrapped_db -q --basetemp state/.pytest-tmp-current/p1-cli`：4 passed。
- `python -m pytest --run-slow tests/test_api.py::test_api_exposes_governance_tech_debt_report tests/test_api.py::test_api_exposes_governance_release_readiness_report tests/test_api.py::test_api_exposes_governance_metrics_and_alerts_reports -q --basetemp state/.pytest-tmp-current/p1-api`：3 passed。
- `python -m infra.scripts.check_doc_links`：passed，7 docs，0 issues。

Bug-first observation:

- 默认 pytest temp cleanup 曾出现 ignored `PermissionError`，显式 `--basetemp` 初次重跑也暴露父目录不存在时 pytest 不会递归创建。已记录到 `state/m67_workflow_closeout/workflow_bug_queue/BUG-P1-PYTEST-TEMP-CLEANUP.md`，并纳入 `M67-VAL-001` 的 P4 修复范围。

## Pending Phases

| Phase | 状态 | 目标 |
| --- | --- | --- |
| P2 | completed | `OperatorActionReceipt` v2 / scope hash / bounded autonomy policy first slice |
| P3 | pending | capability live-proof hard gate |
| P4 | pending | validation / CI reliability |
| P5 | pending | Web and browser surface hardening |
| P6 | pending | scheduler semantics and boot path |
| P7 | pending | hot-file slimming |
| P8 | pending | workflow E2E closeout and go/no-go |

## Go / No-Go

当前结论：`NO-GO`，因为 P3-P8 blocking items 尚未完成。

M67 通过后，M68 才允许恢复能力层开发。

## P2: OperatorActionReceipt v2

状态：`completed`

已完成动作：

- 新增 migration：`infra/migrations/025_m67_operator_action_receipt_scope.sql`。
- `OperatorActionReceipt` contract 增加 `scope_hash` / `scope_payload`。
- `OperatorActionGuard` 在 issue 时 canonicalize scope 并写入 SHA-256 hash；consume 时对高风险动作校验实际 request scope。
- 高风险 API 路径绑定 scope：
  - `resume/approve/reject/cancel` 绑定 `run_id`。
  - `batch-resume` 绑定 `run_ids` 与 `max_workers`。
  - `reconcile apply` 绑定 `run_id/apply/action`。
  - `/runs/launch execute=true` 绑定 `goal/preset_id/execute` 并要求 receipt。
  - `/interaction/sessions/{session_id}/launch execute=true` 绑定 session 与 selected preset/cluster。
- Web UI confirmation 和 chat confirmation 消费 receipt 时传入同一 scope。
- `GET /interaction/watchdogs/evaluate?auto_apply=true` 改为 400 只读拒绝；新增 `POST /interaction/watchdogs/evaluate/apply`，要求 `watchdog_auto_apply` receipt。

验证：

- `python -m pytest tests/test_operator_action_receipt.py -q --basetemp state/.pytest-tmp-current/p2-receipt-final`：6 passed。
- `python -m pytest --run-slow tests/test_web_ui.py -q --basetemp state/.pytest-tmp-current/p2-webui-rerun`：3 passed。
- `python -m pytest --run-slow tests/test_api.py::test_api_chat_launch_keyword_confirms_pending_launch_execute tests/test_api.py::test_api_exposes_plan_graph_and_launch_surfaces tests/test_api.py::test_api_can_create_get_and_launch_interaction_session -q --basetemp state/.pytest-tmp-current/p2-api-rerun`：3 passed。
- `python -m pytest tests/test_operator_action_receipt.py tests/test_web_ui.py -q --run-slow --basetemp state/.pytest-tmp-current/p2-receipt-web-combined`：9 passed。
- `workflowctl --db-path state/.pytest-tmp-current/p2-migration/workflow.db db migrate`：25 migrations applied, pending 0。

剩余：

- `M67-SEC-001` 已偿还。
- `M67-AUTO-001` 仍保持 blocking_open，因为 P2 只修了 execute/auto-apply 的硬边界，完整 Command / PolicyEngine / AutomationLease 语义仍需后续收敛。
