# M9-1B - Run Metrics Surfaces And Focus Data

- Task ID: `M9-1B`
- Phase: `M9 Phase 1 - Replay Linkage And Metrics Baseline`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9-1A`

## Goal

- Add first-class run metrics to operator-facing diagnostics.
- Project metrics through status-detail, summary, audit, inspection, and replay outputs.

## Out Of Scope

- a new dashboard subsystem
- governance metrics
- durable-specific lineage rules beyond what metrics need to observe

## Read Set

- `packages/core_domain/service_projection.py`
- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`
- `tests/test_cli.py`
- `tests/test_api.py`

## Write Set

- Allowed:
  - `packages/core_domain/service_projection.py`
  - `packages/core_domain/services.py`
  - `tests/test_execution_loop.py`
  - `tests/test_cli.py`
  - `tests/test_api.py`
- Avoid:
  - unrelated operator UI files
  - debt registry docs

## Interfaces And Data Changes

- add `run_metrics` to:
  - status detail
  - run summary
  - audit report
  - state inspection
  - replay packet
- metrics include counts, timings, and coverage flags derived from existing runtime artifacts

## Invariants

- metrics must be computed from persisted state, not hidden runtime memory
- new metric fields must not change terminal semantics
- existing operator payloads must remain backward compatible

## Implementation Steps

1. Add a reusable `_run_metrics_for_context(...)` helper.
2. Feed the metric projection into detail, summary, audit, and replay packet builders.
3. Extend tests to validate presence and shape of the new metrics.

## Test Plan

- `python -m pytest tests/test_execution_loop.py -q`
- `python -m pytest tests/test_cli.py tests/test_api.py -q`
- later `python -m pytest -q`

## Risks And Rollback

- Main risk: metric calculations disagree across surfaces.
- Roll back by keeping one shared metric builder and projecting it unchanged everywhere else.

## Completion Evidence

- Actual modified files:
  - `packages/core_domain/service_projection.py`
  - `packages/core_domain/services.py`
  - `tests/test_execution_loop.py`
  - `tests/test_cli.py`
  - `tests/test_api.py`
- Validation:
  - targeted projection tests passed
  - later full `python -m pytest -q` passed
- Implementation note:
  - the final implementation stayed inside service/projection surfaces and did not require a dedicated TUI/dashboard file change
