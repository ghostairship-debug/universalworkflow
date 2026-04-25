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
| P3 | completed | capability live-proof hard gate |
| P4 | completed | validation / CI reliability |
| P5 | completed | Web and browser surface hardening |
| P6 | completed | scheduler semantics and boot path |
| P7 | pending | hot-file slimming |
| P8 | pending | workflow E2E closeout and go/no-go |

## Go / No-Go

当前结论：`NO-GO`，因为 P7-P8 blocking items 尚未完成。

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

## P3: Capability Live-Proof Hard Gate

状态：`completed`

已完成动作：

- capability probe 引入 M67 live-proof contract：`status=ok`、`probe=executed`、`provider`、`live_backend=true`、`no_fallback=true`。
- probe parser 拒绝 generic assistant greeting、simulated、dry-run、fallback-only、minimal `ok` 等 false-positive evidence。
- Codex/OpenCode artifact-only capability probe 直接输出 contract JSON，避免模板文字被误判。
- Claude capability probe 使用 contract JSON 作为唯一 prompt，禁用工具与会话持久化，避免 probe 漂移到 repo 操作。
- LangChain capability probe 先真实调用 primary ChatOpenAI-compatible provider，再写入精确 proof；probe 路径不使用 fallback。
- MMX/Vertex/Claude/LangChain 的 evidence 均纳入 provider-specific live-proof 校验。

验证：

- `python -m pytest tests/test_capability_probe.py -q --basetemp state/.pytest-tmp-current/p3-capability-strict-template`：11 passed。
- `workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider claude --require-live --evidence-dir state/m67_workflow_closeout/capability_probes_single_claude`：passed。
- `workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider langchain --require-live --evidence-dir state/m67_workflow_closeout/capability_probes_single_langchain`：passed。
- `workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider all --require-live --evidence-dir state/m67_workflow_closeout/capability_probes`：passed，shell/Codex/OpenCode/MMX/Vertex/Claude/LangChain 全部 `verified_ready`。

剩余：

- `M67-PROBE-001` 已偿还。
- M67 仍为 `NO-GO`，因为 P4-P8 blocking items 尚未完成。

## P4: Validation And CI Reliability

状态：`completed`

完成动作：

- 创建 P4 多 task-card：`P4A_validation_timeout_root_cause.md`、`P4B_validation_matrix_ci.md`、`P4C_validation_evidence_review.md`。
- 使用 workflow 预演 P4 编排，输出 `p4_plan_graph.json`、`p4_policy_preview.json`、`p4_goal_packet.json`。
- 修复 offline validation 子进程在 Windows 上通过 `multiprocessing.Queue` 传递大 payload 时可能卡住父进程 join 的 bug，改为 result JSON 文件传递。
- 为 validation flow 增加 command trace、`last_command` 和 `flow_result_path`，timeout/failure 不再只留下模糊超时。
- 将 `quick` CLI validation 从完整 CLI closeout 拆为短 smoke；完整 CLI/API/smoke/cluster 覆盖保留在 `full` 和 shards。
- 修复 offline API/cluster validation helper，使自动申请的 `OperatorActionReceipt` 带上与真实请求一致的 `scope_payload`。
- 修正 validation 中过期的 “zero open debt / release ready” 断言；M67 未收口期间验证治理字段真实性，不伪装 ready。
- test matrix basetemp 已统一到 milestone-neutral `state/.pytest-tmp-workflow/`。

验证：

- `python -m pytest tests/test_offline_validation_runner.py tests/test_test_matrix.py -q --basetemp state/.pytest-tmp-workflow/p4-targeted`：11 passed。
- `python -m pytest tests/test_governance.py -q --basetemp state/.pytest-tmp-workflow/p4-governance`：12 passed。
- `workflowctl ... validation run --suite quick --skip-offline-probe --timeout-seconds 120`：passed，报告 `state/m67_workflow_closeout/evidence/p4_offline_validation_quick_pass.json`。
- `workflowctl ... test matrix --suite unit`：57 passed。
- `workflowctl ... test matrix --suite core`：87 passed。
- `workflowctl ... validation run --suite full --shard 1/4`：passed，报告 `p4_full_shard_1of4_after_assertion.json`。
- `workflowctl ... validation run --suite full --shard 2/4`：passed，报告 `p4_full_shard_2of4.json`。
- `workflowctl ... validation run --suite full --shard 3/4`：passed，报告 `p4_full_shard_3of4_after_receipt.json`。
- `workflowctl ... validation run --suite full --shard 4/4`：passed，报告 `p4_full_shard_4of4_after_receipt.json`。
- `python -m infra.scripts.check_doc_links`：passed。
- `workflowctl ... doctor --strict`：ok。

