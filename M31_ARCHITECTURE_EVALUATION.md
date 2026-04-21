# M31 Architecture Evaluation

Date: 2026-04-21  
Status: Proposed next-phase evaluation  
Scope: whole-repo architecture, execution model, governance model, extensibility path, product-readiness path

---

## 1. Executive summary

`universalworkflow` is not a README-first prototype. It is already a real local-first agentic workflow kernel with a surprisingly mature control plane:

- compile / recompile / resume are first-class lifecycle operations
- review policies are modeled, persisted, and projected
- runtime claims, worker leases, snapshots, simulation records, replay packets, and audit reports are all part of the system model
- capability selection, tool projection, worker-pool dispatch, and scheduler-authority quorum slices already exist
- a minimal domain-pack model, bounded repo-mutation contract, and a baseline multi-role `project_delivery` orchestration are implemented
- API, CLI, TUI, and built-in web operator surfaces are already present
- the test suite is broad enough to support confidence that this is a real kernel, not a thin shell around one demo path

That said, the repository has reached a very specific inflection point:

> The control plane is now more mature than the product plane.

This is the central architectural fact that should govern the next phase.

The project is **not** primarily blocked by missing features. It is blocked by the need to turn a strong operator-centric kernel into a clean, extensible, user-facing and agent-facing platform architecture.

My bottom-line evaluation is:

1. `v1 core complete` is a credible description of the current kernel.
2. The repository is strong enough to justify continued investment.
3. It is **not yet ready** to jump directly into broad productization, heavy ecosystem expansion, or deep autonomy/self-upgrade.
4. The next phase should be a bounded **architecture-hardening and interface-refactor phase**, not a breadth-first feature expansion phase.

If this phase is handled correctly, the project can evolve into a genuinely differentiated "agentic workflow OS / engineering control plane". If it is skipped, the most likely failure mode is not technical collapse, but **progressive structural drag**: too many features, too much operator power, too little unified product boundary.

---

## 2. Evaluation scope and evidence base

This evaluation is based on both repository internals and current external ecosystem patterns.

### 2.1 Repository evidence reviewed

Primary repository evidence examined includes:

- `README.md`
- `docs/current_development_workflow.md`
- `docs/reviews/m20-freeze-review.md`
- `docs/reviews/m30-operator-control-freeze-review.md`
- `docs/tech-debt-registry.md`
- `pyproject.toml`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`
- `apps/orchestrator_api/web_ui.py`
- `apps/operator_tui/dashboard.py`
- `packages/core_domain/services.py`
- `packages/core_domain/service_lifecycle.py`
- `packages/core_domain/service_projection.py`
- `packages/core_domain/capability_plane.py`
- `packages/core_domain/external_workers.py`
- `packages/core_domain/scheduler_authority.py`
- `packages/core_domain/config.py`
- `packages/runtime_langgraph/gateway.py`
- `packages/runtime_langgraph/durable_pilot.py`
- `packages/worker_adapters/router.py`
- `infra/seeds/domain_packs.json`
- `infra/seeds/worker_pool_profiles.json`
- `infra/seeds/mcp_server_profiles.json`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_web_ui.py`

### 2.2 External ecosystem references consulted

I also cross-checked the current design against official materials for:

- LangGraph
- OpenAI Agents SDK
- AutoGen
- CrewAI
- Model Context Protocol (MCP)
- Temporal
- Prefect
- Trigger.dev

These references matter because the project is now beyond the stage where architecture can be judged only internally. The key question is no longer “does it run?” but “what kind of platform should this become, and what should it deliberately avoid becoming?”

---

## 3. What the repository already achieves

## 3.1 It already has a real kernel

The repository is best understood as a **service-centric modular monolith** with multiple operator surfaces.

It already includes:

- a persistent run lifecycle model
- explicit compiled/prepared/resumed/awaiting_review/completed/cancelled/repaired snapshots
- persisted runtime state refs and runtime attempts
- claim / lease ownership modeling
- review-policy branching in lifecycle control
- replay / audit / summary / inspection projections
- local execution, opencode execution, noop execution, sessionful execution, agent-lane execution, and external worker dispatch paths
- quorum-based scheduler-authority semantics for lease ownership and handoff lineage

This is not a toy. The kernel is already behaving like the inner control plane of an agent platform.

## 3.2 The control plane is unusually strong for this stage

