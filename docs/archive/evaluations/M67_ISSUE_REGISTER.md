# M67 Workflow-Dogfood 可信收口问题登记表

生成日期：2026-04-26

## 目标

M67 是一个完整 milestone，不再把每个小切片单独编号成新 M。目标是在真实调用 workflow 共同开发的同时，关闭恢复能力层开发前的可信性、安全性、验证性和结构瘦身阻塞项。

本登记表吸收以下输入：

- `PROJECT_DEEP_EVALUATION_M66_OPUS.md`
- `PROJECT_DEEP_EVALUATION_M66_POST_CLOSEOUT.md`
- `AGENTS_M67_universalworkflow.md`
- `docs/governance/tech_debt_registry.json`
- `M61_M66_ISSUE_REGISTER.md`
- `M61_M66_EXECUTION_REPORT.md`

## 状态规则

- `blocking_open`：M67 closeout 前必须解决，否则 M67 `NO-GO`。
- `in_progress`：已经进入当前 phase，尚未完成验证。
- `repaid`：已修复并有测试/evidence。
- `blocked`：外部凭据、配额或环境阻塞；必须有 evidence 和解除条件。
- `carry_forward`：不阻塞 M67 进入能力层开发，但必须记录为后续维护债。
- `obsolete`：被更新事实取代，不再需要执行。

## Blocking Open

当前无 `blocking_open` 项。M67 的阻塞项已在 P2-P8 通过代码、测试和 evidence 关闭；剩余结构性维护债记录在 Carry Forward。

## Carry Forward

| ID | 问题 | 不阻塞理由 | 后续触发条件 |
| --- | --- | --- | --- |
| M67-CARRY-001 | `repositories.py`、`service_lifecycle.py`、`service_projection.py`、`interaction_catalog.py`、`models.py` 仍偏大 | M67 已选择先修安全、验证、workflow evidence 和指定热点文件；继续深拆会扩大风险面 | M67 后如果能力层开发再次被构造面或配置代码拖慢，开独立结构里程碑 |

## Repaid / Evidence

