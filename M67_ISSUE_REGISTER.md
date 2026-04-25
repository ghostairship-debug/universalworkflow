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

| ID | 来源 | 问题 | M67 Phase | 验收标准 |
| --- | --- | --- | --- | --- |
| M67-WF-001 | 用户计划 / P0 evidence | workflow 自身必须参与 M67 开发，不能只靠人工补丁；需要 task-card、route、evidence、operator packet、checkpoint | P0/P8 | 至少三类 workflow-executed task + tracked evidence manifest + operator packet |
| M67-VAL-001 | M66 post-closeout / Opus | offline validation 缺 shard/freshness/timeout 失败报告，旧报告可能被误读 | P4 | quick/full/shard 可运行；timeout 写失败报告；stale report 不算 fresh success |
| M67-WEB-001 | M66 post-closeout | Web UI CSP 仍允许 unsafe-inline，operator UI 存 inline CSS/JS，contribution game template 有 `innerHTML` | P5 | CSP 无 `unsafe-inline`；operator UI 无 inline script/style；game template 无 `innerHTML` |
| M67-SCHED-001 | Opus / post-closeout | scheduler 默认文案和 flag-off boot path 未完全收敛到 local lease arbiter | P6 | flag-off 不 import/construct legacy cluster runtime/support；默认 UI/CLI 文案不称权威 |
| M67-ARCH-001 | Opus / 用户 plan | 热点文件仍超目标；需要 `RepositoryBundle`、`WorkerRuntimeBundle`、test matrix 移出 core domain | P7 | 达到 M67 slimming target 或记录硬阻塞 evidence |
| M67-AUTO-001 | `AGENTS_M67_universalworkflow.md` | `execute=true` / auto-apply 需要统一 Command/PolicyEngine/AutomationLease 语义，不能各入口自行判断 | P2/P5 | 高风险 execute/auto-apply 只有 receipt 或 lease 才执行；GET 不 mutate |
| M67-ROUTE-001 | 用户 plan | 动态/自适应路由只有预演，需要真实 simple/medium/complex E2E 和并发 batch-resume evidence | P8 | opencode+MiniMax simple task、medium route、cluster strong fallback、`batch-resume --max-workers 2` 成功 |

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

## Closeout Gates

M67 closeout 不能只看代码是否改完，必须同时满足：

1. `python -m infra.scripts.check_doc_links`
2. `workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" doctor --strict`
3. `workflowctl ... test matrix --suite unit`
4. `workflowctl ... test matrix --suite core`
5. `workflowctl ... test matrix --suite integration`
6. `workflowctl validation run --suite full`
7. `python -m pytest -q --run-slow`
8. `workflowctl ... capability probe --provider all --require-live --evidence-dir state/m67_workflow_closeout/capability_probes`

任一 provider live probe 失败时，M67 必须输出 `NO-GO`，不能用 degraded/fallback 伪装完成。
