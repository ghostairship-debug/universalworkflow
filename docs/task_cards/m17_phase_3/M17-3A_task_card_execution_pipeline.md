# M17-3A - Task-Card Dogfood Pipeline

Status: complete

## Goal

Let current-phase task cards become direct development execution inputs.

## Scope

- Use task-card refs and task-card paths as first-class developer-execution inputs.
- keep the work aligned to Workflow Developer Execution Baseline

## Write Set

- `packages/core_domain/service_lifecycle.py`
- `packages/core_domain/services.py`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`

## Read Set

- `docs/task_cards/m1_execution_loop_protocol.md`
- `packages/core_domain/compile.py`

## Tests

- `python -m pytest tests/test_cli.py tests/test_api.py -q -k mutation_report`

## Completion Evidence

- implementation landed in the declared write set
- declared tests passed for the shipped baseline
- closeout folded into the milestone freeze review
