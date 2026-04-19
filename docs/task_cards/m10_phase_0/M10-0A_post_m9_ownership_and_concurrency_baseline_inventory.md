# M10-0A - Post-M9 Ownership And Concurrency Baseline Inventory

- Task ID: `M10-0A`
- Phase: `M10 Phase 0 - Post-M9 Rebaseline And Scope Freeze`
- Status: `completed`
- Depends On: `Phase entry`

## Goal

- Build a concrete post-`M9` baseline for claim, worker-lease, runtime-attempt, reconcile, replay, and concurrency-related repository semantics.
- Separate current shipped truth from future distributed-systems ambition.

## Out Of Scope

- ranking `M10` slices
- freezing the first approved feature-bearing phase
- implementing ownership or concurrency code

## Read Set

- `README.md`
- `docs/current_development_workflow.md`
- `docs/reviews/m9-freeze-review.md`
- `docs/tech-debt-registry.md`
- `packages/contracts/runtime.py`
- `packages/core_domain/services.py`
- `packages/core_domain/service_lifecycle.py`
- `packages/core_domain/service_projection.py`
- `packages/core_domain/governance.py`
- `tests/test_execution_loop.py`
- `tests/test_governance.py`

## Write Set

- Allowed:
  - `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`
  - `docs/task_cards/m10_phase_0_task_cards.md`
- Avoid:
  - runtime code
  - debt-registry status changes
  - future phase task-card packs

## Interfaces And Data Changes

- documentation only
- the phase doc must record:
  - current ownership surfaces that already exist
  - current concurrency limits that still exist
  - validation baseline and local-first architectural constraints

## Invariants

- keep the baseline grounded in current repository behavior
- do not relabel local-only semantics as distributed semantics
- do not weaken the current local-first control-plane boundary

## Implementation Steps

1. Read current living docs, the `M9` freeze review, and current ownership/concurrency code anchors.
2. Inventory what claims, leases, attempts, snapshots, replay, inspect, and reconcile already provide.
3. Record explicit local-only limits and control-plane constraints in the phase doc.
4. Update the phase index so later cards consume the same baseline.

## Test Plan

- documentation audit
- later `python -m infra.scripts.check_doc_links`

## Risks And Rollback

- Main risk: the inventory drifts into solutioning or overclaims distributed readiness.
- Roll back by reducing the write set to baseline facts only before `M10-0B` starts ranking slices.

## Completion Evidence

- Actual modified files:
  - `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`
  - `docs/task_cards/m10_phase_0_task_cards.md`
  - `docs/reviews/m10-phase-0-post-m9-rebaseline-and-scope-freeze-review.md`
- Documentation-audit result:
  - confirmed that persisted claim, worker-lease, runtime-attempt, snapshot, projection, and reconcile surfaces already exist in contracts, repositories, services, and tests
  - confirmed that the shipped surface is local-first and coherent, not a placeholder-only design
- Baseline mismatches discovered between docs and code:
  - none that require runtime correction
  - the main clarification was that the open debt is no longer "missing ownership surfaces"; it is "ownership surfaces remain local-only and not yet distributed or barrier-aware"
