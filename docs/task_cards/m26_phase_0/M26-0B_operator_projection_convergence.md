# M26-0B Operator Projection Convergence

Status: completed

## Goal

Improve operator read models so capability descriptors, health, plan graphs, and external session refs are easier to inspect together.

## Acceptance Criteria

- operator-facing read models expose the new capability/session/graph data consistently
- CLI/API compatibility remains backward compatible

## Result

- converged `operator_projection` across status detail, inspection, audit report, replay packet, mutation report, operator rows, operator view, and dashboard focus state
- added policy-aware session projection and capability-health summaries without breaking existing payload keys
