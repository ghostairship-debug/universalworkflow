# M30 Operator Control Freeze Review

Date: 2026-04-21
Status: accepted

## Summary

`M26-M30` completed the operator-control consolidation line. The repository now has explicit policy preview, a compact operator packet, a goal packet for governed natural-language launch, and dashboard focus convergence onto the same packet family.

## What Is Now True

- capability and lane selection are operator-readable before execution expands
- run-level operator state can be consumed through one compact packet instead of multiple ad hoc payloads
- natural-language launch has a governed preview packet containing plan graph, policy preview, matched descriptors, and matched health
- dashboard focus state and operator views are aligned on the same packet family
- the built-in Web UI and TUI are still operator-facing consoles, not chat-style natural-language workbenches

## Validation

- `python -m pytest tests/test_cli.py tests/test_api.py tests/test_execution_loop.py -q -k "policy_preview or plan_graph_and_launch or sessionful_external_agent_lane_projects_session_refs or operator_projections_include_policy_preview_and_session_refs"` passed
- `python -m pytest tests/test_cli.py tests/test_api.py tests/test_execution_loop.py -q -k "plan_graph_and_launch or operator_projections_include_policy_preview_and_session_refs or dashboard_snapshot_projects_recent_runs_and_focus_detail"` passed

## Deferred To M31+

- enforced policy gating instead of preview-only guidance
- automation and long-running background control loops
- broader hosted-provider and multimodal expansion
- a front-end natural-language chat/workbench surface on top of the existing goal-launch backend
- self-upgrade and deeper autonomy work
