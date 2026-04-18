# M4 Phase 1 Task Cards

**Phase:** `M4 Phase 1 - Capability Registry And Minimal Domain Pack Baseline`  
**Status:** Completed

## Scope Lock

- Extract a real `CapabilityRegistry` from hardcoded routing.
- Add only one enabled seed-backed domain pack.
- Prove the baseline through compile/status/smoke surfaces.
- Do not introduce a full domain-pack platform or dynamic plugin system.

## Task Cards

| ID | Complexity | Goal | Depends On | Primary Files | Write Scope | Verification | Exit Signal |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P1-T01` | `complex` | Introduce `CapabilityRegistry`, `DomainPackDefinition`, seed loading, and compile-time domain-pack projection | `Phase 1 entry` | `packages/contracts/*`, `packages/core_domain/compile.py`, `packages/core_domain/domain_packs.py`, `packages/worker_adapters/*`, `infra/seeds/domain_packs.json`, `tests/test_contracts.py`, `tests/test_execution_loop.py` | contracts + registries + compile + adapter routing | contract + execution tests | registry-backed capability and minimal domain-pack baseline exist |
| `P1-T02` | `complex` | Project capability/domain-pack resolution through service, CLI, API, smoke, and offline validation | `P1-T01` | `packages/core_domain/services.py`, `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `infra/scripts/manage.py`, `infra/scripts/offline_validation.py`, `tests/test_api.py`, `tests/test_cli.py` | runtime surfaces + validation | CLI/API + validation | `M4 Smoke` proof is operator-visible and machine-checked |
| `P1-T03` | `medium` | Update phase docs, README, and review notes, then close out the phase | `P1-T01`, `P1-T02` | `README.md`, `m4_phase_docs/`, `docs/task_cards/`, `docs/reviews/` | docs + review | full `pytest` + offline validation | phase is documented and ready for next reassessment |

## Exit Criteria

- All three task cards are completed.
- `software_delivery_pack` is listable and active for the targeted presets.
- `CapabilityRegistry` routes are listable and used by `WorkerRouter`.
- `pytest -q` passes.
- `python -m infra.scripts.offline_validation --skip-offline-probe` passes.

## Closeout

- `P1-T01` completed: contracts, compile decoration, domain-pack seed, and registry-backed adapter routing landed.
- `P1-T02` completed: service, CLI, API, smoke, and offline validation now project domain-pack and capability-route evidence.
- `P1-T03` completed: README, phase docs, and review notes now reflect the actual M4 baseline.
- Final verification:
  - `pytest tests/test_contracts.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q` (`143 passed`)
  - `pytest -q` (`158 passed`)
  - `python -m infra.scripts.offline_validation --skip-offline-probe` (`overall_passed=true`)
