# P5-T03 - Docs, Debt, And Verification

## Basic Info

- Task ID: `P5-T03`
- Phase: `M1.5`
- Status: `completed`
- Depends On: `P5-T01`, `P5-T02`

## Goal

Close the phase by updating operator-facing docs, repaying `TD-005`, and running full verification for both executor paths.

## Read Set

- `README.md`
- `docs/tech-debt-registry.md`
- `m1_phase_docs/phase_5_second_executor_and_capability_routing.md`
- `docs/task_cards/m1_phase_5_task_cards.md`
- `tests/`

## Write Set

- `README.md`
- `docs/tech-debt-registry.md`
- `m1_phase_docs/phase_5_second_executor_and_capability_routing.md`
- `docs/task_cards/m1_phase_5_task_cards.md`

## Invariants

- doc updates reflect the implemented surface, not speculative future work
- debt repayment must be explicit in the registry

## Implementation Steps

1. Update README with the noop/executor routing path where relevant.
2. Mark `TD-005` as repaid if the second executor is proven by tests.
3. Run full `pytest`.
4. Backfill phase gate results into the phase doc and task-card index.

## Test Plan

- full `pytest`
- spot-check shell and noop command examples if surface changed

## Outcome

- README now documents noop routing and compile-time task-kind selection
- `TD-005` is marked repaid in the debt registry
- full `pytest` passed with `59 passed`
- `offline_validation --skip-offline-probe` passed for shell, human-review, and noop executor flows
