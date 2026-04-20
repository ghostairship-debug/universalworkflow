# M18-2A - Authority API And Lease Arbitration Provenance

Status: complete

## Goal

Land the authority APIs and persist arbitration provenance into repository truth.

## Scope

- Add proposal, release, heartbeat, and lease-query APIs plus state-backed arbitration provenance.
- keep the work aligned to TD-021 Multi-Control-Plane First Slice

## Write Set

- `infra/migrations/012_m18_scheduler_authority.sql`
- `packages/core_domain/repositories.py`
- `packages/core_domain/services.py`
- `apps/orchestrator_api/main.py`
- `tests/test_repositories.py`
- `tests/test_api.py`

## Read Set

- `packages/core_domain/service_projection.py`
- `packages/core_domain/governance.py`

## Tests

- `python -m pytest tests/test_repositories.py tests/test_api.py -q -k scheduler_authority`

## Completion Evidence

- implementation landed in the declared write set
- declared tests passed for the shipped baseline
- closeout folded into the milestone freeze review
