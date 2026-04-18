# M4 Phase 2 Task Cards

**Phase:** `M4 Phase 2 - Golden Demo And Release Readiness Closeout`  
**Status:** Completed

## Scope Lock

- Package the shipped runtime into release-shaped operator surfaces.
- Keep the surface CLI-first and API-visible.
- Do not expand the runtime model again.

## Task Cards

| ID | Complexity | Goal | Depends On | Primary Files | Write Scope | Verification | Exit Signal |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P2-T01` | `medium` | Add a structured release-readiness governance report that projects current validation and milestone gates | `Phase 2 entry` | `packages/core_domain/governance.py`, `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_governance.py`, `tests/test_cli.py`, `tests/test_api.py` | governance + operator surfaces | governance + CLI/API tests | release readiness is machine-readable |
| `P2-T02` | `complex` | Add a canonical golden-demo runner on a fresh DB and verify it across representative run paths | `P2-T01` | `infra/scripts/manage.py`, `tests/`, `README.md` | demo runner + docs | demo tests + full verification | demo packet is stable and useful |
| `P2-T03` | `medium` | Update validation hooks, phase review, and closeout docs | `P2-T01`, `P2-T02` | `infra/scripts/offline_validation.py`, `docs/reviews/`, `m4_phase_docs/`, `docs/task_cards/` | validation + docs | offline validation + full pytest | phase is closed cleanly |

## Exit Criteria

- All three task cards are completed.
- `governance release-readiness` is available in CLI and API.
- `python -m infra.scripts.manage --db-path state/workflow.db demo` succeeds.
- `pytest -q` passes.
- `python -m infra.scripts.offline_validation --skip-offline-probe` passes.

## Closeout

- `P2-T01` completed: release-readiness governance report now projects validation, capability routes, domain-pack baseline, and milestone gates through CLI/API.
- `P2-T02` completed: `manage.py demo` now produces a canonical local golden-demo packet across all representative run paths.
- `P2-T03` completed: README, offline validation, and review materials now reflect the shipped closeout baseline.
- Final verification:
  - `pytest tests/test_governance.py tests/test_api.py tests/test_cli.py tests/test_release_closeout.py -q` (`78 passed`)
  - `pytest -q` (`162 passed`)
  - `python -m infra.scripts.manage --db-path state/demo_phase2.db demo` (`status=completed`)
  - `python -m infra.scripts.offline_validation --skip-offline-probe` (`overall_passed=true`)
