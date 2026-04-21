# M31 Current-Stage Remediation Plan

Date: 2026-04-21  
Status: Proposed next-phase execution plan  
Purpose: remove the most serious structural problems before productization, ecosystem expansion, and deeper autonomy

---

## 1. Why this phase must happen now

The repository has already crossed the threshold where adding more features is no longer the highest-value move.

The current danger is not that the system is too small. The danger is that it may expand **before its platform boundaries are clean**.

That would create exactly the kind of drag that kills strong technical kernels:

- more adapters without a unified capability contract
- more surfaces without a unified interaction model
- more orchestration without a generalized orchestration DSL
- more autonomy without a background-control plane
- more product ambition without a product-facing architecture

This remediation phase exists to prevent that failure mode.

In one sentence:

> M31 should make the system easier to extend, easier to supervise, easier to productize, and safer to automate — **before** it becomes broader.

---

## 2. Target outcome of M31

At the end of M31, the repository should no longer feel like “one very strong service with many features.”

It should feel like a platform with clearly separated but cooperating layers:

1. **Kernel / control plane**  
   Deterministic lifecycle truth, governance, review, leases, snapshots, budgets, repair.

2. **Orchestration engine**  
   Generic execution-graph compilation and runtime control, no longer special-casing only one orchestration path.

3. **Interaction plane**  
   A canonical natural-language / guided workbench interface model above the kernel.

4. **Capability plane**  
   One unified contract for built-in tools, MCP, external workers, sessionful runtimes, and future providers.

5. **Automation plane**  
   Background controllers, timed/event-driven resumes, stale-run recovery, and long-lived operational loops.

If those five things are achieved, the project will be ready for real productization and controlled ecosystem expansion.

---

## 3. M31 design principles

This phase should follow a few non-negotiable principles.

### 3.1 Keep the monolith, split the boundaries

The repo does **not** need a microservice rewrite.

It **does** need clean architectural seams inside the monolith.

### 3.2 Code-driven outer control, model-driven inner execution

The system should treat LLM autonomy as a bounded execution strategy inside a larger code-controlled orchestration and governance framework.

That means:

- graph creation may involve models
- role execution may involve models
- tool selection may involve models
- but lifecycle transitions, policy enforcement, budget control, repair, and lease control should remain code-owned

### 3.3 Stable contracts before broad plugins

Before expanding providers, plugins, or external integrations, the platform contract must be made explicit.

### 3.4 Product surface must not be a thin wrapper over operator internals

The future NL workbench should be built **above** a dedicated interaction API, not directly against every operator-only projection.

### 3.5 Autonomy must be layered, not implicit

Self-improvement and autonomous loops should be added as explicit subsystems with budgets, scopes, and approval rules.

---

## 4. Problems to solve before expansion

Below are the problems that should be treated as blocking or near-blocking.

## 4.1 P0 — blocking problems

### P0-1. Oversized public service boundary

Problem:

- `OrchestratorService` is still too dominant
- too many concerns terminate at the same façade
- every new surface risks coupling to the same oversized contract

Why it blocks expansion:

- new UI, NL workbench, external SDK, background automation, and dynamic orchestration will otherwise all reinforce the wrong center of gravity

### P0-2. No generalized orchestration substrate

Problem:

- `project_delivery` proves orchestration works, but orchestration is not yet a generic reusable system model

Why it blocks expansion:

- fixed-role and dynamic-role systems cannot scale cleanly without a general graph / node / edge / barrier / approval / reducer model

### P0-3. No canonical interaction/session model

Problem:

- operator surfaces exist; natural-language workbench architecture does not

Why it blocks expansion:

- productization requires a stable way to represent intent, clarification, plan approval, execution supervision, and follow-up change requests

### P0-4. Policy preview is not enough

Problem:

- the system can describe policy implications well, but enforcement still needs strengthening as a platform boundary

Why it blocks expansion:

- more automation without stronger gating increases the risk of governance theater rather than governance control

### P0-5. No true background automation plane

Problem:

- there is lifecycle and operator control, but not yet a first-class automation controller for long-running loops, watchers, triggers, or stale-state recovery

