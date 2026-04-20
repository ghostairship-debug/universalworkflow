# M20-4B - Add cluster smoke coverage to offline validation and final hardening checks.

Status: planned

## Goal

Add cluster smoke coverage to offline validation and final hardening checks.

## Scope

- Cover the hosted cutover path in offline validation and hardening flows.
- keep the work aligned to TD-021 retirement and core completion

## Write Set

- `infra/validation/api_flow.py`
- `infra/validation/cli_flow.py`
- `infra/validation/common.py`
- `tests/test_api.py`

## Read Set

- `infra/scripts/offline_validation.py`
- `packages/core_domain/services.py`

## Tests

- `python -m infra.scripts.offline_validation --skip-offline-probe`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
