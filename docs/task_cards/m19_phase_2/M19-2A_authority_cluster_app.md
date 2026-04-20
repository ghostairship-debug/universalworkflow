# M19-2A - Add the scheduler authority API app with proposal, vote, heartbeat, release, lease, and cluster endpoints.

Status: planned

## Goal

Add the scheduler authority API app with proposal, vote, heartbeat, release, lease, and cluster endpoints.

## Scope

- Ship the authority peer app, quorum voting, and committed lease log.
- keep the work aligned to TD-021 final repayment track

## Write Set

- `apps/scheduler_authority_api/main.py`
- `packages/core_domain/scheduler_authority.py`
- `tests/test_scheduler_authority_api.py`

## Read Set

- `packages/core_domain/config.py`
- `packages/core_domain/repositories.py`

## Tests

- `python -m pytest tests/test_scheduler_authority_api.py -q`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
