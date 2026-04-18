# M1.5 Task Cards

## Reassessment

- M1 and the legacy hardening uplift are complete.
- `TD-005` is still open: the repository exposes two task kinds but only one real adapter path.
- The next post-`M1` hardening phase should therefore close the adapter boundary first, before any `M2` repair/reconcile work.
- Historical note: this file stays under `m1_phase_5_task_cards.md` for path stability, but the milestone name is `M1.5`. See [docs/m1_to_m2_progression.md](/D:/Universal%20Agentic%20workflow/docs/m1_to_m2_progression.md:1).
- Scope note: `M1.5` is execution-boundary hardening, not a second dedicated legacy-uplift batch.

Phase outcome:

- `P5-T01`, `P5-T02`, and `P5-T03` are completed.
- `TD-005` is repaid.
- Verification closed with `59 passed` plus `offline_validation --skip-offline-probe` returning `overall_passed=true`.

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P5-T01` | `complex` | Extract shared adapter primitives, add `NoopAdapter`, and introduce a deterministic `WorkerRouter` | `M1.5 entry` | `packages/worker_adapters/shell_adapter.py`, `packages/core_domain/services.py`, `tests/test_execution_loop.py`, `docs/tech-debt-registry.md` | `packages/worker_adapters/*`, `packages/core_domain/services.py`, `tests/test_execution_loop.py` | adapter + execution tests | real second executor boundary |
| `P5-T02` | `complex` | Add compile-time task-kind override, validate preset/task-kind compatibility, and route execution through the selected adapter | `P5-T01` | `packages/core_domain/compile.py`, `packages/contracts/models.py`, `apps/orchestrator_api/main.py`, `apps/operator_cli/main.py`, `tests/test_api.py`, `tests/test_cli.py` | same plus `packages/core_domain/errors.py`, `tests/test_contracts.py` | contract + API + CLI + execution tests | explicit task-kind routing flow |
| `P5-T03` | `complex` | Update docs and debt tracking, then run full verification for shell and noop paths | `P5-T01`, `P5-T02` | `README.md`, `docs/tech-debt-registry.md`, `m1_phase_docs/phase_5_second_executor_and_capability_routing.md`, `tests/` | docs + tests | full `pytest` | phase closeout |

Implementation status:

- `P5-T01`: completed, including `WorkerRouter`, `NoopAdapter`, and shell/noop adapter separation
- `P5-T02`: completed, including compile-time task-kind override, preset allow-list enforcement, and stable CLI/API error coverage
- `P5-T03`: completed, including README updates, `TD-005` repayment, full `pytest`, and noop coverage in offline validation

## Gate Checklist

- `noop` is no longer implemented inside `ShellAdapter`
- `WorkerRouter` is the single runtime entry for adapter selection
- `research_spike` can be compiled with `--task-kind noop`
- task-kind override rejects values outside the preset allow-list
- shell and noop execution paths both pass tests

Gate result:

- Passed for all checklist items
