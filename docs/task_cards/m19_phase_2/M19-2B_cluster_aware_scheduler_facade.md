# M19-2B - Upgrade the orchestrator scheduler facade to consume cluster-backed committed leases.

Status: planned

## Goal

Upgrade the orchestrator scheduler facade to consume cluster-backed committed leases.

## Scope

- Ship the authority peer app, quorum voting, and committed lease log.
- keep the work aligned to TD-021 final repayment track

## Write Set

- `packages/core_domain/services.py`
- `apps/orchestrator_api/main.py`
- `packages/core_domain/service_projection.py`
- `tests/test_api.py`

## Read Set

- `packages/core_domain/scheduler_authority.py`
- `packages/core_domain/governance.py`

## Tests

- `python -m pytest tests/test_api.py -q -k scheduler`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
