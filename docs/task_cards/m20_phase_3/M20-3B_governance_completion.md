# M20-3B - Align governance, release-readiness, and debt reporting with the completed consensus model.

Status: planned

## Goal

Align governance, release-readiness, and debt reporting with the completed consensus model.

## Scope

- Update governance outputs to describe TD-021 as complete once the evidence exists.
- keep the work aligned to TD-021 retirement and core completion

## Write Set

- `packages/core_domain/governance.py`
- `tests/test_api.py`
- `tests/test_execution_loop.py`

## Read Set

- `docs/tech-debt-registry.md`
- `docs/governance/tech_debt_registry.json`

## Tests

- `python -m pytest tests/test_api.py -q -k governance`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
