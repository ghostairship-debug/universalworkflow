# M1 Phase 2 Task Cards

## Reassessment

- Phase 1 已经把 contracts、migration 和 repository 能力铺好了。
- 当前最自然的下一步是把 `suggest()` 和 compile surface 做成 operator 可见入口。
- 本阶段仍然不碰 resume 的真实执行和 human review。

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output | Doc Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `P2-T01` | `complex` | 实现 deterministic heuristic `PresetResolver.suggest(goal_text)` 与 suggestion tests | `Phase 1 gate` | `packages/core_domain/resolver.py`, `infra/seeds/presets.json`, `tests/test_contracts.py` | `packages/core_domain/resolver.py`, `tests/test_contracts.py` | suggestion determinism tests | suggestion engine | [P2-T01_deterministic_suggestion.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_2/P2-T01_deterministic_suggestion.md:1) |
| `P2-T02` | `complex` | 扩展 compile service 与 compile snapshot，支持 compile / recompile / status-detail / handoffs 查询 | `P2-T01` | `packages/core_domain/compile.py`, `packages/core_domain/services.py`, `packages/core_domain/repositories.py`, `packages/runtime_langgraph/gateway.py`, `tests/test_api.py`, `tests/test_cli.py` | `packages/core_domain/compile.py`, `packages/core_domain/services.py`, `packages/core_domain/repositories.py`, `tests/test_api.py`, `tests/test_cli.py`, `tests/test_execution_loop.py` | service + integration tests | public compile surface | [P2-T02_compile_service_and_status_detail.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_2/P2-T02_compile_service_and_status_detail.md:1) |
| `P2-T03` | `complex` | 新增 compile / recompile / status-detail / handoffs 的 API 与 CLI 入口，并保持 `POST /runs` 边界不变 | `P2-T02` | `apps/orchestrator_api/main.py`, `apps/operator_cli/main.py`, `README.md`, `tests/test_api.py`, `tests/test_cli.py` | `apps/orchestrator_api/main.py`, `apps/operator_cli/main.py`, `README.md`, `tests/test_api.py`, `tests/test_cli.py` | API + CLI tests | operator surface delta | [P2-T03_api_and_cli_compile_surface.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_2/P2-T03_api_and_cli_compile_surface.md:1) |
| `P2-T04` | `complex` | 形成 Phase 2 gate 证据，验证 `suggest()`、compile、recompile 和查询面 | `P2-T01`, `P2-T02`, `P2-T03` | `tests/test_contracts.py`, `tests/test_api.py`, `tests/test_cli.py`, `tests/test_execution_loop.py` | `tests/test_contracts.py`, `tests/test_api.py`, `tests/test_cli.py`, `tests/test_execution_loop.py` | targeted `pytest` | Phase 2 gate proof | [P2-T04_phase_gate_tests.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_2/P2-T04_phase_gate_tests.md:1) |

## Gate Checklist

- `suggest()` 稳定返回排序结果和 reason
- compile / recompile 已可从 CLI / API 调用
- `POST /runs` 仍不自动 compile
- status-detail / handoffs 已可查询
- Phase 2 targeted tests 通过

## Gate Review Result

- Decision: `pass`
- 结论：Phase 2 已完成 deterministic suggestion 与 public compile surface，且 targeted tests 已通过。
- 验证结果：`pytest tests/test_contracts.py tests/test_api.py tests/test_cli.py tests/test_execution_loop.py`
