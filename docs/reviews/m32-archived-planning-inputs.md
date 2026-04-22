# M32 Archived Planning Inputs

Date: 2026-04-22  
Status: reference-only  
Source worktree: `D:\Universal Agentic workflow` on `codex/main-pre-m32-20260422`

## Purpose

This document preserves the useful planning direction from the pre-merge backup workspace without restoring those root-level files as active truth.

It exists so the repository can keep the roadmap and execution rationale that helped shape `M32`, while still treating the accepted freeze reviews, living workflow guide, and debt registry as the authoritative sources.

## Source Documents

The preserved material came primarily from:

- `NEXT_DEVELOPMENT_PLAN.md`
- `LOCAL_WORKTREE_WORKFLOW_PARALLEL_PLAN.md`
- the archived domain-specialized cluster proposal exported from the pre-merge workspace

Those files remain part of the backup workspace history and should not be restored to the repository root as parallel planning truth.

## Preserved Decisions

### 1. Interaction Before Automation

The post-`M31` expansion line should remain interaction-first:

- stabilize interaction/session/launch surfaces first
- keep automation-plane breadth deferred
- avoid opening later product planes until the active bounded phase closes honestly

This is already reflected in the accepted `M32 Phase 0` closeout and remains the correct sequencing rule.

### 2. Public Role + Profile + Cluster Direction

The planning inputs converged on the same role-system conclusion:

- keep the platform-level public roles small and stable
- represent specialized or temporary roles through profiles rather than a large enum explosion
- promote multi-role domain execution through `ExecutionClusterTemplate` rather than new `*_delivery` service special cases

The key preserved principles are:

- public governance roles remain stable and operator-friendly
- specialized roles should be profile-driven
- temporary roles should be generated-profile driven
- execution-domain clusters must stay distinct from scheduler-authority cluster semantics

### 3. First Cluster Template Scope

The useful preserved cluster direction is:

- `DevCluster` and `ResearchCluster` are the right first templates
- cluster packet/output concepts should extend the existing packet family instead of replacing it
- cluster routing should stay bounded and only apply where the extra orchestration complexity is justified

The backup planning inputs were especially helpful in reinforcing that cluster support should be introduced through governed contracts and packet extensions rather than ad hoc orchestration branching.

### 4. Local Worktree + Workflow Two-Level Execution Model

The preserved execution model remains useful for future high-risk development:

- use separate local `git worktree` lanes for isolation
- use independent workspace-scoped databases per worktree
- use workflow inside each lane for bounded parallel execution and validation
- keep one integration lane responsible for final convergence
- keep bug-first above feature expansion

In short:

- `worktree` isolation handles cross-lane safety
- workflow parallelism handles within-lane execution speed

### 5. Controlled Promotion From Future Bundles

The planning inputs also reinforced the right stance toward future ZIP or bundle material:

- promote only the pieces that match active debt repayment and bounded phase scope
- do not bulk-import future platform objects into the live contract surface
- keep promotion governed by explicit repayment and compatibility checks

This remains the correct interpretation of `TD-STRUCT-006`.

## Operational Notes From The Actual M32 Execution

The live `M32` implementation confirmed a few execution rules from the planning inputs:

- a dirty primary workspace should be treated as reference-only during high-risk self-modification
- a clean integration or main worktree should carry the actual merge candidate
- bounded lane worktrees are practical for contracts, runtime/routing, projection/workbench, tests/governance, and integration
- regression and workflow dogfood should be used as merge gates, not as afterthought validation

## What Was Intentionally Not Promoted

The following ideas remain intentionally non-authoritative:

- restoring `NEXT_DEVELOPMENT_PLAN.md` at the repository root as a second master plan
- restoring closed `M31` phase/task-card packs as active guidance
- promoting vision/reference material from later bundles without explicit bounded-phase justification
- using the old planning files to override the accepted `M32` freeze review, living workflow guide, or debt registry

## Relationship To Active Truth

Use this document only for historical planning context and future roadmap recall.

For current repository truth, continue to use:

1. `docs/reviews/m32-interaction-profile-cluster-foundation-freeze-review.md`
2. `docs/current_development_workflow.md`
3. accepted freeze reviews
4. `docs/tech-debt-registry.md`
