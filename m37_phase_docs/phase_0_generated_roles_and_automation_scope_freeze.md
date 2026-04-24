# M37 Phase 0: Generated Roles And Automation Scope Freeze

Status: completed
Opened: 2026-04-24
Closed: 2026-04-24
Baseline: accepted `M36`

## Purpose

Open `M37` honestly by freezing a bounded generated-role and automation shape before deeper implementation.

## Scope

This phase includes:

- session-scoped generated profiles only
- bounded watchdog/controller evaluation only
- explicit preservation of review-gated high-risk actions

This phase does not include:

- unbounded autonomous multi-agent execution
- background job schedulers
- replacing the operator review gate

## Outcome

`M37 Phase 0` is complete.

The frozen line is:

- generated roles are implemented as additive generated profiles scoped to existing sessions and runs
- watchdogs evaluate bounded control-plane conditions and only auto-apply low-risk closeout bookkeeping
- high-risk actions remain review-gated and visible
