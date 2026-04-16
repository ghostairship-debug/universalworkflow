# P3-T03 — Resume API And CLI Surface

## Basic Info

- Task ID: `P3-T03`
- Phase: `M1 Phase 3`
- Status: `verified`
- Depends On: `P3-T01`, `P3-T02`

## Goal

把 `resume` 暴露到 operator surface，同时保持旧执行路径兼容。

## Output

- `POST /runs/{run_id}/resume`
- `workflowctl run resume <run_id>`
