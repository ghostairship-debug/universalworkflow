# M32 Interaction / Profile / Cluster Foundation Freeze Review

Date: 2026-04-22  
Status: accepted

## Summary

`M32 Phase 0` is accepted as a bounded closeout. The repository completed the first post-`M31` interaction-first expansion line without opening automation-plane breadth or a second operator/read-model family.

The accepted outcome is:

- first-class interaction-session contracts and minimum service seams
- stable public-role plus profile layering
- first execution-cluster templates
- cluster-aware graph and packet surfaces
- a minimum interaction-first workbench preview
- governed absorption of the dirty primary workspace back into one clean main worktree

This is an accepted phase closeout, not a zero-debt claim. The repository now uses `M32 Phase 0` as its latest accepted bounded baseline and carries the remaining structural debt explicitly into the next bounded phase.

## Landed

- opened and completed the full `M32 Phase 0` phase/task-card pack
- added `IntentSession`, `IntentPacket`, `ClarificationState`, `PlanDraft`, `LaunchDecision`, and `FollowupRequest`
- added `packages/core_domain/service_interaction.py` and minimum interaction CLI/API/service entry points
- added public-role plus profile contracts and registry surfaces
- added `ExecutionClusterTemplate`, `ClusterExecutionPlan`, `ClusterOutputPacket`, `ClusterReviewRubric`, and routing helpers
- defined first execution templates: `DevCluster` and `ResearchCluster`
- extended orchestration graph nodes with `agent_profile_id`, `cluster_template_id`, and `role_label`
- extended goal/operator/replay packet families with cluster-aware fields while preserving one execution truth chain
- shipped a minimum `/ui/workbench` preview on top of the existing operator backend
- absorbed the governed backup-branch deltas that still had value, archived planning rationale, corrected the remaining `M20` scheduler wording, and cleaned the repository back to one primary worktree

## Validation

- `python -m pytest -q` passed with `281 passed`
- `python -m infra.scripts.check_doc_links` passed
- workflow/runtime regression coverage now includes:
  - interaction session create/get/launch and follow-up surfaces
  - `project_delivery` compatibility
  - `guarded_project_delivery` shared graph substrate coverage
  - `DevCluster` packet and execution-path coverage
  - capability-plane degradation honesty when optional MCP support is missing
  - scheduler-authority API honesty for `/healthz` and `/authority/cluster`

## What Is Now True

- `M32 Phase 0` is complete as a bounded interaction/profile/cluster foundation phase
- `M32` is no longer just an opening plan; the foundation objects are now on the accepted mainline
- `project_delivery` compatibility remains intact, but cluster-aware execution is now part of the shipped model
- the repository has returned to one clean primary `main` worktree
- the dirty pre-merge state is retained only through the archival tag `archive/pre-m32-workspace-leftovers-20260422`
- no post-`M32` bounded phase is open yet

## Repaid In M32 Phase 0

- `TD-STRUCT-002`
  - opening-bundle and backup-workspace truth were absorbed into review/archive material
  - the primary workspace was cleaned and the temporary worktree topology was removed from the live tree

## Carried Forward

- `TD-STRUCT-001`: `OrchestratorService` still concentrates too much cross-plane wiring even after additional service seams and interaction extraction
- `TD-STRUCT-003`: scheduler-authority naming still carries legacy internal wording beyond the corrected public semantics
- `TD-STRUCT-004`: orchestration still carries residual `project_delivery`-shaped assumptions despite the new cluster foundation
- `TD-STRUCT-005`: capability health still needs fuller runtime-backed telemetry across provider lanes
- `TD-STRUCT-006`: governed selective promotion exists in review/governance practice, but not yet as a fuller reusable promotion mechanism

## Entry Gate To The Next Phase

The next valid expansion step is an explicitly opened post-`M32` bounded phase.

That phase should start by:

1. using this freeze review as the latest accepted baseline
2. carrying the remaining `TD-STRUCT-*` items forward explicitly
3. deciding whether the next bounded phase remains inside `M32` follow-on repayment or opens under `M33`
4. keeping automation-plane breadth deferred until the next bounded phase is formally opened
