# M26-0A Capability Policy Preview And Gating Baseline

Status: completed

## Goal

Add an explicit capability-policy preview so operators can understand which capability descriptors and execution lanes a goal would use before execution expands further.

## Acceptance Criteria

- a policy preview surface exists for goal/preset planning
- the preview names sessionful lanes, review gates, and notable side-effect levels
- the preview is additive and does not block current execution paths

## Result

- added `workflowctl run policy-preview` and `POST /runs/policy-preview`
- added run-level `capability_policy_preview` projection for status/detail, audit, replay, and operator views
- repaired compile-time adapter override propagation so stored plan graphs and policy previews reflect the actual execution lane
