# M19-1B - Extend workflow.toml with control-plane and scheduler-authority cluster config.

Status: planned

## Goal

Extend workflow.toml with control-plane and scheduler-authority cluster config.

## Scope

- Add the multi-authority quorum contracts and cluster config surface.
- keep the work aligned to TD-021 final repayment track

## Write Set

- `packages/core_domain/config.py`
- `README.md`
- `tests/test_cli.py`
- `tests/test_api.py`

## Read Set

- `apps/orchestrator_api/main.py`
- `apps/operator_cli/main.py`

## Tests

- `python -m pytest tests/test_cli.py tests/test_api.py -q -k config`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
