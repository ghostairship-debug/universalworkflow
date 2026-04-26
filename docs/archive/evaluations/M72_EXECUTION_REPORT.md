# M72 Self-Development Loop And Capability Demo 执行报告

生成日期：2026-04-26

## 结论

状态：`completed`

M72 把本轮“workflow 共同开发”从临时 evidence 收口成可复用的治理入口：新增 `workflowctl governance self-development-manifest`，可以扫描 M67-M72 的执行报告、state evidence、task cards、operator packets 和相关 git commits，并输出 GO/NO-GO。这个工具同时固化了任务编排规则：每个 milestone/phase 默认必须有多张 task card，单卡 phase 必须显式标记 `single_card_exception`。

M73 能力层开发建议：`GO`，但继续保留 bug-first 和 workflow dogfood 硬门禁。能力层开发开始前仍应先跑当前 manifest、doctor strict、test matrix、offline validation 和 provider live probe。

## 完成内容

- 新增 `packages/core_domain/self_development_manifest.py`：
  - 扫描指定 milestone 的根目录执行报告。
  - 汇总 `state/<milestone>*/task_cards`、`evidence`、`operator_packets`。
  - 检查 task card 数量是否满足规则。
  - 收集与 milestone 相关的 git commits。
  - 输出 `GO` / `NO-GO` 和 blocking issue 列表。
- 新增 CLI：

```powershell
workflowctl governance self-development-manifest --milestone M67 --milestone M68 --milestone M69 --milestone M70 --milestone M71 --milestone M72
```

- 新增测试：
  - manifest 完整时应为 `GO`。
  - 单卡 phase 未声明例外时应为 `NO-GO`。
  - CLI 可写出 manifest JSON。

## Workflow Dogfood

- Task cards：
  - `state/m72_self_development_loop/task_cards/M72A_self_development_manifest_tool.md`
  - `state/m72_self_development_loop/task_cards/M72B_workflow_self_demo.md`
  - `state/m72_self_development_loop/task_cards/M72C_m73_go_no_go_closeout.md`
- Route preview：
  - `state/m72_self_development_loop/evidence/m72_plan_graph.json`
  - `state/m72_self_development_loop/evidence/m72_policy_preview.json`
  - `state/m72_self_development_loop/evidence/m72_goal_packet.json`
- Manifest evidence：
  - `state/m72_self_development_loop/evidence/m72_manifest_pre_report.json`
  - `state/m72_self_development_loop/evidence/m72_manifest_final.json`
- Workflow-executed review evidence：
  - `state/m72_self_development_loop/evidence/m72_workflow_review_run.json`

## Manifest 结果

- pre-report manifest：`NO-GO`
  - 原因：M72 报告和 operator packet 尚未生成。
  - 该结果证明 manifest 能捕捉 closeout 缺口。
- final manifest：`GO`
  - M67-M72 均有执行报告、task cards、evidence 和 operator packet。
  - task-card policy 全部通过。

## 验证

- `python -m pytest tests/test_self_development_manifest.py -q --basetemp state/.pytest-tmp-workflow/m72-manifest-green`
- `python -m compileall packages/core_domain apps/operator_cli -q`
- `python -m pytest tests/test_self_development_manifest.py tests/test_parallel_execution_contract.py tests/test_capability_control_plane.py tests/test_capability_probe.py::test_cli_capability_provider_contracts_explain_vertex_and_gcloud tests/test_cli.py::test_cli_batch_resume_returns_parallel_batch_summary -q --basetemp state/.pytest-tmp-workflow/m72-targeted-final`
- `python -m infra.scripts.check_doc_links`
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" doctor --strict`
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite unit`
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite core`
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite integration`
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" validation run --suite full --skip-offline-probe --report-path state/m72_self_development_loop/evidence/m72_offline_validation_full.json`
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider all --require-live --evidence-dir state/m72_self_development_loop/capability_probes`
- `python -m pytest -q --run-slow --basetemp state/.pytest-tmp-workflow/m72-full-slow`：462 passed。

## 剩余边界

- M72 没有接入 Gemini CLI；Gemini-family 能力仍以 Vertex/GCP 作为当前入口。
- 本轮 provider live probe 已全部通过；后续若因凭据、配额或外部服务失败，应记录为 blocker，但不伪造 ready。
- M73 开始能力开发时仍应保持“workflow bug 优先修复”的开发纪律。

## Go / No-Go

当前结论：`GO`。

M67-M72 的可信开发底座已经具备闭环：workflow 参与编排和执行、并发路径可审计、provider contract 可查询、capability control-plane 有结构化 policy、LangGraph 只作为 advisory opt-in、最终 manifest 能机器检查证据完整性。可以进入 M73 能力层开发，但每个能力 milestone 仍需继续使用多 task card、route preview、workflow execution、evidence、operator packet 和 phase commit。
