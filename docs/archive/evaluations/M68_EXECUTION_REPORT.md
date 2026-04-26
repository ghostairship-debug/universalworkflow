# M68 LangGraph Focused Runtime 执行报告

生成日期：2026-04-26

## 结论

状态：`completed`

M68 只接入一个受控 LangGraph 子图，范围限定为 `planning -> review -> evidence`。该子图是 opt-in advisory runtime，不 compile、不 resume、不 patch apply，也不作为新的 workflow 状态源；它只读取现有 workflow route preview，并在显式传入 evidence dir 时写入 evidence JSON。

## 完成内容

- 新增 `packages/runtime_langgraph/focused_runtime.py`。
- 新增 CLI：`workflowctl run langgraph-focus --goal ... --preset ... --evidence-dir ...`。
- CLI 先调用既有 workflow `preview_orchestration_plan_graph`，再运行 focused LangGraph runtime 做对比。
- 输出包含 `workflow_route`、`langgraph_route`、`comparison`、`review`、`evidence`。
- `comparison.mutation_allowed=false`，`comparison.direct_mutation_disabled=true`。
- LangGraph 可用时 provider 为 `langgraph`；不可用时保持 deterministic `linear` fallback，仍不 mutation。

## Workflow Dogfood

- Task cards：
  - `state/m68_langgraph_focus/task_cards/M68A_focused_langgraph_runtime.md`
  - `state/m68_langgraph_focus/task_cards/M68B_cli_route_comparison.md`
  - `state/m68_langgraph_focus/task_cards/M68C_closeout_evidence.md`
- Route preview：
  - `state/m68_langgraph_focus/evidence/m68_plan_graph.json`
  - `state/m68_langgraph_focus/evidence/m68_policy_preview.json`
  - `state/m68_langgraph_focus/evidence/m68_goal_packet.json`
- Workflow-executed evidence：
  - `state/m68_langgraph_focus/evidence/m68_workflow_advisory_review_run.json`
  - `state/m68_langgraph_focus/evidence/m68_workflow_task_card_review_run.json`

## Route Comparison Smoke

命令：

```powershell
python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run langgraph-focus --goal "M68 focused runtime closeout smoke" --preset project_delivery --evidence-dir state/m68_langgraph_focus/evidence
```

结果：

- workflow route：`project_delivery` / `dev_cluster` / `planner_generated_graph_with_parallel_children`
- LangGraph route provider：`langgraph`
- LangGraph path：`planning -> review -> evidence`
- workflow preview latency：44 ms
- focused runtime latency：3 ms
- mutation risk nodes observed：1
- mutation allowed：false
- evidence：`state/m68_langgraph_focus/evidence/m68_langgraph_35c5552cd4cc.json`

## 验证

- `python -m compileall packages/runtime_langgraph apps/operator_cli -q`：passed。
- `python -m pytest tests/test_langgraph_focused_runtime.py tests/test_runtime_boundary.py tests/test_cli.py::test_cli_run_langgraph_focus_writes_advisory_evidence -q --run-slow --basetemp state/.pytest-tmp-workflow/m68-focused-targeted-rerun`：8 passed。
- `workflowctl run langgraph-focus ...` smoke：passed。
- `python -m infra.scripts.check_doc_links`：passed。
- `workflowctl ... test matrix --suite unit`：passed。
- `workflowctl ... test matrix --suite core`：passed。
- `workflowctl ... test matrix --suite integration`：passed。

## Go / No-Go

当前结论：`GO`。

M68 的 LangGraph 能力保持 opt-in advisory-only；不稳定时可直接忽略该路径，不影响既有 workflow route。M69 可以继续做 capability control plane，但不能把 M68 focused runtime 扩展为 mutation runtime，除非另开明确安全设计和状态源治理。
