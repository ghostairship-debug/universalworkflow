# M20-2B - Prove delayed, duplicate, and stale callbacks fail closed without corrupting runtime truth.

Status: planned

## Goal

Prove delayed, duplicate, and stale callbacks fail closed without corrupting runtime truth.

## Scope

- Guarantee idempotent rejection of stale or duplicate callbacks.
- keep the work aligned to TD-021 retirement and core completion

## Write Set

- `packages/core_domain/services.py`
- `tests/test_api.py`
- `tests/test_execution_loop.py`

## Read Set

- `packages/core_domain/service_projection.py`
- `packages/core_domain/repositories.py`

## Tests

- `python -m pytest tests/test_api.py tests/test_execution_loop.py -q -k callback`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
