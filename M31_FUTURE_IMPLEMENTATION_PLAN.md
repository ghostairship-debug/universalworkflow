# M31+ Future Implementation Plan

Date: 2026-04-21  
Status: Proposed architecture blueprint  
Purpose: define the future implementation direction after current-state remediation, with emphasis on multi-agent collaboration, fixed roles, dynamic roles, orchestration, natural-language interaction, external capability integration, self-improvement, engineering execution, and usability

---

## 1. Design target

The future version of `universalworkflow` should not be framed as “a workflow runner with some agent features.”

It should be framed as:

> **A local-first agentic engineering and operations platform made of three cooperating products:**
>
> 1. a deterministic control plane
> 2. a conversational / guided interaction workbench
> 3. a pluggable execution and capability runtime

This future system must work well for three classes of callers:

- **humans**: product builders, operators, reviewers, developers
- **agents**: planners, researchers, coders, reviewers, monitors, domain specialists
- **external systems**: APIs, worker pools, schedulers, IDEs, CI, MCP hosts, future SaaS surfaces

And it must support three modes of execution:

1. **deterministic workflow mode**  
   good for auditable, fixed, policy-heavy workflows

2. **agent-assisted workflow mode**  
   good for bounded reasoning inside a code-owned orchestration shell

3. **delegated specialist mode**  
   good for dynamic role spawning, distributed execution, and specialized sessions when properly governed

---

## 2. Core architectural thesis

The best future architecture is **not** “let the strongest model run everything.”

The best future architecture is:

> **Code-owned outer control, contract-owned state, model-owned bounded cognition, and operator-owned final governance.**

That means:

- state transitions remain explicit
- orchestration is compiled and inspectable
- models can plan and execute within bounded nodes
- tool and capability access is contract-governed
- review, budget, risk, and trust decisions remain part of the control plane
- natural-language interaction sits on top of the control plane rather than bypassing it

This is the architecture most likely to maximize:

- reliability
- extensibility
- debuggability
- operator trust
- future productization

---

## 3. Proposed reference architecture

The future platform should be organized into **seven planes**.

```text
+--------------------------------------------------------------+
|  Interaction Plane                                            |
|  chat/workbench | guided launch | operator UI | CLI | SDK     |
+--------------------------------------------------------------+
|  Planning & Orchestration Plane                               |
|  intent -> plan -> graph compile -> schedule -> supervise     |
+--------------------------------------------------------------+
|  Role System Plane                                            |
|  fixed roles | dynamic roles | role registry | role factory   |
+--------------------------------------------------------------+
|  Capability Runtime Plane                                     |
|  adapters | MCP | worker pools | sessions | remote runtimes   |
+--------------------------------------------------------------+
|  Memory & Knowledge Plane                                     |
|  session memory | run memory | artifact memory | skill memory |
+--------------------------------------------------------------+
|  Governance & Observability Plane                             |
|  policy | audit | replay | evals | trace | repair | budgets   |
+--------------------------------------------------------------+
|  Kernel / Control Plane                                       |
|  lifecycle | snapshots | claims | leases | scheduler truth    |
+--------------------------------------------------------------+
```

The key idea is that the planes are layered, but not siloed.

- the kernel provides truth
- governance inspects and constrains truth
- memory augments context
- capability runtime executes work
- role system determines who/what acts
- orchestration decides in what order and structure things happen
- interaction plane makes it usable

---

## 4. Canonical platform objects

To make the architecture stable, the future system should revolve around a small set of canonical objects.

## 4.1 Interaction objects

- `IntentSession`
- `IntentPacket`
- `ClarificationState`
- `PlanDraft`
- `LaunchDecision`
- `ConversationTurn`
- `FollowupRequest`

These objects represent what the user is trying to do, how the system clarified it, and what approved plan led to execution.

## 4.2 Orchestration objects

- `ExecutionGraph`
- `NodeSpec`
- `EdgeSpec`
- `BarrierSpec`
- `ReducerSpec`
- `ApprovalGateSpec`
- `RetryPolicy`
- `WatchdogPolicy`

