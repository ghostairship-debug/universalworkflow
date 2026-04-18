# M6 Phase 2 Task Cards

**Phase:** `M6 Phase 2 - Domain Pack Resolution Preview And Catalog Validation`  
**Goal:** Make the platformized domain-pack catalog inspectable and mechanically valid before compile/resume.

## Task Cards

| Task | Size | Goal | Depends On | Primary Files | Verification | Done When |
| --- | --- | --- | --- | --- | --- | --- |
| `P2-T01` | `complex` | Add pack-resolution preview for preset/task-kind pairs | `Phase 2 entry` | `packages/core_domain/domain_packs.py`, `packages/core_domain/services.py`, `tests/test_execution_loop.py` | execution/service tests | pack selection can be previewed before compile |
| `P2-T02` | `complex` | Add catalog-validation report for pack/preset/adapter consistency | `P2-T01` | `packages/core_domain/domain_packs.py`, `packages/core_domain/services.py`, `tests/test_contracts.py`, `tests/test_governance.py` | contract + governance tests | invalid catalog conditions are reported structurally |
| `P2-T03` | `medium` | Expose preview/validation through CLI/API/docs/offline validation | `P2-T01`, `P2-T02` | `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `infra/scripts/offline_validation.py`, `README.md`, `tests/test_api.py`, `tests/test_cli.py` | CLI/API/validation tests | preview/validation is operator-visible and documented |

## Closeout

- `P2-T01` completed: pack-resolution preview exists before compile.
- `P2-T02` completed: catalog validation detects preset/task-kind/adapter consistency issues structurally.
- `P2-T03` completed: preview/validation are exposed through CLI/API/docs/offline validation.
