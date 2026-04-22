# M32-0B Interaction Plane Contracts

Status: completed

## Goal

Introduce the minimum interaction-plane object model and service seam so that intent capture, clarification, preview, and launch become first-class platform objects.

## Acceptance

- add `IntentSession`
- add `IntentPacket`
- add `ClarificationState`
- add `PlanDraft`
- add `LaunchDecision`
- add `FollowupRequest`
- add a minimum interaction service facade
- keep interaction state separate from run/execution truth
- provide minimum CLI/API coverage for intent session, preview, launch decision, and follow-up

## Result

- landed `IntentSession`, `IntentPacket`, `ClarificationState`, `PlanDraft`, `LaunchDecision`, and `FollowupRequest`
- added the minimum interaction service in `packages/core_domain/service_interaction.py`
- wired interaction surfaces through CLI, API, and service layers without replacing run/execution truth
- shipped interaction-backed preview and launch flow on top of existing planning/policy/goal-packet surfaces
