# M25 Beta Freeze Review

Status: completed
Closed: 2026-04-21
Milestones absorbed: `M21` through `M25`

## Summary

The repository has moved from a post-`M20` trust rebaseline into a beta-shaped control plane for selective ecosystem expansion and controlled autonomy.

## What Landed

- `M21`
  - explicit migration operations through `workflowctl db migrate` and `workflowctl db migration-status`
  - internal `ResultEnvelope v1` projected through evidence, audit, and mutation reports
  - canonical rebaseline evidence through `infra/scripts/m21_rebaseline_report.py`
  - compile/recompile prepared-run persistence deduplicated in `service_lifecycle`
- `M22`
  - formal `CapabilityDescriptor` and `CapabilityHealth` read models
  - unified descriptor and health surfaces in CLI/API
- `M23`
  - sessionful external-agent lane via `opencode_session`
  - session refs projected into trace context and `ResultEnvelope`
- `M24`
  - `OrchestrationPlanGraph` and node contracts
  - compile-time graph planning persisted into run state and replay surfaces
- `M25`
  - natural-language `launch` / plan-graph surfaces in CLI/API
  - single-goal entry can now recommend a preset, materialize a plan graph, create a run, compile, and optionally execute

## Verified Highlights

- targeted regression coverage for capability descriptors, plan-graph surfaces, sessionful external-agent projections, mutation reports, and existing project-delivery flows
- `M21` rebaseline report proves canonical demo coverage for `feature_delivery`, `research_spike_reviewable`, `guarded_delivery`, and `project_delivery`

## Deferred

- capability policy enforcement as a first-class gate rather than a read-only preview surface
- deeper operator UI convergence for descriptor/plan/session visibility
- broader hosted provider breadth and multimodal expansion

## Next Active Work

Open `M26 Phase 0 - Post-M25 Policy Control And Operator Convergence Freeze`.
