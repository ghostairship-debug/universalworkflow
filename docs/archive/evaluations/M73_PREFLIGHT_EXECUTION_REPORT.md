# M73 Preflight 执行报告

生成日期：2026-04-26

## Summary

M73 preflight 已完成。两份外部评估已经吸收到 [M73 Preflight 与能力层开发计划](M73_PREFLIGHT_AND_CAPABILITY_PLAN.md)，原始报告已归档：

- [PROJECT_DEEP_EVALUATION_M73_OPUS.md](docs/archive/evaluations/PROJECT_DEEP_EVALUATION_M73_OPUS.md)
- [GPT_EVALUATION.md](docs/archive/evaluations/GPT_EVALUATION.md)

本轮结论：

```text
M73 capability-layer development: GO
```

GO 的含义不是“没有任何技术债”，而是：M73 能力层开发的准入门槛已经补齐，已知 blocking gate 均通过。后续能力开发仍必须保持 workflow dogfood、scoped receipt、provider live proof、evidence、operator packet 和 bug-first 规则。

## Completed Changes

### 1. 外部评估吸收

- 新增 [M73_PREFLIGHT_AND_CAPABILITY_PLAN.md](M73_PREFLIGHT_AND_CAPABILITY_PLAN.md)。
- 将 Opus 报告作为红队准入提醒吸收：manifest 不是代码质量评估、M68 LangGraph 只是 advisory、closeout gates 必须补跑。
- 将 GPT 报告作为 M73 能力层路线吸收：Capability enforcement、MCP Broker、AutomationLease、LangGraph real-runtime spike、Manifest provenance。
- 两份外部评估移入 `docs/archive/evaluations/`。

### 2. Governance quick wins

- 新增 [docs/archive/evaluations/README.md](docs/archive/evaluations/README.md)，给历史评估和执行报告建立索引。
- 新增 [docs/governance/optional_modules.json](docs/governance/optional_modules.json)，登记 scheduler authority cluster runtime、remote worker API、external worker pools 的 review/delete 条件。
- README 增加架构图，并明确 M68 LangGraph 是 advisory comparison，不是 runtime substrate。
- `docs/milestone_history.md` 将 M68 口径收敛为 LangGraph advisory comparison。

### 3. Code cleanup

- 删除无 active import 的 `packages/core_domain/local_game_artifacts.py` shim。
- 当前 game artifact 入口保留在 `packages/contributions/games/local_game_artifacts.py`。
- 新增回归测试确认 core domain 不再保留 game artifact compatibility shim。

### 4. Manifest provenance

`workflowctl governance self-development-manifest` 保持旧 JSON 兼容，同时为每个 milestone 增加 additive `provenance` 字段：

- `execution_report_path`
- `state_directory_paths`
- `task_card_paths`
- `evidence_paths`
- `operator_packet_paths`
- `evidence_category_counts`
- `traceability_status`
- `missing_links`

当前 M67-M72 manifest 仍为 `GO`，并且 provenance 均为 `complete`。

## Workflow Evidence

M73 preflight task cards：

- `state/m73_preflight_capability/task_cards/M73PREFLIGHT_001_plan_and_report.md`
- `state/m73_preflight_capability/task_cards/M73PREFLIGHT_002_quick_wins.md`
- `state/m73_preflight_capability/task_cards/M73PREFLIGHT_003_manifest_provenance.md`
- `state/m73_preflight_capability/task_cards/M73PREFLIGHT_004_closeout_gates.md`
- `state/m73_preflight_capability/task_cards/M73PREFLIGHT_005_final_packet.md`

Workflow previews：

- `state/m73_preflight_capability/evidence/preflight_plan_graph.json`
- `state/m73_preflight_capability/evidence/preflight_policy_preview.json`
- `state/m73_preflight_capability/evidence/preflight_goal_packet.json`

## Gate Results

| Gate | Evidence | Result |
| --- | --- | --- |
| Doc links | `state/m73_preflight_capability/evidence/doc_links_final_after_debt_update.json` | passed |
| Doctor strict | `state/m73_preflight_capability/evidence/doctor_strict.json` | passed |
| Unit matrix | `state/m73_preflight_capability/evidence/test_matrix_unit.json` | 57 passed |
| Core matrix | `state/m73_preflight_capability/evidence/test_matrix_core.json` | 93 passed |
| Integration matrix | `state/m73_preflight_capability/evidence/test_matrix_integration.json` | 7 passed, 134 skipped |
| Full validation | `state/m73_preflight_capability/evidence/validation_full_skip_offline_probe.json` | overall passed |
| Slow pytest | `state/m73_preflight_capability/evidence/pytest_run_slow.txt` | 465 passed |
| Capability live probe | `state/m73_preflight_capability/evidence/capability_probe_all_live.json` | overall passed, blocked_count 0 |

Notes:

- Integration matrix returns green but currently has many skipped API/CLI/Web tests by suite selection. This is recorded as a coverage characteristic, not hidden.
- Full validation was run with `--skip-offline-probe`, matching the current local closeout convention.
- All-provider require-live probe passed for shell, Codex, OpenCode, MMX, Vertex, Claude, and LangChain.

## Remaining Non-Blocking Debt

- `M67-CARRY-001` remains non-blocking: repositories, lifecycle, projection, interaction catalog, and models are still large and should be ratcheted when touched.
- LangGraph is not runtime substrate yet. M73D must keep the first real-runtime spike non-mutating.
- Capability control-plane is ready for an enforcement pilot, but not yet full-path mandatory enforcement.
- MCP still needs per-task broker semantics before more MCP expansion.
- AutomationLease v0 remains unimplemented and is the right next step for bounded unattended execution.

## M73 Next Phase Recommendation

Proceed in this order:

1. **M73A Capability Enforcement Pilot**: enforce live proof + write_set + receipt on one real mutation path.
2. **M73B MCP Broker v1**: canonical tool IDs and per-task projection.
3. **M73C AutomationLease v0**: bounded unattended execution lease.
4. **M73D LangGraph Real-Runtime Spike**: non-mutating checkpoint/interruption/resume path.
5. **M73E Manifest V2 Provenance**: task_card -> run_id -> evidence -> test_result -> commit_sha traceability.

## Decision

M73 preflight is complete.

```text
GO for capability-layer development, with gates retained.
```
