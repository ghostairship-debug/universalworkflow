# M1 Phase 1 Task Cards

## Reassessment

- Phase 0 已经把状态机、suggest、human review、runtime 边界和 UoW 粒度冻结好了。
- 因此，Phase 1 不再讨论“应该怎么做”，而是把这些冻结项落成 contracts、migration 和 repository 能力。
- 当前最关键的风险是把行为逻辑混进 Phase 1；本阶段必须只收口数据层和边界层。

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output | Doc Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `P1-T01` | `complex` | 扩展 contracts 与 runtime interface，加入 `awaiting_review`、`PresetSuggestion`、`RuntimeStateRef` 并把 `RuntimeGateway` 移到 contracts | `Phase 0 gate` | `packages/contracts/models.py`, `packages/contracts/events.py`, `packages/runtime_langgraph/gateway.py`, `tests/test_contracts.py`, `tests/test_runtime_boundary.py` | `packages/contracts/*`, `packages/runtime_langgraph/gateway.py`, `tests/test_contracts.py`, `tests/test_runtime_boundary.py` | contract round-trip + import boundary tests | M1 contract delta | [P1-T01_contracts_and_runtime_interface_delta.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_1/P1-T01_contracts_and_runtime_interface_delta.md:1) |
| `P1-T02` | `complex` | 新增 `002_*` migration，落 `handoff_lite`、`runtime_state_refs` 表并扩展 event schema 所需持久化字段 | `P1-T01` | `infra/migrations/001_init.sql`, `packages/contracts/models.py`, `packages/contracts/events.py`, `tests/test_repositories.py` | `infra/migrations/002_m1_runtime_state_and_handoffs.sql`, `tests/test_repositories.py` | migration repeatability + table round-trip | M1 migration delta | [P1-T02_migration_delta.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_1/P1-T02_migration_delta.md:1) |
| `P1-T03` | `complex` | 扩展 repositories 与 db helper，使写操作支持 connection 注入并新增 handoff / state ref repository | `P1-T02` | `packages/core_domain/db.py`, `packages/core_domain/repositories.py`, `tests/test_repositories.py` | `packages/core_domain/db.py`, `packages/core_domain/repositories.py`, `tests/test_repositories.py` | repository round-trip + injected connection tests | persistence API delta | [P1-T03_repository_and_connection_injection.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_1/P1-T03_repository_and_connection_injection.md:1) |
| `P1-T04` | `complex` | 更新 contracts / repository / runtime boundary 测试，形成 Phase 1 gate 证据 | `P1-T01`, `P1-T02`, `P1-T03` | `tests/test_contracts.py`, `tests/test_repositories.py`, `tests/test_runtime_boundary.py` | `tests/test_contracts.py`, `tests/test_repositories.py`, `tests/test_runtime_boundary.py` | `pytest` targeted suite | Phase 1 gate proof | [P1-T04_phase_gate_tests.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_1/P1-T04_phase_gate_tests.md:1) |

## Gate Checklist

- `P1-T01` ~ `P1-T04` 全部完成
- 所有新增 contract 与持久化对象都可 round-trip
- repository 注入能力可用于后续 UoW
- Phase 2 可以直接在此基础上实现 `suggest()` 与 public compile surface

## Gate Review Result

- Decision: `pass`
- 结论：Phase 1 已完成 contracts / migration / repository 底座扩展，且 targeted tests 已通过。
- 验证结果：`pytest tests/test_contracts.py tests/test_repositories.py tests/test_runtime_boundary.py`
