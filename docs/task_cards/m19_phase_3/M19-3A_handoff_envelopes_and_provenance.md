# M19-3A - Add control-plane handoff envelopes and committed-lease provenance into runtime truth.

Status: planned

## Goal

Add control-plane handoff envelopes and committed-lease provenance into runtime truth.

## Scope

- Make committed leases and handoff envelopes authoritative for control-plane takeover.
- keep the work aligned to TD-021 final repayment track

## Write Set

- `packages/core_domain/services.py`
- `packages/core_domain/service_projection.py`
- `packages/contracts/models.py`
- `tests/test_execution_loop.py`

## Read Set

- `packages/core_domain/repositories.py`
- `packages/core_domain/evidence_builder.py`

## Tests

- `python -m pytest tests/test_execution_loop.py -q -k handoff`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
