# M19-1A - Add authority-node, term, vote, committed-lease, fencing, and takeover contracts plus persistence.

Status: planned

## Goal

Add authority-node, term, vote, committed-lease, fencing, and takeover contracts plus persistence.

## Scope

- Add the multi-authority quorum contracts and cluster config surface.
- keep the work aligned to TD-021 final repayment track

## Write Set

- `packages/contracts/models.py`
- `packages/contracts/__init__.py`
- `packages/core_domain/repositories.py`
- `infra/migrations/013_m19_scheduler_cluster.sql`
- `tests/test_contracts.py`
- `tests/test_repositories.py`

## Read Set

- `packages/core_domain/services.py`
- `packages/core_domain/service_projection.py`

## Tests

- `python -m pytest tests/test_contracts.py tests/test_repositories.py -q -k authority`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