Three aspects are already better than most early agent-workflow repos:

### A. State is explicit

The project persistently models:

- runtime states
- runtime attempts
- snapshots
- evidence
- review verdicts
- claims
- worker leases
- simulation records
- scheduler proposals / decisions / committed leases / handoff envelopes

This matters because it enables replayability, inspectability, repair, and eventually automation.

### B. Governance is modeled, not implied

Review policies are not comments in a README. They actually shape lifecycle transitions.

The system distinguishes:

- `auto_only`
- `optional`
- `recommended`
- `human_required`
- `mandatory`

and projects them into status detail, review state, operator packets, and audit output. This is a major asset for future productization.

### C. Observability is built into the domain model

The system does not treat observability as external logging only. It has internal products for:

- status detail
- run summary
- event inspection
- audit report
- replay packet
- operator packet
- operator view
- dashboard snapshot

That is a strong sign that the project is thinking like a control plane, not just like a task runner.

## 3.3 The repository already has a credible extensibility baseline

The following extensibility primitives already exist:

- capability descriptors and capability health
- tool projection manifests
- trust tiers
- MCP profile projection
- worker pool profiles
- default config resolution and feature-flagged incubation
- domain packs and skill export baseline

This is a meaningful base for a future plugin / extension / external capability architecture.

## 3.4 The repo-mutation path is not superficial

The bounded repo-mutation path is particularly important because it proves the system can already serve real engineering workflows, not just abstract reasoning loops.

Notable strengths:

- explicit mutation contract
- read/write set constraints
- bounded fix iterations
- test command integration
- patch-apply mode
- mutation reports
- orchestration propagation into `project_delivery`

This is a credible starting point for “arbitrary engineering development” as long as it is promoted from a special case into a first-class platform contract.

## 3.5 The test surface is broad and meaningful

The test corpus is deep enough to materially raise confidence.

It covers, among other things:

- lifecycle success and failure paths
- review-policy semantics
- simulation recording and policy triggers
- memory namespaces / candidate materialization / retrieval preview
- domain-pack resolution and validation
- capability source / MCP projection preview
- external worker pools
- durable pilot path
- sessionful external agent path
- multi-role orchestration
- repo mutation and bounded fix loops
- claim / worker lease lifecycle
- parallel batch barriers
- scheduler authority conflict / expiry / regrant paths
- API surface and web operator surface behavior
- inspection and repair actions
- snapshot history and budget projection

This breadth is a major reason the project deserves continued architectural investment.

---

## 4. Architectural reading of the current system

The present architecture can be summarized as:

> **A powerful, service-centered control plane with multiple access surfaces, plus several promising but still partial platform abstractions.**

The key architectural pattern is:

- one dominant public service facade (`OrchestratorService`)
- a set of extracted service modules / mixins underneath it
- multiple interfaces (CLI / FastAPI / Web UI / TUI) all terminating into that shared service layer
- typed contracts as the system language
- SQLite-backed local-first state and governance history

This is a valid architecture for getting from zero to a working core quickly. It has clearly worked.

However, it now creates the main strategic tension of the repo:

- it is excellent for integrating features quickly
- it is increasingly poor as the permanent boundary for product surfaces, external integrations, dynamic multi-agent orchestration, and future ecosystem growth

That is why the next phase must not be “keep adding more things to the same facade.”

---

## 5. What should be preserved

The next phase should **preserve** these properties rather than rewrite them away:

1. **Local-first truth model**  
   The project’s differentiation comes partly from local inspectability, local replay, and local control.

2. **Typed contract discipline**  
   A lot of future stability depends on continuing to treat packets, snapshots, verdicts, leases, and projections as explicit domain objects.

3. **Lifecycle explicitness**  
   `compile -> resume -> review -> terminalize` is a strong backbone.

4. **Governance as domain logic**  
   Review policies, audit products, and inspection/repair logic are not optional extras; they are core product assets.

5. **Operator-grade projections**  
   The existing projection model is strong and should be generalized, not discarded.

6. **Bounded repo mutation**  
   This is a real wedge into practical engineering workflows.

7. **Control-plane ownership model**  
   Claims, worker leases, scheduler leases, and handoff lineage are strong foundations for safe automation.

8. **Feature-flagged incubation**  
   The current flag model is useful while abstractions settle.

---

## 6. Core weaknesses and structural gaps

