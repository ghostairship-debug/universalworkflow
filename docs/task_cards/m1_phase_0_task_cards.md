# M1 Phase 0 Task Cards

## Reassessment

- M0 已提供可运行骨架，但 M1 当前仍缺少状态机、compile public surface、handoff 落库、runtime state persistence、human review 闭环和事务边界。
- Gemini 与 Claude Opus 的最新评估都确认 M1 大方向正确，但同时指出 `Phase 0` 必须先冻结 5 类战术细节，否则 Phase 1 之后容易边写边漂移。
- 因此，Phase 0 全部按 `complex task` 执行，不接受轻量卡片。

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output | Doc Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `P0-T01` | `complex` | 冻结 M1 Run Status State Machine、合法状态转换矩阵和对应事件增量 | None | `packages/contracts/models.py`, `packages/contracts/events.py`, `packages/core_domain/services.py`, `tests/test_execution_loop.py`, `M0_Evaluation_Claude_Opus.md` | `m1_phase_docs/phase_0_rebaseline_and_scope_freeze.md`, `docs/task_cards/m1_phase_0/P0-T01_run_status_state_machine.md`, 后续 `packages/contracts/*`, `tests/*` | 文档审查 + Phase 1/3 编码前作为状态守卫输入 | 状态机冻结基线 | [P0-T01_run_status_state_machine.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_0/P0-T01_run_status_state_machine.md:1) |
| `P0-T02` | `complex` | 冻结 `suggest(goal_text)` 的 contract、规则模型与离线确定性策略 | `P0-T01` | `packages/core_domain/resolver.py`, `infra/seeds/presets.json`, `tests/test_contracts.py`, `M1_Evaluation_and_Suggestions.md` | `m1_phase_docs/phase_0_rebaseline_and_scope_freeze.md`, `docs/task_cards/m1_phase_0/P0-T02_suggest_strategy_and_contract_delta.md`, 后续 `packages/core_domain/resolver.py`, `tests/*` | 文档审查 + Phase 2 suggestion 测试输入 | `suggest()` 规则冻结 | [P0-T02_suggest_strategy_and_contract_delta.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_0/P0-T02_suggest_strategy_and_contract_delta.md:1) |
| `P0-T03` | `complex` | 冻结 `human_required` 最小闭环的触发、挂起、approve/reject 与终态语义 | `P0-T01` | `packages/contracts/models.py`, `packages/core_domain/auto_review.py`, `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_cli.py`, `tests/test_api.py` | `m1_phase_docs/phase_0_rebaseline_and_scope_freeze.md`, `docs/task_cards/m1_phase_0/P0-T03_human_review_minimum_loop.md`, 后续 `packages/core_domain/services.py`, `apps/*`, `tests/*` | 文档审查 + Phase 4 测试输入 | human review 闭环冻结 | [P0-T03_human_review_minimum_loop.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_0/P0-T03_human_review_minimum_loop.md:1) |
| `P0-T04` | `complex` | 冻结 runtime “真实主链”边界、`RuntimeStateRef` 语义与 `RuntimeGateway` 归属 | `P0-T01` | `packages/runtime_langgraph/gateway.py`, `tests/test_runtime_boundary.py`, `packages/core_domain/services.py`, `M1_Evaluation_and_Suggestions.md`, `M0_Evaluation_Claude_Opus.md` | `m1_phase_docs/phase_0_rebaseline_and_scope_freeze.md`, `docs/task_cards/m1_phase_0/P0-T04_runtime_boundary_and_state_ref_strategy.md`, 后续 `packages/contracts/*`, `packages/runtime_langgraph/*`, `tests/*` | 文档审查 + Phase 1/3 边界测试输入 | runtime 边界冻结 | [P0-T04_runtime_boundary_and_state_ref_strategy.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_0/P0-T04_runtime_boundary_and_state_ref_strategy.md:1) |
| `P0-T05` | `complex` | 冻结 UoW 边界、连接注入策略和 M1 破坏性迁移策略 | `P0-T01` | `packages/core_domain/db.py`, `packages/core_domain/repositories.py`, `infra/scripts/manage.py`, `infra/scripts/offline_validation.py`, `tests/test_repositories.py` | `m1_phase_docs/phase_0_rebaseline_and_scope_freeze.md`, `docs/task_cards/m1_phase_0/P0-T05_uow_and_migration_policy.md`, 后续 `packages/core_domain/db.py`, `packages/core_domain/repositories.py`, `infra/scripts/*`, `tests/*` | 文档审查 + Phase 1/3 持久化测试输入 | UoW / migration 冻结 | [P0-T05_uow_and_migration_policy.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_0/P0-T05_uow_and_migration_policy.md:1) |

## Gate Checklist

- `P0-T01` ~ `P0-T05` 全部达到 `ready`
- 状态机、suggest、human review、runtime 边界、UoW / migration 5 类冻结项都在 phase 文档中有明确结论
- 没有仍然需要“实现时再决定”的协议级问题
- Phase 1 task cards 可以直接基于这些冻结项下钻到代码级

## Gate Review Result

- Decision: `pass`
- 结论：Phase 0 已完成范围冻结与战术决策冻结，可以进入“基于 Phase 0 冻结结果重新评估并拆解 Phase 1”的下一步。
- 补充说明：本阶段是文档冻结阶段，不涉及代码测试；其完成证据是 phase 文档与 5 张复杂 task 独立 md 已全部落仓，并且关键冻结项已收敛。
