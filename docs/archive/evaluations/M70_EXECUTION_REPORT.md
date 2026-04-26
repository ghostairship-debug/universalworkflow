# M70 Existing Provider And CLI Contract Consolidation 执行报告

生成日期：2026-04-26

## 结论

状态：`completed`

M70 将当前已接入 provider 的 adapter、CLI dependency、auth source、route role 和 failure taxonomy 收敛到统一 provider contract registry。该 registry 现在被 capability control-plane decision、capability health failure taxonomy 和 CLI `provider-contracts` 共同使用。

## Provider 事实

- 已接入 worker/provider：Shell、Codex、OpenCode、Claude、MMX/MiniMax、Vertex、LangChain。
- OpenCode 默认可走 `minimax/MiniMax-M2.7` simple lane。
- medium lane 可使用 `deepseek/deepseek-v4-flash`，失败时直接 fallback 到 Codex。
- Gemini CLI 当前不是 adapter，也未接入。
- Gemini-family 能力当前通过 Vertex/GCP 路径进入。
- `gcloud` 是 Vertex/GCP 凭据与环境工具，不是独立 worker adapter。

## 完成内容

- `packages/core_domain/capability_control_plane.py` 新增 `PROVIDER_CONTRACTS`。
- provider contract 覆盖：`shell`、`codex`、`opencode`、`mmx`、`vertex`、`claude`、`langchain`。
- `evaluate_capability_policy()` 输出 `provider_contract`，让 policy evidence 能解释实际 provider 语义。
- `CapabilityPlane._failure_classes_for_descriptor()` 优先使用 provider contract failure taxonomy。
- 新增 CLI：

```powershell
workflowctl capability provider-contracts --provider vertex
```

## Workflow Dogfood

- Task cards：
  - `state/m70_provider_contracts/task_cards/M70A_provider_contract_registry.md`
  - `state/m70_provider_contracts/task_cards/M70B_cli_provider_contract_surface.md`
  - `state/m70_provider_contracts/task_cards/M70C_closeout_report.md`
- Route preview：
  - `state/m70_provider_contracts/evidence/m70_plan_graph.json`
  - `state/m70_provider_contracts/evidence/m70_policy_preview.json`
  - `state/m70_provider_contracts/evidence/m70_goal_packet.json`
- Workflow-executed evidence：
  - `state/m70_provider_contracts/evidence/m70_workflow_task_card_review_run.json`

## Smoke Evidence

- `state/m70_provider_contracts/evidence/m70_provider_contract_vertex.json`
  - provider：`vertex`
  - adapter：`vertex_multimodal`
  - CLI dependency：`gcloud`
  - route role：`Vertex/GCP Gemini-family multimodal entrypoint`
  - notes 明确 Gemini CLI 未接入，`gcloud` 不是 worker adapter。
- `state/m70_provider_contracts/evidence/m70_provider_contracts_all.json`：列出全部 provider contracts。

## 验证

- `python -m compileall packages/core_domain apps/operator_cli -q`
- `python -m pytest tests/test_capability_control_plane.py tests/test_capability_probe.py::test_cli_capability_provider_contracts_explain_vertex_and_gcloud tests/test_capability_probe.py::test_cli_capability_control_plane_reports_write_set_and_live_gate tests/test_runtime_boundary.py -q --basetemp state/.pytest-tmp-workflow/m70-provider-contracts-targeted`
- `python -m infra.scripts.check_doc_links`
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite unit`
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite core`
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite integration`

## Go / No-Go

当前结论：`GO`。

M70 不新增 Gemini CLI。后续如果 Gemini CLI 表现和成本恢复，再另开 provider promotion task；在那之前，Vertex 是 Gemini-family 能力入口，`gcloud` 只作为凭据和环境工具。
