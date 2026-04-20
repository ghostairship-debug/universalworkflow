# M20-1B - Reject stale owners and preserve conflict diagnostics across takeover boundaries.

Status: planned

## Goal

Reject stale owners and preserve conflict diagnostics across takeover boundaries.

## Scope

- Ensure stale control planes cannot mutate runtime truth after takeover.
- keep diagnostics explicit for stale-owner rejections and takeover provenance.

## Write Set

- `packages/core_domain/services.py`
- `packages/core_domain/service_projection.py`
- `tests/test_api.py`

## Read Set

- `packages/core_domain/scheduler_authority.py`
- `packages/core_domain/repositories.py`

## Tests

- `python -m pytest tests/test_api.py -q -k stale_owner`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