The repo’s problems are now mostly structural rather than purely functional.

## 6.1 `OrchestratorService` is still too dominant

The codebase already extracted several areas into mixins and companion services, but the effective public center of gravity is still the giant service facade.

Why this is now a problem:

- orchestration semantics, policy semantics, capability semantics, repair semantics, and product projection semantics remain too concentrated
- API / CLI / Web / TUI surfaces are all tightly coupled to the same façade contract
- future external SDKs, NL workbenches, autonomous controllers, and agent-facing APIs will all be tempted to depend on the same oversized surface

This does not mean the repo should split into microservices. It means the repo now needs **clear platform boundaries inside the monolith**.

Severity: **High**

## 6.2 The system is still operator-surface first, not product-surface first

The built-in web UI and TUI are explicitly operator surfaces, not chat-style workbenches.

This is fine for the current phase, but it means the system still lacks a canonical answer to:

- what is the primary end-user interaction model?
- what is the primary builder interaction model?
- what is the canonical session / conversation / plan-approval object?
- how should natural language interact with structured execution state over time?

Right now, the control plane can *support* these things, but it is not yet *shaped around* them.

Severity: **High**

## 6.3 Orchestration exists, but it is not yet a general orchestration engine

`project_delivery` proves that multi-role orchestration is possible, but it is still a baseline rather than a generalized orchestration substrate.

Current limitations:

- one visible canonical orchestration path is still privileged
- graph generation, role planning, barrier semantics, role-specific policy rules, reducers, and dynamic role injection are not yet first-class architecture objects
- orchestration is still too close to service logic and too far from a stable plan/graph DSL

The current system can orchestrate. It cannot yet claim to expose orchestration as a reusable platform abstraction.

Severity: **High**

## 6.4 Policy preview is ahead of policy enforcement

M30 added important visibility around plan graph and policy preview. That is good. But the repo’s own freeze note already identifies the gap: policy gating is not yet strong enough as an enforcement layer.

That means the system currently has a risk of becoming excellent at *showing* governance without being equally strong at *enforcing* governance at every relevant boundary.

Severity: **High**

## 6.5 Feature flags currently hide architectural incompleteness

The flags are useful, but they also indicate which areas are still incubation paths rather than hardened subsystems:

- agent lane
- MCP source
- durable pilot
- external trace export
- skill export
- external worker pools
- sessionful external agents

The risk is not that these are flagged. The risk is allowing too many of them to expand before the surrounding contracts stabilize.

Severity: **Medium-High**

## 6.6 Capability integration is promising but not yet unified enough

The project already has a real capability plane. However, its integration story is still spread across:

- worker adapters
- capability descriptors
- capability routes
- tool projection manifests
- MCP profiles
- worker pools
- runtime gateway
- sessionful external paths

These pieces are adjacent, but not yet unified into one canonical “capability invocation contract” that every human-facing, agent-facing, and system-facing integration can rely on.

Severity: **High**

## 6.7 Memory exists, but not yet as a complete product-facing memory architecture

The memory candidate/materialization flow is useful and thoughtful. But it is still closer to a kernel primitive than a complete interaction-memory architecture.

Missing pieces include:

- separation of conversation memory vs run memory vs artifact memory vs reusable project memory
- long-lived session semantics for natural-language supervision
- memory compaction / summarization / promotion policies
- memory access policy tied to agent role / capability trust / review level

Severity: **Medium**

## 6.8 The tech-debt registry currently under-describes next-stage debt

The open debt section is empty. That can be true if interpreted narrowly as “known pre-M30 structural debts on the mainline kernel.”

But it is misleading if interpreted as “no important structural debt remains.”

There is now a different class of debt:

- architecture transition debt
- product interface debt
- orchestration abstraction debt
- packaging / extension-model debt
- autonomous-controller debt

This should be recorded explicitly in the next phase.

Severity: **Medium-High**

---

## 7. External framework comparison and architectural implication

The best future path is **hybrid absorption**, not framework replacement.

## 7.1 LangGraph

Useful lessons:

- durable checkpointing
- interrupt/resume semantics
- graph/state-first execution model
- thread/checkpoint separation

Implication for this repo:

- LangGraph is a good **lane/runtime backend** and a useful reference model for durable agent execution.
- It should **not** replace the repo’s core kernel and governance model.

## 7.2 OpenAI Agents SDK

