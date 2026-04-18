# P4-T03 - Memory Item Surfaces Validation And Closeout

**Status:** Completed  
**Phase:** `M6 Phase 4 - Persistent Memory Item Baseline`

## Goal

Expose stored memory items through operator-facing surfaces and extend validation/docs so the new baseline is visible and testable.

## Scope

- add CLI surfaces for:
  - `run materialize-memory`
  - `run memory-items`
  - `memory item list`
- add API surfaces for:
  - `POST /runs/{id}/memory-items`
  - `GET /runs/{id}/memory-items`
  - `GET /memory/items`
- extend offline validation
- update README and phase closeout docs

## Primary Files

- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`
- `infra/scripts/offline_validation.py`
- `README.md`
- `tests/test_api.py`
- `tests/test_cli.py`

## Verification

- CLI tests cover materialize/list flows
- API tests cover materialize/list flows
- offline validation proves the persistent memory baseline in both CLI and API paths

## Done When

- stored memory items are operator-visible by run and namespace
- materialization is covered in CLI/API/offline validation
- docs describe the new persistent memory baseline clearly
