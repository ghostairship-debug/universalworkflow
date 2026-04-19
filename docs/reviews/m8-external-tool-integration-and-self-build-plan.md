# M8 External Tool Integration, Replacement, And Continued Self-Build Plan

**Plan date:** 2026-04-19  
**Repository baseline:** `M7 complete` + `Pre-M8 complete`  
**Primary input:** [m8-ecosystem-reuse-and-wheel-reinvention-assessment.md](./m8-ecosystem-reuse-and-wheel-reinvention-assessment.md)

---

## 1. Goal

Define, in concrete terms:

- which generic infrastructure planes should stop deepening in-house
- which external ecosystems should be integrated instead
- which repository-owned semantics should continue to be self-built
- how those integrations should be attached without losing the repository's local-first control model

This document is a **design-and-planning input** for `M8 Phase 0`.
It is **not** a replacement for the repository's current control plane.

---

## 2. Top-Level Strategy

The repository should adopt this strategy:

- **Keep the repository as the local-first control plane**
- **Reuse the ecosystem for generic substrate**
- **Prefer adapter-based integration over core rewrites**
- **Prefer MCP-first capability loading over bespoke connector growth**
- **Keep governance, source-package discipline, simulation, and run/review semantics repository-owned**

In short:

- **Reuse the substrate**
- **Keep the operating model**

---

## 3. Recommended Architecture Split

### A. Repository-owned control plane

Keep self-built:

- run contracts and lifecycle semantics
- compile / recompile / resume / approve / reject / cancel / reconcile flow
- source-package export rules
- documentation governance
- offline validation and release gates
- deterministic simulation and simulation policy semantics
- domain-pack resolution semantics
- memory-item semantics derived from repository execution
- operator-facing local projections such as:
  - `status-detail`
  - `inspection`
  - `summary`
  - `audit-report`
  - `release-readiness`

### B. Externally reused substrate

Reuse instead of deepening in-house:

- connector discovery and tool registry loading
- portable skill packaging
- generic tracing / eval / experiment backends
- generic interrupt / approval substrate
- generic durable runtime persistence and resumption substrate
- managed third-party SaaS connectors

### C. Companion systems, not core replacements

Treat these as companion systems:

- LangGraph / Pydantic AI / Temporal / Prefect
- LangSmith / Langfuse / Phoenix
- Smithery
- n8n / Dify / Flowise

Do **not** replace the core local-first repository with those systems wholesale.

---

## 4. Decision Matrix

## 4.1 Replace / stop deepening in-house

### 4.1.1 Connector registry and tool loading

**Current duplication**

- bespoke `CapabilityRegistry`
- custom per-tool/provider growth pressure
- custom connector discovery semantics

**Decision**

- Stop growing a private connector plane.
- Shift to **MCP-first capability loading**.

**Primary external reuse**

- MCP specification and SDKs
- official/community MCP servers
- Smithery registry/install/search flows
- LangChain MCP adapters or Pydantic AI MCP where useful

**Repository role after replacement**

- keep `CapabilityRegistry`, but repurpose it into:
  - capability filter
  - capability policy layer
  - tool projection layer
- do **not** keep it as a long-term bespoke tool registry

**Expected improvement**

- faster tool coverage growth
- less first-party adapter maintenance
- less provider-specific duplication
- cleaner path to external connectors

### 4.1.2 Private skill packaging

**Current duplication**

- local skill-like packaging that could drift from ecosystem conventions

**Decision**

- Align the repository's skill packaging model with **Agent Skills**.

**Primary external reuse**

- Agent Skills specification
- `SKILL.md` portability conventions
- compatible skill registries such as Smithery

**Repository role after replacement**

- keep local skills
- stop inventing incompatible packaging rules
- expose any repository-owned reusable capability packs through Agent Skills-compatible structure

**Expected improvement**

- portability
- reuse of ecosystem skill assets
- lower future integration cost with LangChain Deep Agents / Pydantic AI / coding-agent ecosystems

