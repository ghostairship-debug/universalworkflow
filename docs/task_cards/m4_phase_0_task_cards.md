# M4 Phase 0 Task Cards

**Phase:** `M4 Phase 0 - Run-Level Review Policy Runtime Expansion`
**Status:** Completed

## Scope Lock

- Implement only `recommended` and `mandatory` as executable policies.
- Keep `optional` as reference-only.
- Do not add new run statuses.
- Do not add new review persistence tables.

## Task Cards

| ID | Complexity | Goal | Depends On | Primary Files | Write Scope | Verification | Exit Signal |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P0-T01` | `medium` | Expand contracts, presets, decision-table, and governance coverage for executable review-policy growth | `Phase 0 entry` | `packages/contracts/models.py`, `infra/seeds/presets.json`, `packages/core_domain/resolver.py`, `packages/core_domain/governance.py`, `docs/reviews/m1_review_semantics_decision_table.md`, `tests/test_contracts.py`, `tests/test_governance.py` | contracts + seed + governance + docs | contract + governance tests | executable policy catalog is defined and documented |
| `P0-T02` | `complex` | Implement `recommended` fail-escalation and `mandatory` always-human-signoff, plus projection compatibility | `P0-T01` | `packages/core_domain/services.py`, `tests/test_execution_loop.py`, `tests/test_api.py`, `tests/test_cli.py` | service + runtime behavior + regression tests | execution loop + CLI/API tests | runtime behavior matches the phase target semantics |
| `P0-T03` | `medium` | Update README, offline validation, review notes, and phase closeout materials | `P0-T02` | `README.md`, `infra/scripts/offline_validation.py`, `docs/tech-debt-registry.md`, `docs/legacy_ai_agent_reference_plan.md`, `docs/reviews/`, `m4_phase_docs/` | docs + validation | offline validation + full pytest | phase is fully documented and ready for next reassessment |

## Exit Criteria

- All three task cards are completed.
- `pytest -q` passes.
- `python -m infra.scripts.offline_validation --skip-offline-probe` passes.
- `TD-006` notes reflect the new runtime baseline and the still-open `optional` gap.

## Closeout

- `P0-T01` completed: contracts / presets / governance / decision-table baseline updated and verified.
- `P0-T02` completed: runtime routing and projection compatibility implemented and verified.
- `P0-T03` completed: README, offline validation, debt notes, and legacy-reference status updated.
- Final verification:
  - `pytest -q` (`153 passed`)
  - `python -m infra.scripts.offline_validation --skip-offline-probe` (`overall_passed=true`)
