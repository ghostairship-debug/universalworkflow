# M10 Phase 2 Task Cards

**Phase:** `M10 Phase 2 - Local Barrier And Parallel Batch Execution`  
**Status:** Complete

This is a complex phase. Every task below has a standalone detailed card.

## Reassessment

- `M10 Phase 1` completed the ownership-topology freeze.
- the remaining `M10` execution gap was still local serial-first resume semantics for prepared runs.
- the approved next step was a small local-first concurrency slice, not distributed scheduling breadth.

## Task Cards

| ID | Complexity | Goal | Depends On | Read Scope | Write Scope | Verification | Exit Signal | Doc Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `M10-2A` | `complex` | Add local batch-barrier runtime semantics, event payloads, and error handling around parallel resume | `Phase entry` | `packages/contracts/events.py`, `packages/core_domain/errors.py`, `packages/core_domain/services.py`, `packages/core_domain/service_lifecycle.py`, `tests/test_execution_loop.py` | contracts, lifecycle/runtime semantics, focused runtime tests, active phase docs | execution-loop barrier tests | prepared runs can cross one local batch barrier without breaking ownership invariants | [M10-2A](m10_phase_2/M10-2A_local_batch_barrier_runtime_semantics.md) |
| `M10-2B` | `complex` | Expose `parallel_batch` through projection, CLI, API, and focused surface tests | `M10-2A` | `packages/core_domain/service_projection.py`, `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_cli.py`, `tests/test_api.py` | projection, CLI/API surfaces, focused tests, active phase docs | CLI + API batch tests | batch resume is operator-visible and replay-visible | [M10-2B](m10_phase_2/M10-2B_projection_cli_api_and_surface_validation.md) |
| `M10-2C` | `medium` | Close the phase and milestone with updated debt, governance, living docs, and freeze-review evidence | `M10-2B` | `README.md`, `docs/current_development_workflow.md`, `docs/tech-debt-registry.md`, `docs/governance/tech_debt_registry.json`, `packages/core_domain/governance.py`, `tests/test_governance.py`, active phase docs | living docs, governance wording, debt registry, review docs, focused governance tests | governance tests + doc link audit + milestone validation | `M10` can close with a truthful next-step instruction | [M10-2C](m10_phase_2/M10-2C_docs_governance_and_milestone_closeout.md) |

## Completion Notes

### `M10-2A`

- Implemented the local batch barrier inside `resume_run()` / `resume_runs_parallel(...)`.
- Fixed the initial SQLite lock failure by committing around barrier boundaries instead of holding the write transaction open.

### `M10-2B`

- Added `parallel_batch` projection, CLI/API batch-resume surfaces, and focused runtime/CLI/API coverage.
- Kept the slice local-first and prepared-run scoped.

### `M10-2C`

- Closed `TD-009`, retired the `M10` debt set, and opened a narrower `M11` debt for external worker-pool breadth.
- Handed the repository off to the `M10` freeze review instead of pre-generating `M11` task cards.