Useful lessons:

- clean distinction between code-orchestrated flow and model-driven orchestration
- handoffs vs agents-as-tools
- built-in tracing patterns
- explicit conversation/run orchestration guidance

Implication:

- very valuable as a reference for **interaction-plane and multi-agent collaboration design**
- not a substitute for the repo’s local-first kernel, governance, or scheduler-authority model

## 7.3 AutoGen

Useful lessons:

- async, event-driven, distributed agent runtime
- teams / handoffs / routed agents / actor-like structure
- explicit distributed-agent thinking

Implication:

- strong reference for future distributed role-runtime or cross-node multi-agent coordination
- should inform role-runtime architecture, not replace the current domain kernel wholesale

## 7.4 CrewAI

Useful lessons:

- crews + flows split
- event-driven workflow framing
- operational automation packaging
- enterprise automation UX direction

Implication:

- good reference for future workflow authoring/product UX
- should not drive a premature rewrite of the existing kernel

## 7.5 MCP

Useful lessons:

- clean separation between tools, resources, prompts
- client/server capability negotiation
- standardized protocol boundary

Implication:

- MCP should be an important part of the **general external capability integration layer**
- MCP should **not** be treated as the entire platform abstraction; it is one boundary, not the only boundary

## 7.6 Temporal / Prefect / Trigger.dev

Useful lessons:

- durable background workflows
- long-running job supervision
- managed queues / schedules / triggers / automation loops
- live status and operational monitoring

Implication:

- very relevant for the repo’s missing background-controller / automation plane
- these systems are more directly analogous to the repo’s future automation-control needs than to its inner review/evidence kernel

### Conclusion from framework comparison

The right strategic choice is:

> Keep the current kernel. Generalize its abstractions. Borrow proven patterns. Avoid rewriting the project around any single external framework.

---

## 8. Readiness assessment by dimension

| Dimension | Assessment | Notes |
|---|---|---|
| Core lifecycle kernel | Strong | compile/recompile/resume/review/repair are real |
| Governance & auditability | Strong | review policies, audit reports, replay, inspection are already valuable |
| Operator observability | Strong | status, packets, operator view, web UI, TUI all exist |
| Capability integration baseline | Medium-Strong | descriptors, health, projection, MCP, worker pools exist |
| External execution boundary | Medium-Strong | worker pools and scheduler authority are credible baselines |
| General orchestration substrate | Medium | current baseline is real, but not yet generalized enough |
| Dynamic role system | Weak | not first-class yet |
| Natural-language workbench UX | Weak | backend hints exist, product surface does not |
| Background automation / long-running control loops | Weak-Medium | not yet first-class |
| Ecosystem / packaging model | Medium-Weak | seeds and skill export exist, but packaging architecture is still early |
| Safe self-upgrade path | Weak | evaluation and repair exist, but self-improvement loop is not yet platformized |

---

## 9. Overall verdict

### 9.1 What this project is now

Today, `universalworkflow` is best described as:

> **A local-first agentic execution and governance kernel with real operator control, strong lifecycle semantics, and an emerging platform architecture.**

### 9.2 What it is not yet

It is not yet:

- a fully generalized multi-agent orchestration platform
- a polished natural-language workbench
- a mature ecosystem platform with stable extension packs
- a safe self-improving autonomous engineering system

### 9.3 What the next phase should be

The next phase should be:

> **M31: architecture hardening, protocol unification, orchestration generalization, and interaction-plane/product-plane construction.**

### 9.4 Final judgment

This repository is worth pushing forward.

But the path forward should be disciplined:

- **do not** broaden first
- **do not** rewrite the kernel into someone else’s framework
- **do not** confuse operator maturity with product maturity
- **do** formalize the internal platform boundaries now
- **do** make orchestration, role definition, interaction sessions, and capability invocation first-class architecture objects
- **do** prepare the system for productization and ecosystem growth by reducing implicit coupling before adding more surface area

In short:

> The repo has earned the right to become a serious platform. It has **not** yet earned the right to skip the platform-refactor step.

---

## 10. Recommended decision

Proceed to the next phase only under this framing:

- phase type: **bounded architecture/product hardening**
- goal: **turn the current kernel into a stable platform substrate**
- success condition: **the project can support humans, agents, and external systems through clean contracts rather than through one giant service surface**

That is the highest-value move available from the current state.