### 4.1.3 Full proprietary tracing / eval platform ambitions

**Current duplication**

- growing local reporting surfaces that could drift toward a proprietary observability stack

**Decision**

- Stop extending local reports into a full trace/eval platform.
- Keep local operator projections, but externalize generic tracing/eval infrastructure.

**Primary external reuse**

- Langfuse
- Phoenix
- LangSmith

**Repository role after replacement**

- keep local projections as operator/governance outputs
- export traces, spans, eval records, and run metadata outward

**Expected improvement**

- better experiment management
- better trace search and comparison
- lower internal maintenance burden

---

## 4.2 Integrate with adapters, keep repository semantics

### 4.2.1 Durable runtime substrate

**Current duplication risk**

- claims
- leases
- attempts
- snapshots
- partial durable state progression
- local suspend/resume/repair deepening

**Decision**

- Do not rewrite immediately.
- Pilot a durable execution backend under `RuntimeGateway`.

**Recommended order**

1. **LangGraph** as first pilot
2. **Pydantic AI durable execution** as secondary path if the team prefers stronger Python-native MCP/toolset ergonomics
3. **Temporal** only if industrial durability and infrastructure weight are justified
4. **Prefect** only if deployment/event/schedule ergonomics become more important than agent-native control semantics

**Repository role after integration**

- keep run/review/governance contracts
- map runtime engine state into repository state
- do not expose raw framework state as the product contract

**Expected improvement**

- stronger resume/interruption semantics
- less bespoke durable-state deepening
- easier future HITL and long-running flow support

### 4.2.2 Generic HITL substrate

**Current duplication risk**

- generic approval gating and suspension machinery

**Decision**

- Keep repository `review_policy` and review semantics.
- Stop deepening generic interruption/approval substrate entirely in-house.

**Primary external reuse**

- LangGraph interrupts / human-in-the-loop
- OpenAI Agents SDK HITL
- similar substrate in runtime engines if selected

**Repository role after integration**

- preserve `auto_only`, `recommended`, `human_required`, `mandatory`
- preserve operator-visible `review` semantics
- remap framework-level pauses/approvals into repository review state

**Expected improvement**

- less bespoke state machinery
- cleaner future alignment with durable runtime engines

### 4.2.3 Memory/session plumbing

**Current duplication risk**

- generic memory/session/context transport

**Decision**

- Keep repository-owned `memory_item` and selection semantics.
- Allow external frameworks to carry generic session/context substrate underneath.

**Primary external reuse**

- LangGraph memory/checkpoint substrate
- Pydantic AI / Mastra / OpenAI Agents SDK session primitives

**Repository role after integration**

- retain:
  - memory namespaces
  - memory candidates
  - memory item persistence
  - compile-time memory brief semantics
- avoid rebuilding generic context/session infrastructure if an engine already provides it

**Expected improvement**

- less duplication in generic state transport
- easier runtime integration

### 4.2.4 External automation / workflow hosts

**Decision**

- Treat n8n / Dify / Flowise as external companions, not core replacements.

**Best use**

- expose selected repository actions as tools
- consume their workflows as tools
- use them for external automation, SaaS glue, or business workflow surfaces

**Repository role after integration**

- remain the source of truth for local-first runs, governance, freeze reviews, and source-package discipline

**Expected improvement**

- broader integration coverage without core replacement

---

## 4.3 Continue self-building

These areas should remain repository-owned.

### 4.3.1 Run/review/governance operating model

Keep self-built:

- run lifecycle contract
- compile / recompile / resume semantics
- run-to-review mapping
- freeze review discipline
- repo-native task-card governance

This is the core product identity.

### 4.3.2 Source-package and documentation governance

Keep self-built:

- source-package export policy
- documentation governance
- release gate discipline
- pre-freeze validation evidence

These are not commoditized well by the ecosystem.

### 4.3.3 Deterministic simulation

Keep self-built:

