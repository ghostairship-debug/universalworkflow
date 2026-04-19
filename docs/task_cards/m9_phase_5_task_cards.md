# M9 Phase 5 Task Cards

**Phase:** `M9 Phase 5 - Freeze Review And Scope Closure`  
**Status:** Complete

This is a complex phase. Every task below has a standalone detailed card.

## Scope Lock

- close `M9`
- retire debts completed in `M9`
- explicitly defer the high-blast-radius concurrency debts beyond `M9`

## Task Cards

| ID | Complexity | Goal | Depends On | Primary Files | Verification | Exit Signal | Doc Link |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `M9-5A` | `medium` | Write the `M9` freeze review and phase closeout records | `M9 Phase 4 complete` | `docs/reviews/`, `m9_phase_docs/` | document review | `M9` closeout record exists | [M9-5A](m9_phase_5/M9-5A_m9_freeze_review_and_phase_records.md) |
| `M9-5B` | `medium` | Update living docs and debt registry to post-`M9` truth, including explicit rescope of deferred debts | `M9-5A` | `README.md`, `docs/current_development_workflow.md`, `docs/tech-debt-registry.md`, `docs/governance/tech_debt_registry.json`, `infra/validation/doc_hygiene.py` | docs audit + link check | current-state docs match the closed milestone | [M9-5B](m9_phase_5/M9-5B_post_m9_living_docs_and_debt_registry.md) |
| `M9-5C` | `small` | Run final verification and record the green baseline used for the freeze claim | `M9-5A`, `M9-5B` | tests + `docs/reviews/m9-freeze-review.md` | targeted/full verification | milestone can be declared complete | [M9-5C](m9_phase_5/M9-5C_final_verification_and_green_baseline.md) |
