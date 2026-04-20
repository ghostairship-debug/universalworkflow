# M19-4A - Add cluster demo tooling and dogfood workflow execution for 3 authority peers and 2 control planes.

Status: planned

## Goal

Add cluster demo tooling and dogfood workflow execution for 3 authority peers and 2 control planes.

## Scope

- Run cluster-backed dogfood and failure drills before M19 closeout.
- keep the work aligned to TD-021 final repayment track

## Write Set

- `infra/validation/common.py`
- `infra/validation/api_flow.py`
- `infra/validation/cli_flow.py`
- `README.md`

## Read Set

- `apps/scheduler_authority_api/main.py`
- `apps/orchestrator_api/main.py`

## Tests

- `python -m infra.scripts.offline_validation --skip-offline-probe`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