- simulation policy model
- deterministic simulation runner semantics
- simulation-record lifecycle hooks
- operator-facing simulation interpretations

### 4.3.4 Domain-pack semantics

Keep self-built:

- domain-pack resolution semantics
- pack-to-run projection
- compile-facing pack behavior

### 4.3.5 Memory-item semantics

Keep self-built:

- memory candidates
- namespace strategy
- item persistence semantics
- compile-time memory brief selection rules

### 4.3.6 Operator projections

Keep self-built:

- `status-detail`
- `inspection`
- `summary`
- `audit-report`
- `release-readiness`

These should stay as local governance surfaces even if traces/evals are exported elsewhere.

---

## 5. Detailed Tool Recommendations

## 5.1 Capability / connector plane

### Primary recommendation

- **MCP-first capability plane**

### Supporting tools

- official MCP servers
- Smithery for discovery/install/search
- LangChain MCP adapters or Pydantic AI MCP when direct MCP client logic is useful

### Repository integration pattern

Introduce:

- `CapabilitySource`
- `MCPServerProfile`
- `MCPCapabilitySource`
- `ToolProjectionManifest`

Recommended layering:

1. `CapabilitySource` loads available tools/resources from one source
2. `CapabilityRegistry` filters and normalizes them
3. compile step emits a `ToolProjectionManifest`
4. runtime receives only the projected tool subset

### What not to do

- do not expose all discovered MCP tools to the model
- do not drop router/policy control
- do not replace local capability policy with raw MCP server exposure

## 5.2 Observability / eval plane

### Primary recommendation

- **Langfuse** as the default vendor-neutral tracing/eval backend

### Alternative choices

- **LangSmith** if the durable runtime pilot chooses LangGraph and the team wants the tightest ecosystem alignment
- **Phoenix** if the team prioritizes local/open evaluation workflows

### Repository integration pattern

Introduce:

- `TraceExporter`
- `RunTraceEnvelope`
- `EvalArtifactExporter`

Export:

- run ids
- phase ids
- review policy
- adapter/tool projection summary
- selected event/state transitions
- simulation references

Keep local:

- operator-facing summary and governance wording

## 5.3 Skill packaging

### Primary recommendation

- **Agent Skills** compatibility

### Repository integration pattern

Introduce:

- `SkillManifest`
- `SkillPackageValidator`
- compatibility rules for repository local skills

Migration rule:

- existing local skill assets remain
- packaging and metadata converge toward Agent Skills structure

## 5.4 Durable runtime engine

### Primary recommendation

- **LangGraph pilot behind `RuntimeGateway`**

### Secondary option

- **Pydantic AI durable execution** if the team wants stronger Python-native toolset/MCP ergonomics and is willing to evaluate a different runtime style

### Repository integration pattern

Introduce:

- `RuntimeEngineAdapter`
- `LangGraphRuntimeAdapter`
- state mapping rules between framework state and repository state

Rules:

- repository state remains canonical product state
- framework state remains implementation substrate
- no `langgraph` imports leak into repository contracts/core domain boundaries

## 5.5 Companion workflow hosts

### Recommended posture

- companion-only

### Suggested usage

- n8n for external automations and business process glue
- Dify for external plugin/workflow/tool hosting
- Flowise only if the team later wants a visual agentflow lane

### Repository integration pattern

- integrate them via MCP/tools/webhooks
- do not move the repository core onto their runtime model

---

## 6. MCP-First Token And Context Policy

This repository should adopt **router-first MCP**, not model-first MCP.

### Required rules

1. **Projection before exposure**

- compile/runtime must decide the allowed tool subset first
- models see only projected tools, never the full MCP surface

2. **Small active tool set**

- normal target:
  - one active server when possible
  - one to five active tools

3. **Schema minimization**

- expose normalized, concise tool descriptions
- avoid dumping full raw server manifests into model context

4. **Resource retrieval is not prompt stuffing**

