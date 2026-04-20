# M16-4A - Test Fix Loop And Mutation Evidence Projection

Status: complete

## Goal

Project bounded fix-loop evidence into audit and replay surfaces.

## Scope

- Add bounded retries and make mutation evidence first-class in status, audit, and replay.
- keep the work aligned to Workflow Repo-Mutation Foundation

## Write Set

- `packages/core_domain/services.py`
- `packages/core_domain/service_projection.py`
- `packages/core_domain/evidence_builder.py`
- `tests/test_execution_loop.py`

## Read Set

- `packages/core_domain/compile.py`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`

## Tests

- `python -m pytest tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q -k mutation`

## Completion Evidence

- implementation landed in the declared write set
- declared tests passed for the shipped baseline
- closeout folded into the milestone freeze review
