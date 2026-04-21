# M26 Policy Control Freeze Review

Date: 2026-04-21
Status: accepted

## Summary

`M26` converted capability selection from an implicit compile/runtime side effect into an explicit operator-readable surface. The repository now exposes policy preview, plan-graph-backed lane reasoning, and converged operator projections across CLI, API, audit, replay, and dashboard contexts.

## Landed

- goal and run level capability policy preview surfaces
- converged `operator_projection` read models with session refs and capability-health summaries
- adapter-override propagation fix so stored plan graphs match actual compiled execution lanes

## Validation

- targeted CLI/API/execution-loop regressions passed for policy preview and operator projection paths

## Entry Gate To M27-M30

The next bounded sequence should stay on operator convergence instead of jumping to new provider breadth:

1. standardize a compact operator packet
2. standardize a goal packet for natural-language launch
3. converge dashboard focus state onto the same packet family
4. freeze at `M30` before reopening breadth
