# Post-M10 Integrated Technical Roadmap

## Role

This document is the current synthesis for the repository's **post-`M10` technical route**.

It combines:

- the original control-plane-first direction from [universal_agentic_workflow_os_M8_phase_plan_v1_0.md](../../universal_agentic_workflow_os_M8_phase_plan_v1_0.md)
- the new root-level assessment in [Current_Version_Evaluation_and_Roadmap.md](../../Current_Version_Evaluation_and_Roadmap.md)
- the historical evaluation context in [M8_Phase_Plan_Evaluation.md](../../M8_Phase_Plan_Evaluation.md) and [M8_Strategic_Evaluation_Claude_Opus.md](../../M8_Strategic_Evaluation_Claude_Opus.md)
- the official shipped baseline in [m10-freeze-review.md](./m10-freeze-review.md), [../tech-debt-registry.md](../tech-debt-registry.md), and [../current_development_workflow.md](../current_development_workflow.md)

It does **not** replace the freeze review.
It explains what the best next route is, given the repository that actually exists today.

## Baseline

Validated baseline date: `2026-04-20`

Current confirmed repository shape:

- `M10` is complete
- the repository is a **local-first control plane**
- SQLite remains the canonical persistence layer
- claim / worker-lease / ownership topology / local batch-barrier semantics are shipped
- agent lane, MCP source, external trace export, and durable pilot still exist as **opt-in** external lanes
- the operator surface is still CLI/API-first plus a **read-mostly TUI**, not a full web console
- the only official open debt is `TD-019`: true external worker pools and multi-node scheduling are not yet productized

## Integrated Judgment

The three main inputs are more aligned than they first appear.

### 1. The original `M8` route was fundamentally correct

The original master plan did **not** aim to turn the repository into a generic agent platform as early as possible.
It aimed to make the repository a stable workflow control plane that:

- borrows mature agent/runtime/tooling substrate where useful
- keeps lifecycle, review, governance, projections, and release gates inside the repository
- preserves a local-first baseline even when every external flag is off

That remains the right architectural center of gravity.

### 2. The new root evaluation is also directionally correct

The new root evaluation correctly identifies that the best near-term target is **Level B: Local + External Enhance**, not immediate distributed-runtime completion.

It also correctly calls out three post-`M10` realities:

- `OrchestratorService` remains a structural bottleneck even after earlier extraction work
- `repositories.py` is still too centralized for the next expansion step
- external lanes exist, but their **real end-to-end verification depth is still shallow**

Those are not side observations.
They directly determine whether `M11+` can be developed safely.

### 3. The official post-`M10` truth still matters

The repository has not approved an open-ended platform expansion.
The official next step is still:

- `M11 Phase 0 - Post-M10 Rebaseline And Scope Freeze`

And the only currently recorded blocking debt is:

- `TD-019` - external worker pools and multi-node scheduling are not yet productized

So the next route must stay grounded in that official gate.

## Synthesis Result

The best route from here is **two-layered**:

### Near-term official target

Use `M11-M13` to finish a **real, productized Level B**:

- local-first control plane remains canonical
- external execution lanes become genuinely usable and testable
- external worker semantics stop being purely deferred theory
- service boundaries are made safe enough for the next expansion step

### Medium-term full-platform target

Use `M14-M15` to move from Level B into the user's intended end-state:

- formal multi-agent role orchestration
- full operator web UI
- productized configuration and deployment story
- hosted/distributed readiness beyond the local-first baseline

This keeps the original path intact while making the missing late-stage work explicit instead of leaving it implicit.

## What This Means For Scope

### Not rejected, only deferred

The following items should be treated as **deferred**, not permanently excluded:

- generic multi-agent role-system modeling
- full operator web UI
- broader hosted/distributed productization

The earlier wording that placed some of these outside an opening slice was useful for scope discipline, but should not be read as final product rejection.

### What must stay true

The following principles should continue to hold:

- repository state stays the public product truth
- external runtime refs remain subordinate to repository transitions
- new external breadth must stay opt-in until it is proven
- no milestone should widen `TaskKind` just to express tool or role differences
- UI should not get ahead of runtime semantics
- role modeling should not get ahead of ownership, lease, and scheduling semantics

## Recommended Milestone Route

## `M11` - External Execution Substrate And Integration Hardening

### Goal

Turn the repository from a local-first runtime with pilot external lanes into a local-first runtime with a **credible external execution substrate**.

### Why this is the right next milestone

`M11` has to start with `TD-019`, because that is the official open debt.
But it should not solve `TD-019` in isolation.
If the repository adds external worker vocabulary without also fixing service boundaries and proving real lane depth, it will widen complexity faster than it raises confidence.

### Must complete

