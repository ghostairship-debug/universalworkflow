# M17-2A - Project Delivery Repo-Mutation Coder Lane

Status: complete

## Goal

Upgrade project_delivery coder runs from artifact-only to bounded repo mutation.

## Scope

- Carry mutation contracts through project_delivery coder child runs and reviewer evidence.
- keep the work aligned to Workflow Developer Execution Baseline

## Write Set

- `packages/core_domain/services.py`
- `packages/core_domain/service_projection.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`

## Read Set

- `packages/worker_adapters/opencode_adapter.py`
- `packages/core_domain/compile.py`

## Tests

- `python -m pytest tests/test_execution_loop.py tests/test_api.py -q -k project_delivery`

## Completion Evidence

- implementation landed in the declared write set
- declared tests passed for the shipped baseline
- closeout folded into the milestone freeze review
