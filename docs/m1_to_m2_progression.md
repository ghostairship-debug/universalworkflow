# M1 -> M1.5 -> M2 Progression Note

## Purpose

This note normalizes milestone naming across the repository so that `M1`, `M1.5`, and `M2` are read consistently.

## Canonical Sequence

1. `M1 Phase 0` to `M1 Phase 4`
   These phases establish the run-centric lifecycle, public compile/recompile/resume surfaces, minimal human review loop, operator diagnostics, and the `M1` freeze checkpoint.
2. `M1 legacy hardening uplift`
   This is the dedicated legacy-reference batch documented in [docs/m1_legacy_reference_uplift_plan.md](/D:/Universal%20Agentic%20workflow/docs/m1_legacy_reference_uplift_plan.md:1). It implements the three uplift batches that strengthen the current `M1` spine:
   - explicit run/runtime transition matrix
   - review semantics and test matrix
   - operator-facing `status-detail` plus read-only `inspection`
3. `M1.5`
   This is the post-freeze hardening stage that repays `TD-005` through second-executor enablement and capability routing. The implementation lives in [m1_phase_docs/phase_5_second_executor_and_capability_routing.md](/D:/Universal%20Agentic%20workflow/m1_phase_docs/phase_5_second_executor_and_capability_routing.md:1). The file path keeps the historical `phase_5` naming for continuity, but the milestone should be read as `M1.5`.
4. `M2`
   `M2` starts only after `M1.5` is complete and `TD-005` is repaid.

## Scope Boundaries

- `docs/reviews/m1-freeze-review.md` covers only `M1 Phase 0` to `M1 Phase 4`.
- `docs/m1_legacy_reference_uplift_plan.md` covers the dedicated `M1` legacy hardening batch; it is not the definition of `M1.5`.
- `M1.5` is post-`M1` hardening focused on execution-boundary realism and adapter routing.
- `M2` should never be described as starting directly after the `M1` freeze review; it starts after `M1.5`.

## Reading Guide

- If a document says `M1 Phase 5`, interpret it as `M1.5` unless it is explicitly talking about a file path.
- If a document discusses the three uplift batches `Phase A/B/C`, it is referring to the dedicated `M1 legacy hardening uplift`, not `M1.5`.
- If a document says `M2 Phase 0` starts after the second executor work closes `TD-005`, that prerequisite is `M1.5`.
