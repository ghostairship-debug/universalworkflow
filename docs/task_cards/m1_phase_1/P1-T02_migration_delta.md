# P1-T02 — Migration Delta

## Basic Info

- Task ID: `P1-T02`
- Phase: `M1 Phase 1`
- Status: `verified`
- Depends On: `P1-T01`

## Goal

新增 M1 所需的持久化表和索引，为 `HandoffLite`、`RuntimeStateRef` 与后续状态查询提供底座。

## Read Set

- `infra/migrations/001_init.sql`
- `packages/contracts/models.py`
- `packages/contracts/runtime.py`
- `tests/test_repositories.py`

## Write Set

- 新增 `infra/migrations/002_m1_runtime_state_and_handoffs.sql`
- `tests/test_repositories.py`

## Tests

- migration repeatability
- fresh db apply
- new table round-trip

## Output

- `handoff_lite`
- `runtime_state_refs`
- 对应索引和重复迁移保障
