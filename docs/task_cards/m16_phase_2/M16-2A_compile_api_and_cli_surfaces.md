# M16-2A - Compile Recompile Mutation Contract Surfaces

Status: complete

## Goal

Make compile and recompile consume task-card-driven mutation contracts.

## Scope

- Extend CLI/API and runtime compile surfaces to carry write-set/read-set/test directives.
- keep the work aligned to Workflow Repo-Mutation Foundation

## Write Set

- `packages/core_domain/compile.py`
- `packages/core_domain/service_lifecycle.py`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`
- `tests/test_cli.py`
- `tests/test_api.py`

## Read Set

- `packages/contracts/models.py`
- `packages/core_domain/services.py`

## Tests

- `python -m pytest tests/test_cli.py tests/test_api.py -q -k mutation_report`

## Completion Evidence

- implementation landed in the declared write set
- declared tests passed for the shipped baseline
- closeout folded into the milestone freeze review
