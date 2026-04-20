# M18-4A - Hosted Demo And Release-Readiness Hardening

Status: complete

## Goal

Make the first slice honest in governance and hosted demo claims.

## Scope

- Update governance and release-readiness surfaces so TD-021 narrows instead of disappearing.
- keep the work aligned to TD-021 Multi-Control-Plane First Slice

## Write Set

- `packages/core_domain/governance.py`
- `docs/tech-debt-registry.md`
- `docs/governance/tech_debt_registry.json`
- `tests/test_governance.py`
- `tests/test_cli.py`
- `tests/test_api.py`

## Read Set

- `docs/reviews/m15-freeze-review.md`
- `docs/reviews/post-m18-integrated-technical-roadmap.md`

## Tests

- `python -m pytest tests/test_governance.py tests/test_cli.py tests/test_api.py -q -k governance`

## Completion Evidence

- implementation landed in the declared write set
- declared tests passed for the shipped baseline
- closeout folded into the milestone freeze review