- fetch resources only when needed
- summarize or structure them before prompt injection
- never blindly inject large raw MCP resources

5. **Stable manifests**

- cache capability metadata by source/version
- avoid resending full tool descriptions every turn if runtime supports persistent tool registration

6. **Policy-bound exposure**

Projection should be filtered by:

- `preset`
- `task_kind`
- `domain_pack`
- `adapter_name`
- review policy
- execution trust boundary

### Expected result

- MCP-first integration without uncontrolled token explosion

---

## 7. Recommended M8+ Delivery Sequence

This is the recommended execution order after `M8 Phase 0`.

## 7.1 M8 Phase 0 - Feature Rebaseline And Scope Freeze

Freeze:

- what stops being deepened in-house
- what becomes MCP-first
- what stays repository-owned
- which durable engine pilot will be tried first
- which observability backend will be tried first

Required outputs:

- architecture decision record for MCP-first capability plane
- architecture decision record for durable runtime pilot
- architecture decision record for trace/eval backend choice

## 7.2 M8 Phase 1 - MCP-First Capability Plane Pilot

Build:

- `CapabilitySource`
- `MCPCapabilitySource`
- server profiles
- tool projection manifest
- filtered runtime exposure path

Success criteria:

- at least one real MCP server integrated
- projected tool subset visible in runtime surfaces
- token policy enforced by design

## 7.3 M8 Phase 2 - Skill Packaging Standardization

Build:

- Agent Skills-compatible metadata layer
- repository skill validation rules
- migration notes for local skills/plugins

Success criteria:

- repository-owned skills can be exported/reused without proprietary packaging lock-in

## 7.4 M8 Phase 3 - Trace/Eval Backend Integration

Build:

- trace exporter
- correlation mapping from local run ids to external trace ids
- selected eval/export pipeline

Success criteria:

- local reports remain unchanged
- external backend receives structured run traces and selected evaluation signals

## 7.5 M8 Phase 4 - Durable Runtime Pilot

Build:

- first runtime engine adapter
- controlled pilot path for one run class
- state mapping and regression tests

Success criteria:

- one repository run path is backed by the selected durable runtime engine
- no leakage of framework state into public repository contracts

## 7.6 M8 Phase 5 - Companion Workflow Integration

Build only if needed:

- one external workflow host integration via MCP or tool/webhook bridge

Success criteria:

- repository can call companion workflows without surrendering core control-plane ownership

## 7.7 M8 Freeze Review

Confirm:

- MCP-first capability plane is real, not aspirational
- external tracing/eval is connected
- at least one durable runtime pilot exists
- custom development remains focused on repository-owned semantics

---

## 8. What Should Explicitly Not Happen

- do **not** rewrite the repository core onto Dify / Flowise / CrewAI / AutoGen
- do **not** abandon the local-first control model
- do **not** expose full MCP inventories directly to the model
- do **not** replace operator-facing local governance surfaces with external observability dashboards
- do **not** continue deepening bespoke connector infrastructure if MCP-first loading is available
- do **not** continue building a private incompatible skill ecosystem

---

## 9. Priority Ranking

If only the highest-value items are executed first, the recommended order is:

1. MCP-first capability plane
2. external trace/eval backend
3. Agent Skills packaging alignment
4. durable runtime pilot
5. companion workflow host integration

This order gives the largest reduction in wheel-reinvention risk while preserving the repository's differentiating value.

---

## 10. Bottom-Line Recommendation

The right move is **not** to replace the repository.
The right move is to **stop rebuilding generic substrate** and turn the repository into a stronger local-first control plane sitting on top of reused ecosystem infrastructure.

That means:

- replace bespoke connector growth with MCP-first loading
- replace proprietary skill packaging with Agent Skills alignment
- replace full in-house observability ambitions with an external backend
- pilot a durable runtime engine under `RuntimeGateway`
- keep run/governance/source/simulation/domain semantics custom

That is the highest-leverage path into `M8` and beyond.
