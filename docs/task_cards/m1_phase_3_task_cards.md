# M1 Phase 3 Task Cards

## Reassessment

- compile 已公开，`RuntimeStateRef` 已持久化，因此 Phase 3 可以直接接 `resume`
- 当前 `execute_run()` 仍是 M0 风格直接执行入口，需要退化为兼容层
- 当前 `cancel_run()` 仍缺幂等与状态守卫

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output | Doc Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `P3-T01` | `complex` | 实现 `resume_run()`，让 persisted `RuntimeStateRef` 真正进入执行主链并写入 `runtime_resumed` | `Phase 2 gate` | `packages/core_domain/services.py`, `packages/runtime_langgraph/gateway.py`, `packages/core_domain/repositories.py`, `tests/test_execution_loop.py` | `packages/core_domain/services.py`, `tests/test_execution_loop.py` | resume path tests | resumable runtime core | [P3-T01_resume_service_and_state_progression.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_3/P3-T01_resume_service_and_state_progression.md:1) |
| `P3-T02` | `complex` | 为 `execute_run()` 和 `cancel_run()` 增加状态守卫、幂等与 UoW 接线 | `P3-T01` | `packages/core_domain/services.py`, `packages/core_domain/errors.py`, `tests/test_execution_loop.py`, `tests/test_cli.py` | `packages/core_domain/services.py`, `tests/test_execution_loop.py`, `tests/test_cli.py` | invalid transition + idempotent cancel tests | state guard delta | [P3-T02_execute_cancel_guards_and_uow.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_3/P3-T02_execute_cancel_guards_and_uow.md:1) |
| `P3-T03` | `complex` | 新增 resume 的 API / CLI surface，并把旧 execute 兼容路径保持可用 | `P3-T01`, `P3-T02` | `apps/orchestrator_api/main.py`, `apps/operator_cli/main.py`, `tests/test_api.py`, `tests/test_cli.py` | `apps/orchestrator_api/main.py`, `apps/operator_cli/main.py`, `tests/test_api.py`, `tests/test_cli.py` | resume API/CLI tests | operator resume surface | [P3-T03_resume_api_and_cli_surface.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_3/P3-T03_resume_api_and_cli_surface.md:1) |
| `P3-T04` | `complex` | 形成 Phase 3 gate 证据，验证 resume、terminal state ref 与 cancel idempotency | `P3-T01`, `P3-T02`, `P3-T03` | `tests/test_api.py`, `tests/test_cli.py`, `tests/test_execution_loop.py` | `tests/test_api.py`, `tests/test_cli.py`, `tests/test_execution_loop.py` | targeted `pytest` | Phase 3 gate proof | [P3-T04_phase_gate_tests.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_phase_3/P3-T04_phase_gate_tests.md:1) |

## Gate Checklist

- `resume_run()` 进入真实主链
- terminal state ref 已更新
- cancel 重复调用幂等
- resume API / CLI 可用
- Phase 3 targeted tests 通过

## Gate Review Result

- Decision: `pass`
- 结论：Phase 3 已完成 resume 主链、terminal state ref 更新和 cancel idempotency。
- 验证结果：`pytest tests/test_api.py tests/test_cli.py tests/test_execution_loop.py`