These objects represent the structure of work.

## 4.3 Role objects

- `RoleTemplate`
- `RoleSpec`
- `RoleAssignment`
- `RoleExecutionContext`
- `RoleTerminationRule`
- `RoleEvaluationRubric`

These objects represent who is allowed to act and under what constraints.

## 4.4 Capability objects

- `CapabilityDescriptor`
- `CapabilitySelection`
- `CapabilityInvocationEnvelope`
- `CapabilityExecutionReceipt`
- `ToolProjectionManifest`
- `CapabilityTrustPolicy`
- `SandboxProfile`

These objects make every backend capability look structurally coherent to the platform.

## 4.5 Memory objects

- `SessionMemoryItem`
- `RunMemoryItem`
- `ArtifactMemoryItem`
- `SkillMemoryItem`
- `MemoryRetrievalPlan`
- `MemoryPromotionRule`

These objects let memory become a product subsystem instead of a side utility.

## 4.6 Governance and evolution objects

- `EvalScenario`
- `EvalReport`
- `RepairPlan`
- `UpgradeProposal`
- `CanaryPolicy`
- `PromotionDecision`

These objects make self-improvement and controlled evolution explicit.

---

## 5. Multi-agent collaboration model

The collaboration model should support multiple patterns, but one default philosophy should dominate:

> **The platform chooses the collaboration topology; the model fills in bounded decisions inside that topology.**

### 5.1 Supported collaboration patterns

The future platform should support at least these patterns.

#### Pattern A — Manager-as-code

- the graph and flow are determined by code / compiled plan
- specialist agents are used as bounded executors
- good for predictable and high-governance workflows

This should be the default for engineering, release, mutation, and policy-sensitive flows.

#### Pattern B — Specialists-as-tools

- a manager agent owns the final answer
- specialist agents are wrapped as tools
- good when the user should keep talking to one primary agent

This is the best default for conversational workbench UX.

#### Pattern C — Handoff / routed-specialist mode

- one agent transfers the active role to another
- good for support-like flows or domain-specialist deep dives
- should be opt-in, not the global default

#### Pattern D — Parallel map / reducer mode

- multiple roles execute concurrently
- outputs are reduced, reviewed, or merged
- good for research, code + test, multi-perspective review, and batch execution

#### Pattern E — Reviewer quorum / debate mode

- several reviewers or evaluators inspect the same output
- a stronger consolidator or explicit reducer combines their outputs
- should be used when false positives / false negatives matter

### 5.2 Anti-loop policy

Every collaboration mode should be bounded by:

- max iterations
- max tool iterations
- time budget
- token budget
- max handoffs
- escalation conditions
- stall detection
- watchdog kill / reroute

This is where the current monitor/operator idea becomes important. The platform should have a **first-class monitor role** and a **watchdog policy** that can:

- interrupt low-progress loops
- request clarification
- downgrade to deterministic path
- switch models
- escalate to human review

---

## 6. Fixed role system

The future system should have a small, well-designed set of fixed core roles.

These roles are not prompts only. They should be part of the platform contract.

## 6.1 Mandatory core roles

### 1. Planner

Purpose:

- transform intent into an execution graph or draft plan

Inputs:

- goal
- constraints
- domain context
- policy rules
- available capabilities

Outputs:

- plan draft
- graph candidate
- capability assumptions
- risk notes

### 2. Architect

Purpose:

- turn plan into technical decomposition
- define boundaries, interfaces, and sequencing

Outputs:

- technical task breakdown
- dependency graph
- implementation notes
- risk hotspots

### 3. Retriever / Researcher

Purpose:

- collect relevant repo context, docs, external context, or prior artifacts

Outputs:

- evidence bundle
- uncertainty report
- cited context set

### 4. Coder

Purpose:

- perform implementation work inside bounded mutation or artifact contracts

Outputs:

- patch / artifact / code change / generated files
- self-report of assumptions and changed scope

### 5. Tester / Verifier

Purpose:

- run checks, tests, reproduction flows, linting, validation scripts

Outputs:

- verification result
- failing cases
- reproducibility notes

