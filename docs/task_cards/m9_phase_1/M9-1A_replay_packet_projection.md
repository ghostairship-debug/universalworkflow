# M9-1A - Replay Packet Projection

- Task ID: `M9-1A`
- Phase: `M9 Phase 1 - Replay Linkage And Metrics Baseline`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9 Phase 0 complete`

## Goal

- Add a replay-grade packet that projects timeline, state refs, attempts, ownership, reviews, task packets, and simulation context from existing persisted artifacts.
- Expose the packet through service, CLI, and API surfaces.

## Out Of Scope

- new persistence tables
- governance automation
- durable merge-policy redesign

## Read Set

- `packages/core_domain/service_projection.py`
- `packages/core_domain/services.py`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`
- `tests/test_execution_loop.py`
- `tests/test_cli.py`
- `tests/test_api.py`

## Write Set

- Allowed:
  - `packages/core_domain/service_projection.py`
  - `packages/core_domain/services.py`
  - `apps/operator_cli/main.py`
  - `apps/orchestrator_api/main.py`
  - `tests/test_execution_loop.py`
  - `tests/test_cli.py`
  - `tests/test_api.py`
- Avoid:
  - schema or migration files
  - governance code

## Interfaces And Data Changes

- add `get_run_replay_packet(run_id)`
- add `workflowctl run replay-packet`
- add `GET /runs/{run_id}/replay-packet`
- replay packet must reuse existing persisted run artifacts instead of inventing a parallel store

## Invariants

- keep SQLite as the only persistence layer
- keep the replay packet read-only
- avoid duplicating status-summary logic when the same context can be reused

## Implementation Steps

1. Build the packet in `service_projection` from existing projections and repositories.
2. Reuse summary/detail/inspection context where possible.
3. Expose the packet through CLI and API.
4. Add regression tests for service, CLI, and API.

## Test Plan

- `python -m pytest tests/test_execution_loop.py -q`
- `python -m pytest tests/test_cli.py tests/test_api.py -q`
- later `python -m pytest -q`

## Risks And Rollback

- Main risk: replay packet fields drift away from existing operator projections.
- Roll back by collapsing duplicated packet sections back onto already-tested projection helpers.

## Completion Evidence

- Actual modified files:
  - `packages/core_domain/service_projection.py`
  - `packages/core_domain/services.py`
  - `apps/operator_cli/main.py`
  - `apps/orchestrator_api/main.py`
  - `tests/test_execution_loop.py`
  - `tests/test_cli.py`
  - `tests/test_api.py`
- Validation:
  - targeted execution-loop, CLI, and API tests passed
  - later full `python -m pytest -q` passed
- Implementation note:
  - this card established the packet structure that later `M9-1B` enriched with first-class run metrics
