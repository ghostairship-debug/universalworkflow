# M9-2B - Durable Diagnostics And Reconciliation Checks

- Task ID: `M9-2B`
- Phase: `M9 Phase 2 - Durable Recovery Lineage And Reconciliation`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9-2A`

## Goal

- Add durable-specific diagnostics and reconciliation signals to inspection, status, and audit surfaces.
- Make missing or inconsistent durable linkage actionable.

## Out Of Scope

- durable alert automation
- non-durable reconciliation redesign
- external monitoring integrations

## Read Set

- `packages/core_domain/services.py`
- `packages/core_domain/service_projection.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`

## Write Set

- Allowed:
  - `packages/core_domain/services.py`
  - `packages/core_domain/service_projection.py`
  - `tests/test_execution_loop.py`
  - `tests/test_api.py`
- Avoid:
  - governance reports
  - seed files

## Interfaces And Data Changes

- inspection/status-detail/audit surfaces expose:
  - `durable_lineage`
  - durable reconciliation problems
  - durable transition counts and checkpoint counts through run metrics

## Invariants

- diagnostics must stay read-only
- durable inconsistency detection must not mutate stored data
- existing inspection fields must remain available

## Implementation Steps

1. Add durable-lineage inspection checks in service inspection helpers.
2. Project durable lineage and related metrics through service projection.
3. Extend tests to cover missing lineage, ref mismatch, and history-empty conditions.

## Test Plan

- `python -m pytest tests/test_execution_loop.py -q`
- `python -m pytest tests/test_api.py -q`
- later `python -m pytest -q`

## Risks And Rollback

- Main risk: false-positive durable warnings create noisy operator diagnostics.
- Roll back by reducing checks to lineage-presence and ref-match assertions until the projection stabilizes.

## Completion Evidence

- Actual modified files:
  - `packages/core_domain/services.py`
  - `packages/core_domain/service_projection.py`
  - `tests/test_execution_loop.py`
  - `tests/test_api.py`
- Validation:
  - targeted inspection/audit tests passed
  - later full `python -m pytest -q` passed
- Implementation note:
  - durable transition counts now feed both inspection surfaces and the replay/metrics baseline
