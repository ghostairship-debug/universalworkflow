# M19-4B - Cover leader loss, active control-plane loss, standby takeover, and stale-plane fencing drills.

Status: planned

## Goal

Cover leader loss, active control-plane loss, standby takeover, and stale-plane fencing drills.

## Scope

- Run cluster-backed dogfood and failure drills before M19 closeout.
- keep the work aligned to TD-021 final repayment track

## Write Set

- `tests/test_scheduler_authority_api.py`
- `tests/test_api.py`
- `infra/validation/common.py`

## Read Set

- `packages/core_domain/services.py`
- `packages/core_domain/scheduler_authority.py`

## Tests

- `python -m pytest tests/test_scheduler_authority_api.py tests/test_api.py -q -k authority`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
