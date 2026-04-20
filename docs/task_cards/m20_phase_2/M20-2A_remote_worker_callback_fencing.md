# M20-2A - Finalize remote worker callback validation with lease and fencing context.

Status: planned

## Goal

Finalize remote worker callback validation with lease and fencing context.

## Scope

- Require committed lease context on remote worker callbacks.
- keep the work aligned to TD-021 retirement and core completion

## Write Set

- `apps/remote_worker_api/main.py`
- `packages/core_domain/services.py`
- `packages/core_domain/external_workers.py`
- `tests/test_api.py`

## Read Set

- `packages/contracts/models.py`
- `packages/core_domain/scheduler_authority.py`

## Tests

- `python -m pytest tests/test_api.py -q -k callback`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