| ID | 结论 | Evidence |
| --- | --- | --- |
| M67-P0-ROUTE-REHEARSAL | P0 预演已证明 dynamic/adaptive env 能让 complex lane 经 adaptive router 选择 `opencode` 与 `minimax/MiniMax-M2.7` | `state/m67_workflow_closeout/evidence/p0_plan_graph.json`、`p0_policy_preview.json`、`p0_goal_packet.json` |
| M67-SEC-001 | P2 已加入 `scope_hash` / `scope_payload`，高风险 API/UI/chat receipt 消费绑定实际 run/body/session scope；legacy receipt 缺 scope hash 会拒绝；watchdog auto-apply 从 GET mutate 改为 POST + receipt | `tests/test_operator_action_receipt.py`，`infra/migrations/025_m67_operator_action_receipt_scope.sql` |
| M67-PROBE-001 | P3 已加入 provider-specific live-proof contract，拒绝 generic/simulated/dry-run/fallback-only false-positive；Codex/OpenCode/Claude/LangChain probe 路径输出带 provider/live_backend/no_fallback 的真实 proof | `tests/test_capability_probe.py`，`state/m67_workflow_closeout/capability_probes/` |
| M67-VAL-001 | P4 已修复 offline validation 可靠性：quick 不再跑 full CLI closeout；flow 子进程大 payload 改为 result JSON 文件，避免 Windows multiprocessing Queue deadlock；timeout/failure 报告包含 trace 和 last command；API/cluster validation helper 按 receipt v2 scope_payload 申请 receipt；full suite 可分片运行 | `tests/test_offline_validation_runner.py`，`state/m67_workflow_closeout/evidence/p4_offline_validation_quick_pass.json`，`p4_full_shard_1of4_after_assertion.json`，`p4_full_shard_2of4.json`，`p4_full_shard_3of4_after_receipt.json`，`p4_full_shard_4of4_after_receipt.json` |
| M67-WEB-001 | P5 已完成 Web/browser hardening：operator CSS/JS 改为 `/static/operator.css` 与 `/static/workbench.js`，CSP 移除 `unsafe-inline`，高风险 UI 动作继续两步 receipt confirmation，`reconcile` 也改为先签发 receipt，local game artifact 的 `.innerHTML` 清空路径改为 `replaceChildren()` | `tests/test_web_ui.py`，`tests/test_operator_action_receipt.py`，`state/m67_workflow_closeout/evidence/p5_offline_validation_quick.json` |
| M67-SCHED-001 | P6 已完成 scheduler 默认语义收敛：Web/CLI 默认文案改为 local scheduler lease arbiter / 调度租约仲裁，legacy scheduler-authority JSON/API 字段保持兼容；默认 boot path 改用 `SchedulerLeaseProjectionService`，flag-off 子进程验证不 import `packages.core_domain.scheduler_authority` 或 legacy support module，flag-on 仍 lazy import cluster runtime | `tests/test_scheduler_flag_off_isolation.py`，`tests/test_web_ui.py`，`tests/test_api.py::test_api_scheduler_authority_regrants_after_expiry_and_survives_restart` |
| M67-ARCH-001 | P7 已完成热点文件瘦身：`services.py` 1801 行，`service_interaction_chat.py` 883 行，`local_scheduler_lease_arbiter.py` 679 行，`web_ui_components.py` 354 行，`local_game_artifacts.py` 拆分后单文件均 <= 650 行，`test_matrix` 实现迁出 core_domain 并保留兼容 wrapper | `tests/test_service_decomposition.py`，`tests/test_scheduler_flag_off_isolation.py`，`tests/test_chat_llm_runtime.py`，`tests/test_test_matrix.py`，`tests/test_m43_game_artifacts.py` |
| M67-WF-001 | P8 已完成真实 workflow 共同开发证据：三类 task card、route preview、simple/medium/complex workflow runs、tracked evidence manifest、operator packet 和 checkpoint 均已生成；过程中发现并修复 workflow 自身 bug | `state/m67_workflow_closeout/task_cards/P8A_simple_medium_batch_resume.md`，`P8B_complex_orchestration_e2e.md`，`P8C_closeout_evidence_manifest.md`，`state/m67_workflow_closeout/evidence/p8_tracked_evidence_manifest.json`，`state/m67_workflow_closeout/operator_packets/p8_operator_packet.json` |
| M67-AUTO-001 | P2/P5/P8 已关闭 M67 阻塞边界：`execute=true`、`batch-resume`、`reconcile apply`、chat confirmation、watchdog auto-apply 等高风险动作统一通过 `OperatorActionReceipt` scope hash 绑定实际请求；GET auto-apply 被拒绝；broader Command/PolicyEngine/AutomationLease 统一抽象转入 M69 控制面设计，不再阻塞 M67 能力层恢复 | `tests/test_operator_action_receipt.py`，`tests/test_api.py`，`tests/test_web_ui.py`，`state/m67_workflow_closeout/evidence/p8_closeout_validation_full_skip_offline_probe_really_final.json` |
| M67-ROUTE-001 | P8 已完成动态/自适应路由与并发 proof：MiniMax/OpenCode simple lane 真实执行成功，DeepSeek medium lane 成功，Codex fallback 成功，complex task 触发 cluster_parallel orchestration，`batch-resume --max-workers 2` 在 DeepSeek fallback simple tasks 上成功 | `state/m67_workflow_closeout/evidence/p8_minimax_post_utf8_run.json`，`p8_medium_run_guarded.json`，`p8_simple_codex_fallback_run.json`，`p8_complex_orchestration_run.json`，`p8_batch_resume_deepseek_minimal.json`，`p8_cluster_route_stats.json` |

## Closeout Gates

M67 closeout 不能只看代码是否改完，必须同时满足：

1. `python -m infra.scripts.check_doc_links`
2. `workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" doctor --strict`
3. `workflowctl ... test matrix --suite unit`
4. `workflowctl ... test matrix --suite core`
5. `workflowctl ... test matrix --suite integration`
6. `workflowctl validation run --suite full --skip-offline-probe`（本轮为 provider live closeout，外网必须可达；无 skip 的 offline isolation probe 失败证据保留在 `p8_closeout_validation_full_really_final.json`）
7. `python -m pytest -q --run-slow`
8. `workflowctl ... capability probe --provider all --require-live --evidence-dir state/m67_workflow_closeout/capability_probes`

任一 provider live probe 失败时，M67 必须输出 `NO-GO`，不能用 degraded/fallback 伪装完成。
