# M26 Phase 0 - Post-M25 Policy Control And Operator Convergence Freeze

Status: completed
Opened: 2026-04-21
Milestone: M26

## Purpose

Open the next bounded cycle after the `M25` beta freeze. This phase exists to turn newly landed capability descriptors, session lanes, and plan graphs into operator-governed surfaces before the repository expands provider breadth or automation depth.

## Inputs

- [docs/reviews/m25-beta-freeze-review.md](../docs/reviews/m25-beta-freeze-review.md)
- [docs/tech-debt-registry.md](../docs/tech-debt-registry.md)
- [docs/current_development_workflow.md](../docs/current_development_workflow.md)
- [NEXT_DEVELOPMENT_PLAN.md](../NEXT_DEVELOPMENT_PLAN.md)

## Scope

- add capability-policy preview and governance-oriented gating surfaces
- project descriptors, health, session refs, and plan graphs more clearly into operator-facing read models
- define the entry gate from `M26` into the broader `M27-M30` autonomy and ecosystem work

## Non-Goals

- multimodal execution
- large hosted-provider breadth
- autonomous background automation
- self-modifying upgrade loops

## Active Task Cards

- [M26-0A Capability Policy Preview And Gating Baseline](../docs/task_cards/m26_phase_0/M26-0A_capability_policy_preview_and_gating_baseline.md)
- [M26-0B Operator Projection Convergence](../docs/task_cards/m26_phase_0/M26-0B_operator_projection_convergence.md)
- [M26-0C Closeout And M27 Entry Gate](../docs/task_cards/m26_phase_0/M26-0C_closeout_and_m27_entry_gate.md)

## Exit Criteria

- capability policy preview exists as an explicit operator surface
- operator projections clearly expose capability descriptors, health, plan graphs, and session refs
- `M26` closeout states what remains for `M27-M30`

## Outcome

- explicit capability-policy preview landed for goal planning and run inspection
- operator-facing projections now expose policy mode, capability health, plan graphs, and external session refs together
- compile-time adapter overrides now round-trip into stored orchestration plan graphs, preventing lane drift between planning and execution

## Validation

- `python -m pytest tests/test_cli.py tests/test_api.py tests/test_execution_loop.py -q -k "policy_preview or plan_graph_and_launch or sessionful_external_agent_lane_projects_session_refs or operator_projections_include_policy_preview_and_session_refs"` passed
- `python -m pytest tests/test_cli.py tests/test_api.py tests/test_execution_loop.py -q -k "plan_graph_and_launch or operator_projections_include_policy_preview_and_session_refs or dashboard_snapshot_projects_recent_runs_and_focus_detail"` passed

## Closeout

See [docs/reviews/m26-policy-control-freeze-review.md](../docs/reviews/m26-policy-control-freeze-review.md).
