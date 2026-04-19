# M9 Phase 0 Task Cards

**Phase:** `M9 Phase 0 - Post-M8 Rebaseline And Scope Freeze`  
**Status:** Completed

This is a complex phase. Every task below has a standalone detailed card.

## Reassessment

- `M8` is complete and the next approved work is a fresh `M9` rebaseline, not automatic feature expansion.
- The current repository already ships a local-first runtime, opt-in external lanes, structured governance sources, and a direct OpenAI dependency baseline aligned to the current runtime path.
- The remaining debt set is still the six-item carry-over cluster from the `M8` freeze review: `TD-001`, `TD-006`, `TD-007`, `TD-008`, `TD-009`, and `TD-010`.
- The main Phase-0 question is not "how much can `M9` do", but "which debt/theme should open `M9` first without losing the post-`M8` control-plane boundary".

## Task Cards

| ID | Complexity | Goal | Depends On | Read Scope | Write Scope | Verification | Exit Signal | Doc Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `M9-0A` | `complex` | Build an explicit post-`M8` baseline inventory from current repo files, flags, dependency metadata, and validated proof points | `Phase entry` | `README.md`, `docs/current_development_workflow.md`, `docs/reviews/m8-freeze-review.md`, `pyproject.toml`, `packages/core_domain/*`, `packages/runtime_langgraph/*`, `apps/*`, `tests/*` | `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`, `docs/task_cards/m9_phase_0_task_cards.md` | documentation audit | the phase doc cites concrete post-`M8` facts instead of generic roadmap language | [M9-0A](m9_phase_0/M9-0A_post_m8_baseline_inventory_and_gap_map.md) |
| `M9-0B` | `complex` | Cluster the open debt set into candidate `M9` themes and rank them by dependency, risk, and validation readiness | `M9-0A` | `docs/tech-debt-registry.md`, `docs/governance/tech_debt_registry.json`, `docs/governance/review_policy_cases.json`, `packages/core_domain/governance.py`, `tests/test_governance.py`, relevant review docs | `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`, `docs/task_cards/m9_phase_0_task_cards.md` | documentation audit | one ordered candidate matrix exists for `TD-001`, `TD-006`, `TD-007`, `TD-008`, `TD-009`, and `TD-010` | [M9-0B](m9_phase_0/M9-0B_open_debt_clustering_and_entry_gate_ranking.md) |
| `M9-0C` | `complex` | Freeze the first approved `M9` slice, the explicit non-goals, and the post-`M8` pilot-promotion guardrails | `M9-0A`, `M9-0B` | `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`, `docs/reviews/m8-freeze-review.md`, `README.md`, `m8_phase_docs/*`, `packages/core_domain/m8_flags.py`, `packages/core_domain/observability.py`, `packages/runtime_langgraph/durable_pilot.py` | `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`, `docs/task_cards/m9_phase_0_task_cards.md` | documentation audit | the next feature-bearing phase is frozen without reopening `M8` or broadening into unconstrained `M9` | [M9-0C](m9_phase_0/M9-0C_first_slice_scope_freeze_and_non_goals.md) |
| `M9-0D` | `medium` | Normalize phase-closeout expectations, living-doc touchpoints, and verification hooks for later execution of the frozen scope | `M9-0C` | `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`, `docs/task_cards/m9_phase_0_task_cards.md`, `docs/current_development_workflow.md`, `docs/documentation_governance.md` | active phase docs only | documentation audit + `python -m infra.scripts.check_doc_links` | the document pack is execution-ready and later closeout duties are explicit | [M9-0D](m9_phase_0/M9-0D_phase_closeout_expectations_and_verification_hooks.md) |

## Execution Notes

### `M9-0A`

- Record the current validated baseline separately from transient worktree state.
- Explicitly capture which post-`M8` surfaces are canonical, which are opt-in pilot paths, and which dependency tiers are base vs optional.
- Do not turn the inventory into a new roadmap or reopen pre-`M8` service-boundary work.

### `M9-0B`

- Group the six open debts into a small number of candidate entry themes instead of treating them as one undifferentiated `M9` bucket.
- Rank the themes by dependency order, blast radius, and validation readiness.
- Do not silently re-scope or retire debt items while performing the ranking.

### `M9-0C`

- Freeze one first feature-bearing `M9` slice and an explicit deferred set.
- Preserve the local-first control-plane baseline and keep borrowed agent, MCP, external trace export, durable pilot, and skill export as opt-in until a later promotion decision.
- Do not let distributed worker ownership or real concurrent scheduling enter the first slice unless the earlier analysis clearly justifies that override.

### `M9-0D`

- Keep closeout duties, living-doc touchpoints, and verification hooks explicit.
- Keep the standalone execution cards aligned with the index rather than treating the index as a substitute for them.

## Default Candidate Ordering To Verify

1. Theme A: `TD-007` + `TD-008` + `TD-010`
2. Theme B: `TD-006`
3. Theme C: `TD-001` + `TD-009`

This ordering is the current planning hypothesis, not an auto-approved result. `M9-0B` and `M9-0C` must confirm or replace it.

## Frozen Milestone Breakdown

- `M9 Phase 1 - Replay Linkage And Metrics Baseline`
- `M9 Phase 2 - Durable Recovery Lineage And Reconciliation`
- `M9 Phase 3 - Governance Metrics And Alerting`
- `M9 Phase 4 - Optional Review Policy Completion`
- `M9 Phase 5 - Freeze Review And Scope Closure`

Frozen out of `M9`:

- `TD-001`
- `TD-009`

## Gate Checklist

- `M9-0A`, `M9-0B`, and `M9-0C` are all completed and reconciled with the phase doc.
- The phase doc states a concrete first `M9` slice and concrete deferred items.
- The pack preserves the local-first canonical lane and opt-in pilot guardrails.
- The next feature-bearing phase can be split into implementation cards without redoing Phase 0.

## Closeout Expectations

- Write a phase review when `M9 Phase 0` actually completes.
- Update living docs only if the frozen next-slice decision changes current roadmap wording or debt scoping.
- Re-run `python -m infra.scripts.check_doc_links` after any doc-pack changes land.

## Closeout

- `M9-0A` completed: the post-`M8` baseline is now explicitly framed around the current local-first control plane, opt-in pilot lanes, and the aligned OpenAI dependency baseline.
- `M9-0B` completed: the six open debts are now grouped into Theme A, Theme B, and Theme C, with Theme A chosen as the first entry slice.
- `M9-0C` completed: `M9` is frozen to Theme A plus Theme B, while Theme C is explicitly deferred beyond the milestone.
- `M9-0D` completed: the milestone now has an execution-ready phase sequence and later closeout expectations.
