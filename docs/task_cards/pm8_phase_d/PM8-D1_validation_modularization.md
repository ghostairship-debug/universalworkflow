# PM8-D1 - Validation Modularization

## Objective

Move offline validation from a single oversized script into a validation package with dedicated flow modules and a thin entry runner.

## Write Set

- `infra/validation/`
- `infra/scripts/offline_validation.py`
- `tests/` as needed

## Required Outcomes

- shared validation helpers live in reusable module(s)
- CLI, smoke, and API validation flows are separated into dedicated modules
- `infra/scripts/offline_validation.py` becomes a thin wrapper
- external command line remains stable: `python -m infra.scripts.offline_validation ...`

## Verification

- targeted `pytest`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
