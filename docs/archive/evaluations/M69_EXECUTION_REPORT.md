# M69 Capability Control Plane 执行报告

生成日期：2026-04-26

## 结论

状态：`completed`

M69 新增了一个可审计的 capability control-plane policy decision。它把 provider live proof、mutation write_set 和 operator receipt 元数据合并为统一判定，但本阶段保持观察式集成：不会突然改变既有 run 执行成功语义；CLI control-plane check 会对非 `allowed` 判定返回非零，方便无人值守 gate 使用。

## 完成内容

- 新增 `packages/core_domain/capability_control_plane.py`。
- `CapabilityInvocationEnvelope` 增加：
  - `requested_write_set`
  - `operator_receipt_id`
  - `live_probe_required`
  - `policy_decision`
- `CapabilityExecutionReceipt` 增加：
  - `requested_write_set`
  - `operator_receipt_id`
  - `live_probe_status`
  - `policy_decision`
- `OrchestratorService` 在 compile 时把 policy decision 写入 invocation envelope；在 resume 后把最新 decision 写入 execution receipt metadata。
- 新增 CLI：

```powershell
workflowctl capability control-plane --provider opencode --mutation-mode patch_apply --write-set packages/core_domain/capability_control_plane.py --operator-receipt-id opreceipt_m69_demo --require-live
```

## Policy 语义

- `allowed`：live proof、write_set、receipt 三项满足当前请求。
- `needs_live_probe`：请求要求 live proof，但 provider 没有 verified live probe evidence。
- `needs_receipt`：patch mutation 有 write_set 和 live proof，但没有 operator receipt id。
- `blocked`：硬条件失败，例如 `patch_apply` 没有 write_set。

## Workflow Dogfood

- Task cards：
  - `state/m69_capability_control_plane/task_cards/M69A_policy_decision.md`
  - `state/m69_capability_control_plane/task_cards/M69B_invocation_ledger_integration.md`
  - `state/m69_capability_control_plane/task_cards/M69C_cli_health_surface.md`
- Route preview：
  - `state/m69_capability_control_plane/evidence/m69_plan_graph.json`
  - `state/m69_capability_control_plane/evidence/m69_policy_preview.json`
  - `state/m69_capability_control_plane/evidence/m69_goal_packet.json`
- Workflow-executed evidence：
  - `state/m69_capability_control_plane/evidence/m69_workflow_task_card_review_run.json`

## Smoke Evidence

- `m69_control_plane_opencode_live.json`：opencode + patch_apply + write_set + receipt + require-live => `allowed`。
- `m69_control_plane_opencode_missing_receipt.json`：同一路径缺 receipt => `needs_receipt`，CLI 返回非零并被 gate 捕获。

## 验证

- `python -m compileall packages/core_domain packages/contracts apps/operator_cli -q`：passed。
- `python -m pytest tests/test_capability_control_plane.py tests/test_capability_probe.py tests/test_contracts.py::test_m31_graph_and_capability_contracts_round_trip tests/test_execution_loop.py::test_compile_and_resume_project_capability_envelope_and_receipt -q --basetemp state/.pytest-tmp-workflow/m69-capability-closeout-targeted`：19 passed。
- `python -m infra.scripts.check_doc_links`：passed。
- `workflowctl ... test matrix --suite unit`：passed。
- `workflowctl ... test matrix --suite core`：passed。
- `workflowctl ... test matrix --suite integration`：passed。

## Go / No-Go

当前结论：`GO`。

M69 让 capability invocation 具备统一 policy decision 和 ledger evidence。M70 可以继续收敛 provider/CLI contract，把 Codex/OpenCode/Claude/MMX/Vertex/LangChain/Shell 的 route metadata、failure taxonomy 和 health projection 进一步标准化。
