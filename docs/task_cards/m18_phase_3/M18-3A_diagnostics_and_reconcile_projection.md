# M18-3A - Cross-Control-Plane Diagnostics And Reconcile View

Status: complete

## Goal

Expose conflicts, stale authority leases, and restart-safe arbitration views.

## Scope

- Project conflict diagnostics and expired authority-lease findings into inspection and replay.
- keep the work aligned to TD-021 Multi-Control-Plane First Slice

## Write Set

- `packages/core_domain/services.py`
- `packages/core_domain/service_projection.py`
- `tests/test_api.py`

## Read Set

- `packages/core_domain/repositories.py`
- `packages/contracts/models.py`

## Tests

- `python -m pytest tests/test_api.py -q -k scheduler_authority`

## Completion Evidence

- implementation landed in the declared write set
- declared tests passed for the shipped baseline
- closeout folded into the milestone freeze review
