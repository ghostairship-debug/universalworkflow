# M9-3A - Governance Metrics Projection

- Task ID: `M9-3A`
- Phase: `M9 Phase 3 - Governance Metrics And Alerting`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9 Phase 2 complete`

## Goal

- Add quantitative governance metrics over debt, validation, policy/runtime coverage, and runtime inventory.
- Expose the metrics through service-adjacent governance builders plus CLI/API surfaces.

## Out Of Scope

- alert classification logic
- hosted dashboards
- execution-semantics changes

## Read Set

- `packages/core_domain/governance.py`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`
- `tests/test_governance.py`
- `tests/test_cli.py`
- `tests/test_api.py`

## Write Set

- Allowed:
  - `packages/core_domain/governance.py`
  - `apps/operator_cli/main.py`
  - `apps/orchestrator_api/main.py`
  - `tests/test_governance.py`
  - `tests/test_cli.py`
  - `tests/test_api.py`
- Avoid:
  - debt registry closeout
  - non-governance runtime code

## Interfaces And Data Changes

- add `build_governance_metrics_report(...)`
- add `workflowctl governance metrics`
- add `GET /governance/metrics`
- metrics must quantify current repo/runtime state instead of only narrating it

## Invariants

- governance metrics remain local-repo/local-DB derived
- release-readiness continues to build on governance primitives rather than forking them
- existing governance outputs remain backward compatible

## Implementation Steps

1. Add quantitative inventory builders in `governance.py`.
2. Wire the metrics report into CLI and API.
3. Extend governance, CLI, and API tests.
4. Reuse the metrics in later release-readiness composition.

## Test Plan

- `python -m pytest tests/test_governance.py -q`
- `python -m pytest tests/test_cli.py tests/test_api.py -q`
- later `python -m pytest -q`

## Risks And Rollback

- Main risk: governance metrics become disconnected from actual runtime inventory.
- Roll back by computing metrics directly from the current DB/seed state in one builder path.

## Completion Evidence

- Actual modified files:
  - `packages/core_domain/governance.py`
  - `apps/operator_cli/main.py`
  - `apps/orchestrator_api/main.py`
  - `tests/test_governance.py`
  - `tests/test_cli.py`
  - `tests/test_api.py`
- Validation:
  - targeted governance, CLI, and API tests passed
  - later full `python -m pytest -q` passed
- Implementation note:
  - release-readiness later consumed these metrics instead of maintaining a separate inventory layer