Why it blocks expansion:

- productized multi-agent systems cannot rely only on foreground CLI/API actions

## 4.2 P1 — must follow closely behind

### P1-1. Capability integration is not unified enough

Problem:

- tools, adapters, MCP, worker pools, runtime gateway, and sessionful lanes are all present, but not yet collapsed into one universal capability invocation model

### P1-2. Memory is still kernel-first, not interaction-first

Problem:

- memory items/candidates exist, but session memory, conversation memory, project memory, and reusable skill memory are not yet differentiated enough

### P1-3. Packaging model is too early for broad ecosystem growth

Problem:

- domain packs and skill export exist, but stable distribution/versioning/composition boundaries are still immature

### P1-4. Evaluation and self-improvement loops are not yet platformized

Problem:

- inspection, repair, replay, and trace exist; systematic eval-driven evolution loop does not yet exist as a formal subsystem

---

## 5. The remediation architecture

The remediation plan introduces four explicit architectural boundaries inside the repo.

## 5.1 Boundary A — Kernel API

This is the inner deterministic control plane.

It owns:

- run lifecycle
- state transitions
- claims / worker leases / scheduler authority
- snapshots
- review state
- budgets
- inspection / reconciliation / repair
- evidence and audit products

It should be the strictest and most stable layer.

### Required change

Refactor the current service façade into a set of explicit kernel-facing services, for example:

- `RunKernelService`
- `LifecycleKernelService`
- `ReviewPolicyService`
- `OwnershipLeaseService`
- `SnapshotLineageService`
- `RepairReconciliationService`
- `AuditProjectionService`

`OrchestratorService` can remain as a compatibility façade, but it should become a coordinator over these services rather than the real architectural center.

## 5.2 Boundary B — Orchestration Engine

This becomes the general execution-graph system.

It should own:

- graph compilation
- node typing
- edge semantics
- barriers
- parallel groups
- reducers
- approval gates
- role assignment
- graph-level retries / escalations / watchdog policies

### Required change

Introduce a stable orchestration contract, such as:

- `ExecutionGraph`
- `NodeSpec`
- `EdgeSpec`
- `RoleSpec`
- `BarrierSpec`
- `ApprovalGateSpec`
- `ReducerSpec`
- `WatchdogPolicy`

Then move the existing `project_delivery` orchestration into a **graph definition** rather than leaving it embedded as privileged service logic.

## 5.3 Boundary C — Interaction API

This becomes the product-facing layer for humans and conversational agents.

It should own:

- goal capture
- ambiguity resolution
- intent/session state
- plan preview
- policy preview
- execution launch
- live supervision
- change requests
- follow-up runs / branches / retries

### Required change

Create canonical objects such as:

- `IntentSession`
- `IntentPacket`
- `PlanDraft`
- `LaunchDecision`
- `ConversationState`
- `RunFollowupRequest`

This layer should call into the kernel and orchestration engine, rather than exposing operator projections directly as the primary UX contract.

## 5.4 Boundary D — Capability Runtime

This becomes the unified integration and execution boundary.

It should own:

- built-in tools
- MCP tools/resources/prompts projection
- worker adapters
- external worker pools
- sessionful external runtimes
- runtime gateways
- future provider connectors

### Required change

Create one canonical capability invocation envelope, e.g.:

- `CapabilityDescriptor`
- `CapabilitySelection`
- `CapabilityInvocationEnvelope`
- `CapabilityExecutionReceipt`
- `CapabilityTrustPolicy`
- `CapabilitySandboxProfile`

The point is to make every execution path look structurally similar, even if the backend transport differs.

---

## 6. M31 workstreams

## WS1 — Shrink the façade without breaking surfaces

### Goal

Convert `OrchestratorService` from “god façade” into “compatibility façade + coordinator”.

### Concrete actions

1. Extract service modules by responsibility, not by file size only.
2. Move orchestration-specific logic out of the generic lifecycle service.
3. Move capability-selection logic into its own service.
4. Move repair/reconciliation logic into a dedicated service boundary.
5. Keep public CLI/API signatures stable while redirecting implementation paths.

