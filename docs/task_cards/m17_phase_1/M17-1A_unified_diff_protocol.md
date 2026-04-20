# M17-1A - OpenCode Unified Diff Protocol Freeze

Status: complete

## Goal

Make the coder lane emit bounded unified diff patches as a formal contract.

## Scope

- Freeze the unified-diff-only coder output protocol and invalid-patch failure path.
- keep the work aligned to Workflow Developer Execution Baseline

## Write Set

- `packages/worker_adapters/opencode_adapter.py`
- `packages/core_domain/repo_mutation.py`
- `tests/test_execution_loop.py`

## Read Set

- `packages/contracts/models.py`
- `packages/core_domain/services.py`

## Tests

- `python -m pytest tests/test_execution_loop.py -q -k mutation`

## Completion Evidence

- implementation landed in the declared write set
- declared tests passed for the shipped baseline
- closeout folded into the milestone freeze review
