# M32 Phase 0: Interaction / Profile / Cluster Foundation

Status: active  
Opened: 2026-04-22  
Baseline: accepted `M31 Phase 0`

## Purpose

Open the first bounded post-`M31 Phase 0` phase as an interaction-first `M32` line. This phase establishes the minimum platform objects required to move beyond the `project_delivery` special path without opening automation-plane breadth.

The phase has five concrete outcomes:

1. formal `M32` opening, task-card pack, and carry-forward governance
2. interaction-plane contracts and a minimum interaction service
3. a stable two-layer execution model: public roles plus agent profiles
4. first-class execution-cluster templates
5. cluster-aware graph, packet, and workbench preview surfaces

## Why This Phase Exists

The accepted `M31 Phase 0` closeout left six structural debts open:

- `TD-STRUCT-001`: further `OrchestratorService` facade reduction
- `TD-STRUCT-002`: retained opening/closeout artifact absorption and pruning
- `TD-STRUCT-003`: deeper semantic-honesty cleanup around scheduler wording
- `TD-STRUCT-004`: removal of remaining `project_delivery`-shaped orchestration assumptions
- `TD-STRUCT-005`: fuller runtime-backed capability health
- `TD-STRUCT-006`: governed promotion path for future platform objects

`M32 Phase 0` is the entry gate that converts those carry-forward debts into a bounded implementation line instead of continuing to accumulate reference material outside the active workflow.

## Scope

This phase includes:

- `M32-0` opening/governance and reference absorption inventory
- `M32-A` interaction contracts and minimum service façade
- `M32-B` public role plus profile contracts
- `M32-C` execution-cluster template contracts
- `M32-D` cluster-aware graph and packet integration
- `M32-E` interaction-first workbench preview

This phase explicitly does not include:

- automation plane
- large provider/capability breadth expansion
- large public role enum expansion
- a second operator/read-model family parallel to the existing packet family
- any new `*_delivery` service special path

## Execution Model

Development for this phase runs through five local worktrees:

- `codex/m32-integration`
- `codex/m32-contracts`
- `codex/m32-runtime-routing`
- `codex/m32-projection-workbench`
- `codex/m32-tests-governance`

Rules:

- `integration` owns phase truth, task cards, merges, and closeout
- `contracts` freezes the public objects before broad implementation parallelism begins
- `runtime-routing`, `projection-workbench`, and `tests-governance` may proceed in parallel only after the relevant contract slice is frozen
- every worktree uses an isolated workspace-scoped DB path
- bug-first is mandatory: if a real workflow/runtime regression appears, repair it before continuing feature scope

## Workstreams

### Workstream 0: Opening And Reference Absorption

- open `M32` formally
- create the task-card pack
- inventory the current dirty reference workspace and classify candidate `M31` carry-forward deltas
- update living docs so the repository truth no longer claims there is no open post-`M31` phase

### Workstream A: Interaction Plane

- add `IntentSession`, `IntentPacket`, `ClarificationState`, `PlanDraft`, `LaunchDecision`, `FollowupRequest`
- add a minimum interaction service façade
- keep interaction state separate from execution truth

### Workstream B: Role / Profile Layer

- keep `planner / coder / researcher / reviewer / operator` as the stable public governance roles
- add `AgentProfileDefinition`, `GeneratedAgentProfile`, and registry support
- express specialists such as `architect` and `verifier` as profiles, not new public role enums

### Workstream C: Execution Cluster Templates

- add `ExecutionClusterTemplate`, `ClusterExecutionPlan`, `ClusterOutputPacket`, `ClusterReviewRubric`, and routing
- define first templates: `DevCluster` and `ResearchCluster`
- absorb the `project_delivery` capability into `DevCluster` rather than grow more service special paths

### Workstream D: Cluster-Aware Runtime Surfaces

- extend graph nodes with `agent_profile_id`, `cluster_template_id`, and `role_label`
- extend goal/operator/replay packet families with cluster-aware fields
- reuse parent/child lineage rather than creating a second execution truth chain

### Workstream E: Workbench Preview

- provide a minimum interaction-first preview surface on top of the existing operator backend
- support intent input, clarification, plan/cluster preview, policy/capability preview, launch, and follow-up
- keep workbench preview separate from operator console semantics

## Entry Criteria

To remain in-bounds, the phase must preserve these assumptions:

- accepted `M31 Phase 0` remains the last completed freeze baseline
- the dirty primary workspace is reference-only, not execution truth
- `project_delivery` compatibility must remain intact while `TD-STRUCT-004` is repaid
- no automation-plane behavior is introduced under interaction-plane naming

## Exit Criteria

The phase is complete only when:

- `M32` phase docs and task cards are fully updated with actual outcomes
- interaction contracts are live through minimum CLI/API/service surfaces
- public role plus profile layering is implemented
- at least `DevCluster` and `ResearchCluster` exist as templates
- goal/operator/replay packet families are cluster-aware
- a minimum workbench preview can launch a cluster-aware path
- targeted tests and workflow dogfood pass without unresolved regressions

## Evidence Expectations

Closeout for this phase must include:

- task-card status with actual results
- targeted contract/service/API/UI validation
- workflow dogfood through `project_delivery`, `guarded_project_delivery`, and `DevCluster`
- explicit note of any carried debt that remains open after `M32 Phase 0`