### Exit criteria

- new services own the core domains
- `OrchestratorService` mostly delegates
- future surfaces can target stable sub-services or APIs instead of the giant façade

## WS2 — Generalize orchestration into a first-class graph model

### Goal

Make orchestration configurable and reusable instead of hardcoded.

### Concrete actions

1. Define a graph DSL / typed graph contract.
2. Re-express `project_delivery` as a graph definition.
3. Add support for:
   - sequential nodes
   - parallel nodes
   - barriers
   - reducers
   - approval gates
   - escalation / fallback nodes
4. Add graph validation and static preview.
5. Persist compiled graph objects and expose them through projections.

### Exit criteria

- a new orchestration can be added without editing core lifecycle logic
- `project_delivery` is no longer privileged service code
- graph preview becomes the authoritative orchestration representation

## WS3 — Turn policy preview into policy guard

### Goal

Upgrade policy visibility into policy enforcement.

### Concrete actions

1. Add enforced policy checks at compile time.
2. Add enforced policy checks at resume/dispatch time.
3. Add capability- and role-specific guard rules.
4. Tie trust tiers and mutation privileges into policy rules.
5. Add violation reports to projections and audits.

### Exit criteria

- high-risk actions cannot bypass review/budget/trust rules
- policy preview and actual execution policy stay aligned
- operator packet shows both preview and enforced result

## WS4 — Build the background automation/controller plane

### Goal

Allow the system to manage long-lived workflows without foreground-only control.

### Concrete actions

1. Add a background controller loop.
2. Add timed/event-driven resume triggers.
3. Add stale-run watchers.
4. Add waiting-review reminders and timeout handlers.
5. Add health reconciliation jobs for claims, leases, snapshots, and worker pools.
6. Expose automation state through API and operator surfaces.

### Exit criteria

- runs can continue to be supervised without manual polling
- stale / blocked / expired states are recoverable by background logic
- automation is explicit, inspectable, and bounded

## WS5 — Create the interaction plane v1

### Goal

Make the system usable through a proper natural-language / guided product layer.

### Concrete actions

1. Introduce `IntentSession` and `IntentPacket`.
2. Support goal -> clarify -> preview -> approve -> execute flow.
3. Support conversational supervision of existing runs.
4. Add event streaming for run state and evidence deltas.
5. Separate conversation memory from run execution state.
6. Build an initial workbench UI that sits above the new interaction API.

### Exit criteria

- users do not need to think in operator packets to start and supervise work
- follow-up language instructions can safely map to structured control actions
- workbench layer is additive and does not damage kernel clarity

## WS6 — Unify capability integration

### Goal

Make all external capability paths feel like one platform.

### Concrete actions

1. Standardize capability descriptor and invocation envelope.
2. Map worker adapters, MCP, worker pools, sessionful runtimes, and future tools into the same runtime contract family.
3. Add consistent trust, sandbox, and evidence metadata.
4. Add provider-agnostic policy hooks.
5. Add capability SDK / registration helpers.

### Exit criteria

- adding a new capability backend does not require invasive service edits
- policy, evidence, audit, and projections work consistently across backends
- human and agent callers see the same capability model

## WS7 — Formalize eval / trace / repair loop

### Goal

Turn current introspection assets into a reusable improvement system.

### Concrete actions

1. Define benchmark/eval suites by scenario.
2. Add standard evaluation packets tied to graph executions and role runs.
3. Promote trace export into a real observability spine.
4. Add regression gates for orchestration and capability changes.
5. Add controlled canary paths for new role definitions or integrations.

### Exit criteria

- changes can be judged by scenario performance, not intuition only
- repair is part of a measured loop, not just operator craftsmanship

## WS8 — Harden packaging and extension model

### Goal

Prepare for ecosystem growth without losing control.

### Concrete actions

1. Distinguish:
   - domain packs
n   - skill packs
   - role packs
   - capability packs
2. Add versioning and compatibility metadata.
3. Add validation tooling for pack publication.
4. Keep extension permissions and trust explicit.

### Exit criteria

