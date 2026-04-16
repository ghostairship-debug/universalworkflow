# P3-T01 — Resume Service And State Progression

## Basic Info

- Task ID: `P3-T01`
- Phase: `M1 Phase 3`
- Status: `verified`
- Depends On: `Phase 2 gate`

## Goal

让 `resume_run()` 从 `prepared` 读取 `RuntimeStateRef`，推进 runtime，并在 timeline 中写入 `runtime_resumed`。

## Output

- `resume_run()`
- state ref progression
- `runtime_resumed` event
