# M9-4B - Optional Policy Seed And Governance Surfaces

- Task ID: `M9-4B`
- Phase: `M9 Phase 4 - Optional Review Policy Completion`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9-4A`

## Goal

- Add seed/runtime coverage for `optional`.
- Remove "reference-only" treatment from governance, readiness, CLI/API, and validation surfaces.

## Out Of Scope

- closing the milestone in docs
- concurrency work
- other review-policy families

## Read Set

- `infra/seeds/presets.json`
- `infra/seeds/domain_packs.json`
- `infra/seeds/simulation_policies.json`
- `packages/core_domain/governance.py`
- `packages/core_domain/resolver.py`
- `docs/governance/review_policy_cases.json`
- `infra/validation/cli_flow.py`
- `infra/validation/api_flow.py`
- `tests/test_governance.py`
- `tests/test_cli.py`
- `tests/test_api.py`
- `tests/test_contracts.py`
- `tests/test_repositories.py`

## Write Set

- Allowed:
  - `infra/seeds/presets.json`
  - `infra/seeds/domain_packs.json`
  - `infra/seeds/simulation_policies.json`
  - `packages/core_domain/governance.py`
  - `packages/core_domain/resolver.py`
  - `docs/governance/review_policy_cases.json`
  - `infra/validation/cli_flow.py`
  - `infra/validation/api_flow.py`
  - `tests/test_governance.py`
  - `tests/test_cli.py`
  - `tests/test_api.py`
  - `tests/test_contracts.py`
  - `tests/test_repositories.py`
- Avoid:
  - unrelated runtime lifecycle code
  - debt registry closeout files

## Interfaces And Data Changes

- add `optional_delivery` preset coverage
- update domain-pack and simulation-policy seed linkage
- update governance review-policy report to support five executable policies
- update release-readiness to treat `TD-006` as repaid once closeout lands

## Invariants

- operator surfaces must no longer describe `optional` as reference-only
- seed changes must remain backward compatible with existing preset resolution
- validation flows must recognize the five-policy baseline

## Implementation Steps

1. Add `optional_delivery` to seeds and preset resolution.
2. Update governance and review-policy case docs for executable `optional`.
3. Update offline validation expectations and regression tests.
4. Leave final debt retirement wording for Phase 5.

## Test Plan

- `python -m pytest tests/test_governance.py -q`
- `python -m pytest tests/test_contracts.py tests/test_repositories.py -q`
- `python -m pytest tests/test_cli.py tests/test_api.py -q`
- later `python -m pytest -q`

## Risks And Rollback

- Main risk: seed/governance surfaces disagree on how many executable policies exist.
- Roll back by making governance counts derive from the shared enum plus seed-aware preset mapping.

## Completion Evidence

- Actual modified files:
  - `infra/seeds/presets.json`
  - `infra/seeds/domain_packs.json`
  - `infra/seeds/simulation_policies.json`
  - `packages/core_domain/governance.py`
  - `packages/core_domain/resolver.py`
  - `docs/governance/review_policy_cases.json`
  - `infra/validation/cli_flow.py`
  - `infra/validation/api_flow.py`
  - `tests/test_governance.py`
  - `tests/test_cli.py`
  - `tests/test_api.py`
  - `tests/test_contracts.py`
  - `tests/test_repositories.py`
- Validation:
  - targeted governance, contract/repository, CLI, and API tests passed
  - later full `python -m pytest -q` passed
- Implementation note:
  - `optional` became executable across runtime, seed, governance, and validation surfaces before debt retirement was recorded
