# M32 Backup Branch Absorption Review

Date: 2026-04-22  
Compared sources:
- dirty backup worktree: `D:\Universal Agentic workflow` on `codex/main-pre-m32-20260422`
- clean main baseline: `D:\uawo-main` at `ae26ad3`

## Purpose

Classify the preserved pre-merge backup changes after `M32` landed on `main`, so the repository can keep only deltas that still add value and avoid re-absorbing older or weaker variants of the new baseline.

## Absorb

- `tests/test_runtime_boundary.py`
  Added a missing regression that proves `CapabilityPlane` degrades honestly when the optional MCP dependency is unavailable.
- `tests/test_scheduler_authority_api.py`
  Added a missing API regression that checks `/healthz` and `/authority/cluster` report `authority_mode=single_store_quorum` honestly.
- `docs/reviews/m20-freeze-review.md`
  Corrected lingering `majority-quorum` wording so the historical freeze review matches the accepted semantic-honesty baseline.

## Absorb With Reshape

- `NEXT_DEVELOPMENT_PLAN.md`
  Keep only as archival planning input or fold into later roadmap material; it should not become a parallel active truth beside the current `M32` phase doc and task cards.
- `LOCAL_WORKTREE_WORKFLOW_PARALLEL_PLAN.md`
  The operating model is still useful, but it should be merged into living workflow guidance with the actual worktree names and rules that were used.
- `领域特化_Agent_集群架构说明与开发方案_重新导出.md`
  Keep as an archived source idea document only if we want provenance for the cluster direction; its actionable content is already represented in the M32 interaction/profile/cluster foundation.
- `README.md`
  Some pruning and wording cleanup may still be worth harvesting, but only without regressing the now-correct `M32 Phase 0` active-state language.
- `docs/current_development_workflow.md`
  A few cleanup lines may still be useful, but only if folded into the active `M32` governance guide instead of reintroducing stale `M31` framing.
- `tests/test_api.py`
  There is a small amount of useful execution-state coverage around `role_progress` and `parallel_batch`, but it must be re-added as a new additive test rather than replacing the stronger interaction/cluster coverage already in `main`.

## Drop

- Older or weaker code variants already superseded by `M32`
  `packages/contracts/__init__.py`, `packages/contracts/models.py`, `packages/core_domain/orchestration_engine.py`, `packages/core_domain/service_memory_simulation.py`, `packages/core_domain/service_projection.py`, `packages/core_domain/services.py`
- Exact-match files already absorbed into `main`
  `apps/scheduler_authority_api/main.py`, `packages/core_domain/capability_plane.py`, `packages/core_domain/config.py`, `packages/core_domain/governance.py`, `packages/core_domain/resolver.py`, `packages/core_domain/scheduler_authority.py`, `packages/core_domain/service_lifecycle.py`, `pyproject.toml`, `tests/test_repositories.py`, `packages/core_domain/service_audit_replay.py`, `packages/core_domain/service_ownership_lease.py`, `packages/core_domain/service_review_policy.py`, `packages/core_domain/service_run_lifecycle.py`
- Weaker or redundant test variants
  `tests/test_cli.py`, `tests/test_contracts.py`, `tests/test_execution_loop.py`, `tests/test_governance.py`
- Closed-phase or duplicate archival material that should not be re-promoted into current truth
  `DOMAIN_CLUSTER_EVALUATION.md`, `docs/reviews/m31-architecture-evaluation-r2.md`, `docs/reviews/m31-boundary-contraction-freeze-review.md`, `docs/reviews/m31-services-audit.md`, `docs/task_cards/m31_phase_0_task_cards.md`, `docs/task_cards/m31_phase_0/`, `docs/vision/platform_architecture_blueprint.md`, `m31_phase_docs/phase_0_boundary_contraction_and_semantic_honesty.md`

## Recommended Next Actions

1. Keep the backup worktree as reference only until any desired roadmap/workflow wording is harvested.
2. If we want to preserve long-horizon planning provenance, move the cluster/worktree planning docs into an explicit archive area instead of restoring them at the repository root.
3. If we want one more low-risk follow-up from the backup branch, add a new additive API regression for `role_progress` and `parallel_batch` without weakening the current interaction/cluster suite.
