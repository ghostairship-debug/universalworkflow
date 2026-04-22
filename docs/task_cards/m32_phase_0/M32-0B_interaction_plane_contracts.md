# M32-0B Interaction Plane Contracts

Status: pending

## Goal

Introduce the minimum interaction-plane object model and service seam so that intent capture, clarification, preview, and launch become first-class platform objects.

## Acceptance

- add `IntentSession`
- add `IntentPacket`
- add `ClarificationState`
- add `PlanDraft`
- add `LaunchDecision`
- add `FollowupRequest`
- add a minimum interaction service façade
- keep interaction state separate from run/execution truth
- provide minimum CLI/API coverage for intent session, preview, launch decision, and follow-up
