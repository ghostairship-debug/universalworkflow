# M20-1A - Bind dispatch and lifecycle mutations to quorum-committed lease ownership.

Status: planned

## Goal

Bind dispatch and lifecycle mutations to quorum-committed lease ownership.

## Scope

- Make committed leases and fencing tokens mandatory for cross-plane lifecycle writes.
- keep the work aligned to TD-021 retirement and core completion

## Write Set

- `packages/core_domain/services.py`
- `packages/core_domain/service_lifecycle.py`
- `packages/core_domain/external_workers.py`
- `tests/test_execution_loop.py`

## Read Set

- `packages/core_domain/scheduler_authority.py`
- `packages/contracts/models.py`

## Tests

- `python -m pytest tests/test_execution_loop.py -q -k fencing`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
