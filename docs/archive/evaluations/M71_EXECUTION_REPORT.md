# M71 Cluster And Concurrent Execution Contract 执行报告

生成日期：2026-04-26

## 结论

状态：`completed`

M71 将 `batch-resume` 从“直接开线程跑”提升为可审计的并发执行契约：执行前会生成 parallel batch plan，明确是否启用 barrier、是否降级串行、降级原因、write_set 审计、dirty worktree 审计、SQLite 可用性检查和 partial failure resume 指针。cluster route stats 同步补齐 30 天窗口、source 计数和 dynamic decision 计数。

## 完成内容

- 新增 `packages/core_domain/parallel_execution_contract.py`：
  - `build_parallel_batch_plan()`：判定 `parallel`、`serial_requested`、`serial_single_member`、`serial_degraded`。
  - write_set 冲突时降级串行。
  - dirty path 命中 requested write_set 时降级串行。
  - SQLite preflight 不 ready 时降级串行。
  - `build_partial_failure_resume()`：输出失败 run 的可恢复命令。
- `resume_runs_parallel()` 接入并发契约：
  - 返回 `execution_mode`、`barrier_enabled`、`degraded_to_serial`、`degraded_reasons`、`audit`、`partial_failure_resume`。
  - 真并发路径保留 barrier 事件和状态投影。
  - 串行降级路径不进入 barrier，避免 `max_workers=1` 时自锁等待。
- `ClusterRouteDecisionRepository.summarize_recent()` 增加：
  - `window`
  - `source_counts`
  - `dynamic_decision_count`

## Workflow Dogfood

- Task cards：
  - `state/m71_concurrent_execution_contract/task_cards/M71A_parallel_batch_contract.md`
  - `state/m71_concurrent_execution_contract/task_cards/M71B_cluster_route_stats.md`
  - `state/m71_concurrent_execution_contract/task_cards/M71C_workflow_evidence_closeout.md`
- Route preview：
  - `state/m71_concurrent_execution_contract/evidence/m71_plan_graph.json`
  - `state/m71_concurrent_execution_contract/evidence/m71_policy_preview.json`
  - `state/m71_concurrent_execution_contract/evidence/m71_goal_packet.json`
- Workflow execution evidence：
  - `state/m71_concurrent_execution_contract/evidence/m71_batch_resume_parallel.json`
  - `state/m71_concurrent_execution_contract/evidence/m71_partial_failure_resume.json`
  - `state/m71_concurrent_execution_contract/evidence/m71_workflow_review_run.json`
  - `state/m71_concurrent_execution_contract/evidence/m71_route_stats.json`

## 关键 Evidence

- `m71_batch_resume_parallel.json`：
  - `execution_mode: parallel`
  - `barrier_enabled: true`
  - `effective_max_workers: 2`
  - `degraded_to_serial: false`
  - dirty worktree 被记录，但未命中 requested write_set，因此未降级。
- `m71_partial_failure_resume.json`：
  - 记录失败 run id。
  - 输出 `workflowctl run batch-resume ... --max-workers ...` 恢复指针。
- `m71_route_stats.json`：
  - 30 天窗口内 route decision 可读。
  - source 和 dynamic decision 统计可读。

## 验证

- `python -m compileall packages/core_domain apps/operator_cli apps/orchestrator_api -q`
- `python -m pytest tests/test_parallel_execution_contract.py tests/test_cluster_route_stats.py tests/test_api.py::test_api_batch_resume_returns_parallel_batch_summary tests/test_cli.py::test_cli_batch_resume_returns_parallel_batch_summary tests/test_execution_loop.py::test_resume_runs_parallel_records_batch_barrier_and_starts_runs_together -q --basetemp state/.pytest-tmp-workflow/m71-targeted-final`
- `python -m infra.scripts.check_doc_links`
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite unit`
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite core`
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite integration`

## Go / No-Go

当前结论：`GO`。

M71 关闭后，workflow 并发路径具备了最小可审计契约：能真实并发、能解释为什么降级、能拒绝危险 write_set 并发、能给出 partial failure 恢复指针。后续 M72 可以用这条路径做 self-development loop demo。
