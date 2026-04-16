# P3-T02 — Execute / Cancel Guards And UoW

## Basic Info

- Task ID: `P3-T02`
- Phase: `M1 Phase 3`
- Status: `verified`
- Depends On: `P3-T01`

## Goal

让 `execute_run()` 退化为兼容层，并为 `cancel_run()` 增加状态守卫、幂等和事务边界。

## Output

- execute compatibility alias
- cancel state guard
- idempotent cancel
