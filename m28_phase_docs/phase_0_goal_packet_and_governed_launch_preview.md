# M28 Phase 0 - Goal Packet And Governed Launch Preview

Status: completed
Opened: 2026-04-21
Milestone: M28

## Purpose

Extend natural-language launch so operators can inspect a single goal packet before or alongside launch, rather than bouncing between suggestions, plan graphs, and policy previews.

## Scope

- add a goal packet preview surface
- include matched capability descriptors and health in the packet
- project the packet through launch payloads

## Outcome

- `preview_goal_packet()` landed
- `workflowctl run goal-packet` and `POST /runs/goal-packet` landed
- `launch_goal()` now carries the goal packet alongside plan graph and capability policy preview
