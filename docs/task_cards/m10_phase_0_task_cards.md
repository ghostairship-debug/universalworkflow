# M10 Phase 0 Task Cards

**Phase:** `M10 Phase 0 - Post-M9 Rebaseline And Scope Freeze`  
**Status:** Complete

This is a complex phase. Every task below has a standalone detailed card.

## Reassessment

- `M9` is complete and the next approved work is a post-`M9` rebaseline, not immediate distributed-ownership or concurrency implementation.
- The current repository already ships local-first claim, worker-lease, runtime-attempt, reconcile, replay, and governance surfaces.
- The only remaining cross-milestone open debts are `TD-001` and `TD-009`.
- The main `M10 Phase 0` question is not "how much concurrency can `M10` do", but "what ownership boundary must be frozen first so later concurrency work is still compatible with the current local-first control plane".

## Phase Outcome

- `M10-0A` completed a repository-grounded ownership / lease / attempt / reconcile baseline inventory and confirmed that the shipped surface is already substantial but still local-only.
- `M10-0B` completed the debt clustering and confirmed the entry order `Theme A -> Theme B -> Theme C`.
- `M10-0C` froze the first approved feature-bearing slice as ownership topology and claim-domain hardening on the current local-first control plane.
- `M10-0D` closed the phase with an explicit review record and a fresh `check_doc_links` pass.
- No future `M10` task-card pack was generated during this phase.

## Task Cards

| ID | Complexity | Goal | Depends On | Read Scope | Write Scope | Verification | Exit Signal | Doc Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `M10-0A` | `complex` | Build an explicit post-`M9` baseline inventory for ownership, lease, attempt, and concurrency-related repository semantics | `Phase entry` | `README.md`, `docs/current_development_workflow.md`, `docs/reviews/m9-freeze-review.md`, `docs/tech-debt-registry.md`, `packages/core_domain/*`, `packages/contracts/runtime.py`, `tests/*` | `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`, `docs/task_cards/m10_phase_0_task_cards.md` | documentation audit | the phase doc cites concrete post-`M9` ownership/concurrency facts rather than generic distributed-systems language | [M10-0A](m10_phase_0/M10-0A_post_m9_ownership_and_concurrency_baseline_inventory.md) |
| `M10-0B` | `complex` | Cluster `TD-001` and `TD-009` into candidate `M10` slices and rank them by dependency order, blast radius, and validation readiness | `M10-0A` | `docs/tech-debt-registry.md`, `docs/governance/tech_debt_registry.json`, `docs/task_cards/m2_phase_1_task_cards.md`, `docs/task_cards/m2_phase_4_task_cards.md`, `docs/task_cards/m2_phase_5_task_cards.md`, `packages/core_domain/governance.py`, `tests/test_governance.py` | `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`, `docs/task_cards/m10_phase_0_task_cards.md` | documentation audit | one ordered candidate matrix exists for ownership topology, barrier/parallel semantics, and external worker-pool ambition | [M10-0B](m10_phase_0/M10-0B_open_debt_clustering_and_entry_order.md) |
| `M10-0C` | `complex` | Freeze the first approved `M10` slice, explicit non-goals, and the early-`M10` local-first control-plane guardrails | `M10-0A`, `M10-0B` | `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`, `docs/reviews/m9-freeze-review.md`, `docs/adrs/ADR-005.md`, `docs/adrs/ADR-M8-009.md`, `README.md` | `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`, `docs/task_cards/m10_phase_0_task_cards.md` | documentation audit | the next feature-bearing phase is frozen without auto-approving full hosted or multi-node scheduling breadth | [M10-0C](m10_phase_0/M10-0C_first_slice_scope_freeze_and_non_goals.md) |
| `M10-0D` | `medium` | Normalize current-phase closeout expectations, verification hooks, and the no-pre-generation rule for future phase task-card packs | `M10-0C` | `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`, `docs/task_cards/m10_phase_0_task_cards.md`, `docs/task_cards/m1_execution_loop_protocol.md`, `docs/documentation_governance.md` | active phase docs only | documentation audit + `python -m infra.scripts.check_doc_links` | the current phase pack is execution-ready and future `M10` task-card packs remain unopened | [M10-0D](m10_phase_0/M10-0D_phase_closeout_expectations_and_verification_hooks.md) |

## Execution Notes

### `M10-0A`

- Record the current ownership and concurrency baseline separately from future ambition.
- Explicitly capture which current surfaces are already repository-owned and which semantics are still only local.
- Do not turn the inventory into a future implementation proposal too early.

### `M10-0B`

- Group the two remaining open debts into a small number of candidate implementation slices rather than treating them as one giant `M10` bucket.
- Rank slices by dependency order and blast radius.
- Do not silently assume that "distributed ownership" means immediate hosted multi-node scheduling.

### `M10-0C`

- Freeze one first feature-bearing `M10` slice and an explicit deferred set.
- Preserve the local-first control-plane baseline and do not weaken the `M8` promotion rules.
- Do not let early `M10` silently expand into a full external scheduler or generic role-system rewrite.

### `M10-0D`

- Keep closeout duties, living-doc touchpoints, and verification hooks explicit.
- Reassert that only the active phase owns a task-card pack.

## Frozen Candidate Ordering

1. Theme A: ownership topology and coordination semantics
2. Theme B: barrier and parallel execution semantics
3. Theme C: true external worker pools or multi-node scheduling ambition

This ordering is now the frozen `M10 Phase 0` result.

## Frozen Early-M10 Boundary

- first approved feature-bearing slice: ownership topology and claim-domain hardening on the current local-first control plane
- not yet approved in Phase 0:
  - full hosted scheduler breadth
  - default promotion of `M8` experimental lanes
  - generic multi-agent role-system modeling

## Gate Checklist

- `M10-0A`, `M10-0B`, and `M10-0C` produce a repository-grounded `M10` freeze decision.
- The phase doc states a concrete first `M10` slice and concrete non-goals.
- The pack preserves the local-first canonical lane and the current feature-flag promotion rules.
- No future `M10` task-card pack is generated before its phase becomes active.

## Closeout Result

- Updated the phase doc, current phase index, detailed task cards, and the phase review.
- Re-ran `python -m infra.scripts.check_doc_links` after the doc-pack changes and it passed.
- Closed `M10 Phase 0` without opening the `M10 Phase 1` task-card pack yet.

## Verification Result

- `python -m pytest tests/test_execution_loop.py tests/test_cli.py tests/test_api.py -q -k "claim or lease or reconcile or repair or attempt"` -> `44 passed, 141 deselected`
- `python -m pytest tests/test_runtime_boundary.py -q` -> `4 passed`
- `python -m infra.scripts.check_doc_links` -> `passed=true`