剩余：

- `M67-VAL-001` 已偿还。
- M67 仍为 `NO-GO`，因为 P6-P8 blocking items 尚未完成。

## P5: Web And Browser Surface Hardening

状态：`completed`

完成动作：
- 创建 P5 三张 task-card：`P5A_web_static_assets_csp.md`、`P5B_web_receipt_gate_review.md`、`P5C_game_template_dom_safety_evidence.md`。
- 使用 workflow 预演 P5 编排，输出 `p5_plan_graph.txt`、`p5_policy_preview.txt`、`p5_goal_packet.txt`。
- 将 operator UI CSS/JS 从 Python inline HTML 移到本地静态资源：`apps/orchestrator_api/static/operator.css` 与 `apps/orchestrator_api/static/workbench.js`。
- CSP 移除 `unsafe-inline`，Operator UI 页面移除 inline `<style>` 与 `style=` 属性；Workbench 通过 static JS 保留 `EventSource`、chat confirmation 和 delta streaming 行为。
- Web UI 高风险/状态动作继续走两步 receipt confirmation，并把原直接执行的 `reconcile` POST 改为先签发 `reconcile_run` receipt。
- local game artifact 中的 `.innerHTML` 清空路径改为 `replaceChildren()`，保留生成游戏行为但移除 unsafe DOM sink。

验证：
- `python -m compileall apps/orchestrator_api packages/contributions/games -q`：passed。
- `python -m pytest tests/test_web_ui.py tests/test_operator_action_receipt.py -q --run-slow --basetemp state/.pytest-tmp-workflow/p5-web-receipt`：10 passed。
- `python -m infra.scripts.check_doc_links`：passed。
- `workflowctl ... validation run --suite quick --skip-offline-probe --timeout-seconds 120 --report-path state/m67_workflow_closeout/evidence/p5_offline_validation_quick.json`：passed。

Bug-first observation：
- 原计划引用的 `tests/test_api.py::test_api_high_risk_paths_require_operator_receipt` 在当前代码库不存在；P5 将其视为过期 verification 指针，改用现存 `tests/test_operator_action_receipt.py` 覆盖 API receipt 契约，并在 `tests/test_web_ui.py` 补 Web/CSP/static/DOM regression。

剩余：
- `M67-WEB-001` 已偿还。
- M67 仍为 `NO-GO`，因为 P6-P8 blocking items 尚未完成。

## P6: Scheduler Semantics And Boot Path

状态：`completed`

完成动作：
- 创建 P6 三张 task-card：`P6A_scheduler_wording_local_lease.md`、`P6B_scheduler_flag_off_boot_path.md`、`P6C_scheduler_closeout_evidence.md`。
- 使用 workflow 预演 P6 编排，输出 `p6_plan_graph.txt`、`p6_policy_preview.txt`、`p6_goal_packet.txt`。
- 默认 Web UI 文案从“调度权威”改为“调度租约仲裁 / local scheduler lease arbiter”；旧 JSON/API 字段名保持兼容。
- CLI scheduler help 改为 `Local scheduler lease arbiter and legacy cluster compatibility commands.`。
- 默认服务构造路径改为 import `SchedulerLeaseProjectionService`；旧 `SchedulerAuthoritySupportService` 保留为兼容 alias，但默认 flag-off 构造不再 import legacy support module。
- flag-off 子进程验证 `packages.core_domain.scheduler_authority` 与 `packages.core_domain.service_scheduler_authority_support` 均不在 `sys.modules`；flag-on 仍 lazy import `SchedulerAuthorityClusterService`。

验证：
- `python -m compileall packages/core_domain apps/operator_cli apps/orchestrator_api -q`：passed。
- `python -m pytest tests/test_scheduler_flag_off_isolation.py -q --basetemp state/.pytest-tmp-workflow/p6-isolation`：2 passed。
- `python -m pytest tests/test_web_ui.py tests/test_api.py::test_api_scheduler_authority_regrants_after_expiry_and_survives_restart -q --run-slow --basetemp state/.pytest-tmp-workflow/p6-wording`：5 passed。
- `python -m apps.operator_cli.main scheduler --help`：help text shows local scheduler lease arbiter wording。

剩余：
- `M67-SCHED-001` 已偿还。
- M67 仍为 `NO-GO`，因为 P7-P8 blocking items 尚未完成。
