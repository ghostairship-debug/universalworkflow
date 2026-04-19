# M9 Phase 4 Task Cards

**Phase:** `M9 Phase 4 - Optional Review Policy Completion`  
**Status:** Complete

This is a complex phase. Every task below has a standalone detailed card.

## Scope Lock

- implement `optional`
- keep existing policies backward compatible
- do not broaden into a new review-policy family beyond `optional`

## Task Cards

| ID | Complexity | Goal | Depends On | Primary Files | Verification | Exit Signal | Doc Link |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `M9-4A` | `complex` | Add executable `optional` review-policy runtime behavior with an advisory-only terminal shape | `M9 Phase 3 complete` | `packages/contracts/models.py`, `packages/core_domain/service_lifecycle.py`, `packages/core_domain/services.py`, `tests/test_execution_loop.py` | targeted lifecycle tests | `optional` works end to end | [M9-4A](m9_phase_4/M9-4A_optional_review_policy_runtime_semantics.md) |
| `M9-4B` | `complex` | Update seed presets plus governance/readiness/CLI/API surfaces for the new policy | `M9-4A` | `infra/seeds/presets.json`, `infra/seeds/domain_packs.json`, `infra/seeds/simulation_policies.json`, `packages/core_domain/governance.py`, `packages/core_domain/resolver.py`, `docs/governance/review_policy_cases.json`, `tests/test_governance.py`, `tests/test_cli.py`, `tests/test_api.py`, `tests/test_contracts.py`, `tests/test_repositories.py` | targeted governance/CLI/API/seed tests | `optional` is no longer reference-only in operator surfaces | [M9-4B](m9_phase_4/M9-4B_optional_policy_seed_and_governance_surfaces.md) |
| `M9-4C` | `medium` | Update docs/reviews for the closed review-policy gap | `M9-4A`, `M9-4B` | `m9_phase_docs/`, `docs/reviews/`, `docs/tech-debt-registry.md` if needed | docs audit | phase can close cleanly | [M9-4C](m9_phase_4/M9-4C_docs_reviews_and_phase_closeout.md) |
