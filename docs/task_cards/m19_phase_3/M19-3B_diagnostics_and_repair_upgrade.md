# M19-3B - Upgrade reconcile, inspection, and replay to explain split-brain, stale owner, and authority loss.

Status: planned

## Goal

Upgrade reconcile, inspection, and replay to explain split-brain, stale owner, and authority loss.

## Scope

- Make committed leases and handoff envelopes authoritative for control-plane takeover.
- keep the work aligned to TD-021 final repayment track

## Write Set

- `packages/core_domain/services.py`
- `packages/core_domain/service_projection.py`
- `tests/test_api.py`
- `tests/test_governance.py`

## Read Set

- `README.md`
- `docs/tech-debt-registry.md`

## Tests

- `python -m pytest tests/test_api.py tests/test_governance.py -q -k scheduler`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
