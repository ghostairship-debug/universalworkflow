# M9-3B - Governance Alerts And CLI/API Surfaces

- Task ID: `M9-3B`
- Phase: `M9 Phase 3 - Governance Metrics And Alerting`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9-3A`

## Goal

- Add governance alerts that distinguish blocking vs degraded conditions.
- Expose the alert report through CLI, API, and release-readiness integration.

## Out Of Scope

- external notification systems
- cron/heartbeat automation
- non-governance alert types

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
  - persistence or scheduling subsystems
  - unrelated docs

## Interfaces And Data Changes

- add `build_governance_alert_report(...)`
- add `workflowctl governance alerts`
- add `GET /governance/alerts`
- update release-readiness to consume governance metrics plus alerts as gates

## Invariants

- alerts must derive from current metrics/debt state, not hand-maintained flags
- alert generation stays deterministic and local
- no background automation is introduced in this phase

## Implementation Steps

1. Build alert classification on top of governance metrics and debt state.
2. Wire alert outputs through CLI and API.
3. Fold alert/metric awareness into release-readiness gates.
4. Add regression tests.

## Test Plan

- `python -m pytest tests/test_governance.py -q`
- `python -m pytest tests/test_cli.py tests/test_api.py -q`
- later `python -m pytest -q`

## Risks And Rollback

- Main risk: alert severity becomes noisy or inconsistent with release-readiness.
- Roll back by centralizing gate interpretation in governance builders and projecting it unchanged to CLI/API.

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
  - the final alerting shape remained report-style and local; no external dashboard or automation runtime was added
