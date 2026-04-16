# P1-T03 — Repository And Connection Injection

## Basic Info

- Task ID: `P1-T03`
- Phase: `M1 Phase 1`
- Status: `verified`
- Depends On: `P1-T02`

## Goal

让 repository 写操作支持外部 connection 注入，并新增 handoff / state ref repository，为 Phase 3 的 UoW 铺路。

## Read Set

- `packages/core_domain/db.py`
- `packages/core_domain/repositories.py`
- `tests/test_repositories.py`

## Write Set

- `packages/core_domain/db.py`
- `packages/core_domain/repositories.py`
- `tests/test_repositories.py`

## Tests

- repository round-trip
- injected connection path
- handoff / state ref get/list/update

## Output

- connection injection capable repositories
- `HandoffRepository`
- `RuntimeStateRepository`
