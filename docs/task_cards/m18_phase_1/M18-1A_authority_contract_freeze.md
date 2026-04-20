# M18-1A - Control-Plane Identity And Scheduler Authority Contract

Status: complete

## Goal

Introduce durable control-plane identity and scheduler-authority contracts.

## Scope

- Freeze authority-side proposal, decision, and peer heartbeat contracts.
- keep the work aligned to TD-021 Multi-Control-Plane First Slice

## Write Set

- `packages/contracts/models.py`
- `packages/contracts/__init__.py`
- `tests/test_contracts.py`

## Read Set

- `packages/core_domain/services.py`
- `packages/core_domain/repositories.py`

## Tests

- `python -m pytest tests/test_contracts.py -q`

## Completion Evidence

- implementation landed in the declared write set
- declared tests passed for the shipped baseline
- closeout folded into the milestone freeze review
