# M10-2B - Projection CLI API And Surface Validation

- Task ID: `M10-2B`
- Phase: `M10 Phase 2 - Local Barrier And Parallel Batch Execution`
- Status: `completed`
- Depends On: `M10-2A`

## Goal

- Surface local batch-barrier state through projections, CLI, API, and focused tests.

## Out Of Scope

- new scheduler topology
- hosted dashboard work
- distributed lease renewal

## Read Set

- `packages/core_domain/service_projection.py`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`
- `tests/test_cli.py`
- `tests/test_api.py`

## Write Set

- Allowed:
  - projection, CLI/API, and focused test files above
  - active phase docs

## Invariants

- `parallel_batch` should be visible in the same operator-facing surfaces that already carry ownership and attempt lineage
- batch execution must stay additive to existing single-run lifecycle paths

## Test Plan

- `python -m pytest tests/test_cli.py tests/test_api.py -q -k "batch or parallel or barrier"`

## Completion Evidence

- Actual modified files:
  - `packages/core_domain/service_projection.py`
  - `apps/operator_cli/main.py`
  - `apps/orchestrator_api/main.py`
  - `tests/test_cli.py`
  - `tests/test_api.py`
- Key behavior delivered:
  - `parallel_batch` projection in `status-detail`, `inspect`, `summary`, and `replay-packet`
  - CLI `run batch-resume`
  - API `POST /runs/batch-resume`
  - CLI `run status` now mirrors `parallel_batch` when present