- `M11 Phase 0` rebaseline and scope freeze
- split `TD-019` into payable slices:
  - external worker profile and routing boundary
  - lease renewal / ownership semantics outside the purely local path
  - multi-node scheduler boundary and non-goals
- continue service decomposition:
  - shrink the `OrchestratorService` facade pressure
  - split repository concerns by domain instead of keeping them in one oversized file
- run one real borrowed-agent golden path end to end on a supported preset
- harden one real local stdio MCP golden path end to end
- keep external execution opt-in while proving fallback, disable-path, and recovery behavior

### Should not expand into

- generic role-system modeling
- full web UI
- broad connector proliferation
- making remote scheduling the default path

### Exit shape

At `M11` close, the repository should be able to say:

- external worker semantics now have a supported boundary
- agent lane and MCP lane are real, not just structural placeholders
- the codebase is less bottlenecked around one orchestration facade

## `M12` - Durable, Observability, And Configuration Productization

### Goal

Take the external lanes that became real in `M11` and make them **operationally trustworthy**.

### Must complete

- durable pilot end-to-end validation on one narrow, review-heavy path
- pause / resume / interrupt / reconciliation semantics proven against repository truth
- Langfuse-backed external trace path hardened as the first real sink
- sink-down / trace-failure isolation verified
- introduce a real config layer:
  - config file support
  - env override policy
  - documented operator setup path
- improve quick-start, demo, install, and operator guidance so external lanes are actually usable

### Should not expand into

- multiple observability vendors at once
- large hosted-control-plane claims
- UI-first work that outruns the operator/runtime contract

### Exit shape

At `M12` close, the repository should be able to say:

- external lanes are not only present, but operable
- durable and observability paths are real and bounded
- configuration no longer depends on scattered environment variables alone

## `M13` - Formal Multi-Agent Orchestration Baseline

### Goal

Enter the multi-agent stage only after external execution semantics are stable enough to support it honestly.

### Must complete

- formal role contracts for a minimal role set such as:
  - planner
  - coder
  - reviewer
  - researcher
  - operator
- task handoff envelopes and artifact contracts
- role-aware review, escalation, and retry semantics
- conflict and ownership rules for concurrent work
- orchestration projections that explain multi-agent behavior without changing repository truth ownership

### Why it belongs here, not earlier

Before `M11-M12`, role modeling would mostly be naming without stable execution semantics underneath it.
After `M11-M12`, the repository can define roles against real ownership, claim, lease, and external-lane behavior instead of guessing.

## `M14` - Full Operator Web UI And Human Control Surface

### Goal

Move from a read-mostly TUI to a real operator interface once the runtime semantics are sufficiently stable.

### Must complete

- web dashboard for runs, queues, alerts, and focus views
- human review console
- replay / timeline / ownership inspection surfaces
- configuration and environment diagnostics
- operator intervention flows that align with CLI/API semantics instead of inventing a separate runtime

### Should not do

- replace CLI/API as the canonical surface
- move product truth out of repository-owned state

## `M15` - Productionization And Hosted Readiness

### Goal

Finish the platformization work required for a true "complete" edition.

### Must complete

- installation and bootstrap simplification
- secure configuration and secret-handling model
- upgrade / migration / versioning discipline
- scale and performance baselines
- distributed/hosted hardening beyond the local-first operator baseline
- release packaging and operational documentation

## Completion Model

From the current `M10` baseline, the repository is best understood like this:

- **already strong** at local-first workflow runtime foundations
- **not yet complete** as a fully productized multi-agent development platform

The most realistic interpretation is:

- `M11-M13` complete the **best possible near-term product** without violating the original architecture
- `M14-M15` are what likely turn that product into the fuller platform the user ultimately wants

In other words:

- original path logic: still correct
- Opus Level-B emphasis: correct
- long-range completion estimate: likely still **4 to 5 more milestones** from the current `M10` baseline if the target is full multi-agent orchestration + full external ecosystem + full UI + full productization

## Immediate Next Actions

Before any `M11` implementation breadth starts, the repository should do these three things in `M11 Phase 0`:

1. Freeze this milestone's product target explicitly:
   - `M11-M13` target = Level B complete
   - `M14-M15` target = full-platform expansion
2. Split `TD-019` into concrete payable slices instead of carrying it as one oversized debt label
3. Freeze the order inside `M11`:
   - external execution boundary first
   - service decomposition second
   - real agent/MCP end-to-end validation third

## One-Line Route

> The optimal route after `M10` is to keep the repository centered on a local-first control plane, spend `M11-M13` making external execution lanes and ownership semantics real and maintainable, and only then spend `M14-M15` on formal multi-agent orchestration, full UI, and final productization.
