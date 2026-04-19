# M9-2A - Durable Lineage History Persistence

- Task ID: `M9-2A`
- Phase: `M9 Phase 2 - Durable Recovery Lineage And Reconciliation`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `M9 Phase 1 complete`

## Goal

- Persist structured durable lineage/history through start, resume, awaiting-review, terminal, and cancel transitions.
- Move the durable pilot from "latest refs only" to explicit transition history.

## Out Of Scope

- promoting the durable lane to default
- remote checkpoint stores
- governance surfaces

## Read Set

- `packages/core_domain/services.py`
- `packages/core_domain/service_lifecycle.py`
- `tests/test_execution_loop.py`

## Write Set

- Allowed:
  - `packages/core_domain/services.py`
  - `packages/core_domain/service_lifecycle.py`
  - `tests/test_execution_loop.py`
- Avoid:
  - seed files
  - governance code
  - non-durable execution semantics

## Interfaces And Data Changes

- runtime state payloads now carry structured durable lineage
- durable transitions must record reasons such as `start`, `resume`, `awaiting_review`, `terminal`, and `cancelled`

## Invariants

- durable remains opt-in
- non-durable runs must keep their existing behavior
- lineage additions must not require a schema migration

## Implementation Steps

1. Add helpers to read/write durable lineage from runtime state refs.
2. Initialize lineage when durable execution starts.
3. Update lifecycle transitions to append durable transition records instead of overwriting refs only.
4. Add lifecycle tests covering durable history growth.

## Test Plan

- `python -m pytest tests/test_execution_loop.py -q`
- later `python -m pytest -q`

## Risks And Rollback

- Main risk: durable state payloads diverge between helper paths.
- Roll back by centralizing durable-lineage updates in shared helpers before touching more transitions.

## Completion Evidence

- Actual modified files:
  - `packages/core_domain/services.py`
  - `packages/core_domain/service_lifecycle.py`
  - `tests/test_execution_loop.py`
- Validation:
  - targeted durable lifecycle tests passed
  - later full `python -m pytest -q` passed
- Implementation note:
  - the final implementation did not require direct edits to `packages/runtime_langgraph/durable_pilot.py`