- extensions are composable but governed
- pack installation is visible and auditable
- extension failure does not destabilize kernel invariants

---

## 7. Proposed M31 sequencing

M31 should be staged. Doing everything at once would recreate the same coupling problem in a different form.

## Phase M31-A — Internal boundary refactor

### Focus

- split façade responsibilities
- isolate orchestration service
- isolate capability selection service
- isolate repair service

### Must ship

- service decomposition
- stable internal module boundaries
- compatibility façade maintained

### Exit gate

No new product surface should need to depend directly on monolithic orchestration logic.

## Phase M31-B — Generic orchestration substrate

### Focus

- graph DSL
- role specs
- barrier/reducer/gate semantics
- project_delivery migration into graph definition

### Must ship

- reusable graph compiler
- orchestration registry
- graph preview as source of truth

### Exit gate

At least one new orchestration other than `project_delivery` should be definable without editing core lifecycle code.

## Phase M31-C — Interaction and automation plane

### Focus

- intent/session model
- NL workbench backend
- background controller loops
- event streaming

### Must ship

- interaction API v1
- automation controller v1
- initial workbench surface

### Exit gate

A user should be able to describe a goal, review a plan, launch it, and supervise it conversationally without leaving the supported product flow.

## Phase M31-D — Packaging and eval hardening

### Focus

- unified capability runtime contract
- extension packaging
- eval/canary framework
- trace spine hardening

### Must ship

- capability invocation envelope
- pack contract validation
- eval suites for core scenarios

### Exit gate

The system should be safe to extend and measurable to evolve.

---

## 8. What should explicitly NOT happen in M31

To protect focus, the following should be treated as non-goals for this phase.

### 8.1 Do not rewrite the kernel around a single external framework

No LangGraph rewrite.  
No AutoGen rewrite.  
No CrewAI rewrite.  
No “just use Temporal/Prefect as the product core” rewrite.

External frameworks should inform or power optional lanes, not replace the kernel’s domain model.

### 8.2 Do not broaden provider breadth aggressively

Adding many new providers now will mostly amplify contract ambiguity.

### 8.3 Do not open unconstrained self-modification loops

The repo already has strong bounded mutation paths. It should not yet jump to broad auto-refactor / auto-merge / auto-upgrade behavior without the new eval and approval architecture.

### 8.4 Do not build a pretty UI before the interaction API exists

A good-looking workbench without a strong interaction model would just hide structural debt.

### 8.5 Do not confuse “flag enabled” with “platform ready” 

Incubation features should not be treated as generally available platform surfaces until the surrounding contracts are stable.

---

## 9. Success criteria for M31

M31 should be considered successful only if the following become true.

## 9.1 Architectural success criteria

- `OrchestratorService` is no longer the true architectural choke point
- orchestration is a reusable graph system
- capability integration has one canonical invocation contract
- kernel, orchestration, interaction, and automation planes are cleanly separated

## 9.2 Product-readiness success criteria

- a natural-language or guided workbench can launch and supervise runs through a dedicated interaction API
- users can review plan graph and policy implications before launch
- follow-up instructions can safely map to structured control actions

## 9.3 Automation success criteria

- background controller loops can supervise waiting / stale / resumable workflows
- operator action is no longer required for every long-lived state change

## 9.4 Extensibility success criteria

- new orchestration templates can be added without editing central lifecycle code
- new capability backends can be added without invasive service edits
- packaging/extension contracts are versioned and validated

## 9.5 Safety success criteria

- policy enforcement is real, not only projected
- high-risk mutation and high-trust capability paths remain bounded
- self-improvement remains proposal-driven and reviewable

---

## 10. Final recommendation

The recommendation is straightforward:

> **Do M31 now, and do it as a strict platform-hardening phase.**

This repo already has enough kernel power. The next source of value is not wider breadth. It is:

- cleaner boundaries
- safer autonomy
- reusable orchestration
- better interaction design
- a truly unified capability platform

If M31 is executed well, the repository can then move into productization and ecosystem expansion from a position of architectural strength.

If M31 is skipped, every future success will become more expensive than it needs to be.

That is why this phase should be treated as foundational, not optional.
