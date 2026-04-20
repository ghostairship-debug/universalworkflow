# M16-3A - Controlled Patch Apply And Write-Set Guardrails

Status: complete

## Goal

Enforce fail-closed patch parsing and write-set validation.

## Scope

- Implement patch parsing, touched-path validation, and fail-closed repo mutation application.
- keep the work aligned to Workflow Repo-Mutation Foundation

## Write Set

- `packages/core_domain/repo_mutation.py`
- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`

## Read Set

- `packages/worker_adapters/opencode_adapter.py`
- `packages/core_domain/service_projection.py`

## Tests

- `python -m pytest tests/test_execution_loop.py -q -k mutation`

## Completion Evidence

- implementation landed in the declared write set
- declared tests passed for the shipped baseline
- closeout folded into the milestone freeze review