### 6. Reviewer

Purpose:

- judge output quality, requirement fit, safety, maintainability, and risk

Outputs:

- verdict
- issues
- severity
- recommended next step

### 7. Policy Guardian

Purpose:

- enforce trust, capability, mutation, review, and budget rules

Outputs:

- allow/deny/defer decisions
- policy deltas
- escalation triggers

### 8. Monitor / Operator Agent

Purpose:

- observe live execution and detect stalls, loops, or drift

Outputs:

- interventions
- reroute requests
- health summaries
- escalation signals

### 9. Release Manager

Purpose:

- package results, summarize readiness, prepare ship/no-ship decisions

Outputs:

- release packet
- readiness checklist
- post-run summary

## 6.2 Optional domain roles

Later, domain packs can contribute optional roles such as:

- security reviewer
- product spec writer
- infra operator
- data migration specialist
- localization specialist
- performance analyst
- game-design / narrative / content specialist

These should plug into the same role contract rather than inventing new execution semantics.

---

## 7. Dynamic role generation system

The fixed roles above are necessary, but not sufficient.

The platform also needs **即时 agent 角色生成** — dynamic role creation — because many real workflows need short-lived specialists.

## 7.1 Dynamic role generation principle

A generated role should be:

- **ephemeral**: scoped to one plan/graph/session unless explicitly promoted
- **typed**: created from a stable `RoleSpec`, not from freeform text only
- **bounded**: limited by tools, reposcope, trust, time, and stop rules
- **reviewable**: visible to operator and to audit products
- **cacheable**: reusable through template promotion if it performs well

## 7.2 Role factory input

The `RoleFactory` should take structured inputs such as:

- objective gap
- required deliverable type
- domain
- risk tier
- required capabilities
- expected interaction style
- max autonomy level
- review requirement
- budget envelope

## 7.3 Role factory output

The output should be a `RoleSpec` like:

- `role_id`
- `role_kind` (`fixed`, `generated`, `promoted_template`)
- `name`
- `objective`
- `success_criteria`
- `allowed_capabilities`
- `allowed_memory_namespaces`
- `allowed_repo_scope`
- `review_requirement`
- `max_iterations`
- `termination_conditions`
- `escalation_target`
- `preferred_models`
- `visibility_level`

## 7.4 Generated role lifecycle

A generated role should follow a lifecycle:

1. proposed
2. accepted into graph
3. executed
4. evaluated
5. archived
6. optionally promoted to reusable template

### Promotion rule

A generated role should only become a reusable template if:

- it performs repeatedly well
- its capability set is safe and understandable
- its outputs are predictable enough
- its audit trail is strong enough to justify reuse

This prevents the platform from becoming an ungoverned pile of emergent personas.

---

## 8. Automated orchestration system

The future orchestration engine should compile work into explicit graph nodes.

## 8.1 Required node types

At minimum, the engine should support:

- `AgentNode`
- `ToolNode`
- `CapabilityNode`
- `HumanGateNode`
- `ApprovalGateNode`
- `ParallelMapNode`
- `ReducerNode`
- `EvalNode`
- `RepairNode`
- `PublishNode`
- `WaitEventNode`
- `ScheduleNode`
- `BranchDecisionNode`

## 8.2 Graph compilation path

The graph compiler should support three sources:

### Source A — fixed templates

For stable flows like:

- feature delivery
- guarded delivery
- project delivery
- release prep
- incident investigation

### Source B — plan-derived compilation

A planner outputs a structured draft; the compiler turns it into an explicit execution graph.

### Source C — dynamic hybrid graph

The graph starts from a template, then injects generated roles or branches based on runtime conditions.

## 8.3 Scheduling and control

The orchestration engine should separate:

- graph compilation
- graph scheduling
- node execution
- graph supervision
- graph repair

That makes it possible to add:

- background execution
- distributed workers
- queue-based execution
- canary execution
- replay and re-fork

without redesigning the graph language each time.

---

## 9. General external capability integration

The platform should treat all external execution capabilities as members of one governed family.

## 9.1 Integration categories

The system should support at least these categories:

1. built-in tools
2. MCP tools/resources/prompts
3. local process adapters
4. external worker pools
5. sessionful external runtimes
6. hosted model/provider runtimes
7. IDE / repo / browser / CI connectors
8. long-running background jobs

## 9.2 Unified capability contract

Every integration should project into the same logical structure:

- identity
- transport
- auth mode
- trust tier
- side-effect level
- allowed task kinds
- timeout budget
- review requirement
- evidence schema
- observability hooks
- sandbox profile

## 9.3 MCP’s role in the future architecture

MCP should be used for what it is good at:

- standardizing tool exposure
- standardizing resources and prompts
- reducing connector fragmentation

But the platform should **not** reduce all execution architecture to MCP alone.

MCP is one excellent boundary. It is not the whole platform.

## 9.4 Capability SDK / registration path

The future platform should offer a clean registration model for capabilities, for example:

- `register_tool_capability()`
- `register_worker_pool()`
- `register_session_runtime()`
- `register_mcp_profile()`
- `register_role_pack_capabilities()`

This will make ecosystem expansion sane later.

---

## 10. Natural-language human-computer interaction

The future platform needs a **true NL interaction plane**, not just goal-to-run launch helpers.

## 10.1 The NL flow should be stateful

The ideal interaction loop is:

1. user states goal
2. system clarifies ambiguity
3. system proposes plan / graph / risk / capability assumptions
4. user approves, edits, or narrows scope
5. system launches execution
6. system streams progress, evidence, and issues
7. user issues follow-up instructions in natural language
8. system maps them to structured changes or new graph branches

## 10.2 Conversation state vs execution state

These must remain separate.

- **conversation state** is for interaction continuity
- **execution state** is for run truth and replay

They should reference each other, but not collapse into one object.

## 10.3 Product surface modes

The future UI should offer at least three modes:

### Mode A — Simple goal mode

For users who want:

- “do this task”
- minimal planning overhead
- strong defaults

### Mode B — Guided project mode

For users who want:

- plan preview
- role visibility
- capability choice visibility
- explicit human gates

### Mode C — Operator mode

For advanced users who want:

- run explorer
- claims and lease detail
- scheduler topology
- repair / reconcile actions
- audit and replay tools

This layered UX approach preserves ease of use without sacrificing depth.

---

## 11. Memory and knowledge architecture

The current memory system should evolve into a layered model.

## 11.1 Memory layers

### Layer 1 — Session memory

- tracks user preferences, recent conversation context, active objectives
- used for workbench continuity

### Layer 2 — Run memory

- tied to one execution run or graph
- stores useful facts, retrieved evidence summaries, failures, decisions, checkpoints

### Layer 3 — Artifact memory

- stores reusable implementation patterns, outputs, generated documents, change reports

### Layer 4 — Skill memory

- stores reusable procedural know-how, role templates, domain-specific strategies

### Layer 5 — Policy/failure memory

- stores prior risk findings, policy escalations, repeated failure motifs, regression signatures

## 11.2 Memory access rules

Memory retrieval should be constrained by:

- role
- capability trust tier
- run risk level
- user/session scope
- repo or project boundary
- review requirement

This turns memory from “context stuffing” into a governed system primitive.

---

## 12. Self-iteration and self-upgrade

The platform should support self-improvement, but only through a controlled loop.

## 12.1 What self-improvement should mean

It should mean:

- the system can detect repeated friction
- propose improvements
- run bounded experiments
- evaluate changes
- ask for approval where appropriate
- safely adopt good changes

It should **not** mean:

- unconstrained auto-refactoring on mainline
- self-modification without eval
- auto-promotion of unreviewed role packs or capabilities

## 12.2 Proposed self-improvement loop

1. detect friction / regression / repeated operator interventions
2. generate `UpgradeProposal`
3. compile bounded change plan
4. execute in isolated branch/workspace/sandbox
5. run benchmark/eval suite
6. generate report and diff summary
7. request human approval if needed
8. promote / reject / re-run

This is where the current repo’s mutation contract, audit, replay, repair, and snapshot model can become a powerful advantage.

