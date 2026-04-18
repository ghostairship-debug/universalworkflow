# R0-T01 - Reconcile Catalog And Query Helpers

## Basic Info

- Task ID: `R0-T01`
- Phase: `M2 Phase 0`
- Status: `completed`
- Depends On: `Phase 0 entry`

## Goal

Turn the current dry-run inspection into a repair-aware catalog by adding explicit repairability metadata and the runtime-state query helpers needed by later repair actions.

## Read Set

- `packages/core_domain/services.py`
- `packages/core_domain/repositories.py`
- `packages/contracts/runtime.py`
- `tests/test_execution_loop.py`
- `tests/test_repositories.py`
- `docs/legacy_project_reference_uplift_plan.md`

## Write Set

- `packages/core_domain/services.py`
- `packages/core_domain/repositories.py`
- `tests/test_execution_loop.py`
- `tests/test_repositories.py`

## Invariants

- inspection remains side-effect free
- query helpers stay run-centric
- no project/phase runtime assumptions enter the current repo

## Implementation Steps

1. Add repository helpers for latest, live, and terminal runtime state refs.
2. Extend inspection problems with `repairable` and `repair_action` metadata.
3. Keep manual-only problems explicitly non-repairable.
4. Add tests for query helpers and repair-aware inspection output.

## Test Plan

- repository helper tests
- inspection metadata tests
- existing dry-run side-effect tests still pass

## Outcome

- runtime-state repositories now expose latest/live/terminal queries
- inspection problems now distinguish repairable vs manual-only cases
- dry-run inspection remains side-effect free
