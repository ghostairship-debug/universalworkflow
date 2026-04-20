# Post-M13 Integrated Technical Roadmap

## Role

This document is the current synthesis for the repository's **post-`M13` technical route**.

It combines:

- the original control-plane-first direction from [universal_agentic_workflow_os_M8_phase_plan_v1_0.md](../../universal_agentic_workflow_os_M8_phase_plan_v1_0.md)
- the root-level assessment in [Current_Version_Evaluation_and_Roadmap.md](../../Current_Version_Evaluation_and_Roadmap.md)
- the historical evaluation context in [M8_Phase_Plan_Evaluation.md](../../M8_Phase_Plan_Evaluation.md) and [M8_Strategic_Evaluation_Claude_Opus.md](../../M8_Strategic_Evaluation_Claude_Opus.md)
- the official shipped baseline in [m13-freeze-review.md](./m13-freeze-review.md), [../tech-debt-registry.md](../tech-debt-registry.md), and [../current_development_workflow.md](../current_development_workflow.md)

It does **not** replace the freeze review.
It explains what the best next route is, given the repository that actually exists today.

## Baseline

Validated baseline date: `2026-04-20`

Current confirmed repository shape:

- `M13` is complete
- the repository remains a **local-first control plane**
- SQLite remains the canonical persistence layer
- claim / worker-lease / batch-barrier semantics are shipped
- workflow configuration is now unified through `workflow.toml` plus env and explicit override precedence
- external worker pools have a real contract boundary, but hosted/distributed scheduling is still deferred
- durable pilot and trace-export paths are real enough to operate and diagnose
- the repository now ships a formal `project_delivery` orchestration baseline
- the operator surface is still CLI/API-first plus a **read-mostly TUI**, not a full web console

Current active debt:

- `TD-019` - hosted remote pools and multi-node scheduling are still not productized beyond the local-first/loopback baseline
- `TD-020` - the full operator web UI and human control surface are still missing beyond CLI/API and the read-mostly TUI

## Integrated Judgment

The post-`M10` roadmap held up well.

### 1. The original architectural center was still correct

The repository should still be treated as a workflow control plane that:

- owns lifecycle truth in the repository
- borrows external substrate where useful
- keeps review, governance, projections, and release gates inside the repository
- remains useful when every external flag is off

`M11-M13` strengthened that architecture instead of replacing it.

### 2. The "Level B first" judgment was also correct

The right move after `M10` was not immediate hosted-platform sprawl.
It was to finish a credible intermediate product:

- external execution boundary
- operable config / durable / trace paths
- formal orchestration baseline

That intermediate product now exists.

### 3. The remaining work is now much clearer

After `M13`, the biggest remaining gaps are no longer "Does the runtime have a structure?"
They are:

- human control-surface quality
- orchestration visibility and intervention UX
- hosted/distributed productization

That means the route can narrow rather than widen.

## Recommended Milestone Route

## `M14` - Full Operator Web UI And Human Control Surface

### Goal

Move from a read-mostly TUI to a real operator-facing control surface on top of the stable post-`M13` runtime.

### Must complete

- web dashboard for runs, orchestration state, queues, alerts, and focus views
- human review console aligned with the existing review-policy model
- replay / timeline / orchestration / ownership inspection surfaces
- configuration diagnostics and feature-flag visibility
- operator intervention flows that reuse CLI/API semantics rather than inventing a second runtime

### Should not do

- replace CLI/API as the canonical automation surface
- move product truth out of repository-owned state
- claim hosted/distributed completion as part of UI work

## `M15` - Hosted And Distributed Productization

### Goal

Finish the external-worker and deployment work required for a fuller platform edition.

### Must complete

- hosted remote worker pools
- distributed lease renewal and scheduler hardening
- secure configuration / secret-handling model
- installation and bootstrap simplification for broader operators
- upgrade / migration / release packaging discipline
- scale and performance baselines

### Should stay true

- repository state remains public product truth
- external runtime state stays subordinate to repository transitions
- multi-node behavior must be introduced through explicit contracts, not implicit side effects

## Completion Model

From the current `M13` baseline, the repository is best understood like this:

- **already strong** at local-first workflow runtime, governance, external-lane integration, and orchestration baseline
- **not yet complete** as a fully productized multi-agent development platform

The most realistic interpretation is:

- `M14` completes the human operator product surface
- `M15` completes hosted/distributed productization

## Immediate Next Actions

Before any `M14` implementation breadth starts, the repository should do these three things in `M14 Phase 0`:

1. freeze the UI/human-control scope explicitly against the post-`M13` orchestration baseline
2. decide which orchestration, review, and governance surfaces are authoritative in the web console
3. keep `TD-019` deferred from UI work unless the rebaseline explicitly reorders milestones

## One-Line Route

> The optimal route after `M13` is to keep the repository centered on a local-first control plane, spend `M14` turning the shipped orchestration/runtime surfaces into a full operator web UI, and spend `M15` finishing hosted/distributed productization for external workers and deployment readiness.