---

## 13. Arbitrary engineering development path

This project clearly wants to support “任意工程开发” rather than only prompt-style flows.

The future architecture should lean into that explicitly.

## 13.1 Engineering task should become a first-class task family

The future system should formalize an `EngineeringTaskSpec` that can cover:

- code changes
- docs changes
- config changes
- test additions
- infra changes
- data migration changes
- repo analysis and remediation
- release preparation

## 13.2 Engineering contract fields

Example fields:

- repo/workspace target
- branch / session target
- read set
- write set
- mutation mode
- test plan
- rollback rule
- reviewer requirements
- packaging / PR rule
- acceptance criteria

## 13.3 Engineering execution modes

Support should include:

- local shell path
- opencode patch path
- sessionful collaborative path
- external worker path
- mixed path (research + mutation + verification)

This is a highly differentiated product direction if it stays bounded and well governed.

---

## 14. Ease-of-use strategy

The future system should be easy in layers, not easy by hiding everything.

## 14.1 Ease of use for beginners

- presets
- guided templates
- natural language launch
- safe defaults
- simple progress narrative

## 14.2 Ease of use for builders

- plan graph visibility
- role breakdown
- capability assumptions
- memory preview
- artifact and diff visibility

## 14.3 Ease of use for operators

- full detail when needed
- replay/audit packets
- repair actions
- cluster and lease visibility
- background job control

This layered usability model is better than either extreme:

- too abstract to trust
- too low-level to use

---

## 15. Recommended implementation phases

## Phase M31 — Platform hardening

Focus:

- kernel boundary split
- orchestration graph substrate
- interaction API v1
- background controller v1
- unified capability runtime contract

## Phase M32 — Role system and workbench

Focus:

- fixed role registry
- dynamic role factory
- workbench UX
- role-level evaluation rubrics
- monitor/watchdog subsystem

## Phase M33 — Capability ecosystem and pack model

Focus:

- capability SDK
- role packs
- skill packs
- domain-pack evolution
- validation/publishing pipeline

## Phase M34 — Distributed and long-running runtime maturity

Focus:

- robust external worker topology
- richer scheduler-authority paths
- remote queues / long-running jobs
- optional enterprise automation backends

## Phase M35 — Controlled self-improvement

Focus:

- eval-driven upgrade proposals
- canary infrastructure
- improvement reports
- promotion/rejection workflow

## Phase M36 — Product broadening

Focus:

- domain-specific packaged experiences
- stronger hosted surfaces if desired
- richer third-party ecosystem
- marketplace or private pack registries if justified

---

## 16. External framework adoption strategy

The platform should deliberately use external ecosystems by **role**, not by surrender.

### Use LangGraph for

- optional durable agent lanes
- graph-runtime experiments
- checkpoint semantics reference

### Use OpenAI Agents SDK patterns for

- specialists-as-tools
- handoff semantics
- tracing and multi-agent interaction design

### Use AutoGen patterns for

- distributed role runtime ideas
- actor-like async messaging patterns

### Use CrewAI ideas for

- flow authoring ergonomics
- team/workflow packaging UX

### Use MCP for

- standardized external tool/resource/prompt integration

### Use Temporal / Prefect / Trigger.dev ideas for

- background automation plane
- managed scheduling / long-running job control
- live operational status models

The rule should be:

> adopt patterns and optional runtimes where they strengthen the platform; do not replace the platform’s core state/governance model with someone else’s abstractions.

---

## 17. Final architecture recommendation

The strongest future version of `universalworkflow` is not a clone of any existing framework.

It is a hybrid system with a very specific shape:

- **kernel like a workflow control plane**
- **interaction like a serious AI workbench**
- **orchestration like a graph compiler**
- **roles like a governed multi-agent runtime**
- **capabilities like a unified integration platform**
- **evolution like an eval-driven engineering loop**

If built this way, the project can become unusually strong in exactly the areas that matter most for serious agentic systems:

- not just generation
- not just orchestration
- not just product UX
- but the union of **execution, governance, usability, and extensibility**

That is the future direction I recommend.
