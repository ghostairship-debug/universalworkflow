# PM8-D6 - Release Readiness Provenance

## Objective

Make release-readiness and related governance surfaces explicit about which validation evidence and governance contracts they depend on.

## Write Set

- `packages/core_domain/governance.py`
- `README.md`
- `docs/reviews/pm8-phase-d-validation-governance-context-review.md`

## Required Outcomes

- release-readiness reports include explicit validation provenance
- source paths distinguish canonical structured source vs compatibility fallback
- phase review captures resulting gate state and any remaining debts

## Verification

- governance + CLI/API tests
- full `pytest`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
