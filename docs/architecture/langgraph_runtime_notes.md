# LangGraph Runtime Notes

This file consolidates the M84-M104 architecture notes. It keeps the important rules in one place so the active docs do not fan out into many small files.

## Authority

`WorkflowGraphState` is a projection and checkpoint envelope, not a new source of truth.

| Layer | Authority | Owns |
| --- | --- | --- |
| Run lifecycle | `RunStatus`, `RuntimeGraphStep`, persisted `RunSnapshot` records | durable run status, pause/resume, terminal state, repair snapshots |
| Execution graph | `OrchestrationPlanGraph` | task nodes, task edges, graph validation payload |
| Pipeline plan | `WorkflowPipeline` | plan-of-plans stage ordering, capability requirements, validation gates, stage evidence paths |
| LangGraph projection | `WorkflowGraphState` | checkpoint payload, transient graph data, replay metadata |

Durable approval, repo mutation, and high-risk automation remain guarded by `OperatorActionReceipt` or `AutomationLease`. Validation commands must use `packages/runtime_security/safe_command_runner.py`.

The key phrase for this contract is: `WorkflowGraphState` is a projection and checkpoint envelope.

## Fit Matrix

Decisions use `keep`, `wrap`, `migrate`, `delete`, and `later`.

| Capability Surface | Decision | Reason |
| --- | --- | --- |
| `OrchestrationPlanGraph` | wrap | Task topology authority stays in workflow; graph consumes a projection. |
| `WorkflowPipeline` | wrap | Stage truth remains workflow-owned. |
| Run lifecycle and `RunSnapshot` | keep | Durable status and snapshots stay in repositories. |
| `cluster_router` | later | It may become subgraphs after route parity and safety evidence. |
| `scheduler_authority` | keep | Lease and fencing rules are control-plane safety. |
| `interaction_catalog` | wrap | Session and UX authority stay with current services. |
| Capability plane | keep | Provider readiness requires provider-specific live proof. |
| Repo mutation | keep | Patch apply remains receipt/lease guarded. |
| Test matrix | wrap | Graph can schedule tests, but commands and requirements stay workflow-owned. |
| Evidence and operator packet | keep | Graph evidence references do not replace operator packets. |
| Worker adapters | wrap | Provider-specific adapters remain execution boundaries. |
| `runtime_langgraph.focused_runtime` | migrate | Reference path for graph node timing and evidence shape. |
| Durable pilot/checkpointer | migrate | Useful for checkpoint and resume, synced to workflow snapshots. |
| `commercial_game_production` | wrap | Real game production must be task-card driven; commercial readiness stays three-layer GO/NO-GO. |
| Legacy `commercial_cocos_game` template | delete | Fixed-template delivery is removed and only a deprecation guard remains. |
| Local game artifact generation | later | Keep only as diagnostic scaffolding until the real worker is implemented. |
| Active truth / governance checks | keep | Active truth gates milestone closeout. |

## Boundary Contract

`WorkflowGraphNodeResult` records status, evidence path, next action, failure class, and `SideEffectLevel`.

Allowed `SideEffectLevel` values are `none`, `artifact_only`, `workspace_write`, `repo_mutation`, and `external_action`.

`HumanApprovalInterrupt` records requested action, scope payload, write set, risk level, receipt requirement, automation lease allowance, and idempotent resume contract. High-risk graph paths must return `side_effect_before_interrupt=false`.

Graph nodes may directly execute only no-side-effect or artifact-only work unless workflow gates approve the next action. Graph nodes cannot mark providers ready; readiness only comes from provider-specific live proof.

The CLI-visible interrupt preview remains `workflowctl graph interrupt-preview`. Commercial game work remains a pressure test until player-visible evidence proves otherwise.

## Checkpoint And Repair

`GraphCheckpointRecord` stores checkpoint id, run id, thread id, node, status, evidence path, graph state path, parent checkpoint id, fork reason, and checkpoint metadata.

`workflowctl graph fork` creates a new checkpoint record that points to the parent. Forking must not overwrite parent evidence or graph state.

`GraphRepairDecision` is advisory:

- completed checkpoints return `no_repair_needed`
- validation failures return `retry_from_checkpoint` with `next_node=validate`
- exhausted fix iterations return `request_human_review`

Repair decisions do not directly mutate the repository.

## Cluster To Subgraph

The old `cluster_router` maps to LangGraph subgraphs only after safety and route evidence.

| Cluster Surface | Candidate Mapping | Decision |
| --- | --- | --- |
| cluster template selection | graph entry router | wrap |
| cluster member roles | planner/implementer/reviewer/validator/evidence nodes | migrate |
| cluster handoff packet | node input/output envelope | wrap |
| review rubric | reviewer/validator graph nodes | migrate |
| provider/model routing | external workflow authority | keep |
| write-set ownership | conflict guard before execution | keep |
| failure classification | graph node result plus workflow taxonomy | migrate |

The route mapping keeps `readiness_claim=unchanged`. Duplicate write sets return `write_set_conflict`. The multi-agent smoke command remains `workflowctl graph multi-agent-run`.

## Cocos Pressure Test

`commercial_game_production` replaces the old fixed-template `commercial_cocos_game` delivery path.

The old `commercial_cocos_game` entry now blocks with `legacy_cocos_template_removed`. Low-level `cocos_graph_pressure_test`, scaffold, and E2E utilities remain diagnostic evidence only; they cannot deliver or prove a commercial game.

Readiness remains layered:

- `technical_smoke_go`
- `production_scaffold_go`
- `commercial_playable_go`

Missing player-visible UI, mobile, audio, level, skin, or gallery evidence defaults to `commercial_playable_go=false`.
