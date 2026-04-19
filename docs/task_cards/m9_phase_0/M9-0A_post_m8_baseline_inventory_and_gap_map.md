# M9-0A - Post-M8 Baseline Inventory And Gap Map

- Task ID: `M9-0A`
- Phase: `M9 Phase 0 - Post-M8 Rebaseline And Scope Freeze`
- Status: `verified` (retro-documented from the completed `M9` execution)
- Depends On: `Phase entry`

## Goal

- Build a concrete post-`M8` baseline from current repository files, flags, dependencies, and validated proof points.
- Separate shipped baseline facts from roadmap assumptions.

## Out Of Scope

- ranking the `M9` debt themes
- freezing the `M9` milestone sequence
- implementing any new feature-bearing `M9` code

## Read Set

- `README.md`
- `docs/current_development_workflow.md`
- `docs/reviews/m8-freeze-review.md`
- `docs/tech-debt-registry.md`
- `pyproject.toml`
- `packages/core_domain/*`
- `packages/runtime_langgraph/*`
- `apps/*`
- `tests/*`

## Write Set

- Allowed:
  - `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`
  - `docs/task_cards/m9_phase_0_task_cards.md`
- Avoid:
  - runtime code
  - debt-registry status changes
  - later phase docs before the baseline is explicit

## Interfaces And Data Changes

- documentation only
- the phase doc must record:
  - canonical local-first surfaces
  - opt-in post-`M8` pilot surfaces
  - dependency tiers
  - the last validated pre-`M9` baseline

## Invariants

- keep the post-`M8` control plane local-first
- do not rewrite `M8` history to match hoped-for `M9` scope
- do not treat transient worktree edits as shipped truth

## Implementation Steps

1. Read living docs, the `M8` freeze review, and current runtime/package/test anchors.
2. Inventory canonical vs opt-in surfaces, dependency groups, and validation entry points.
3. Write the reassessment section of the phase doc from current repository evidence.
4. Update the phase index so later tasks consume the same baseline language.

## Test Plan

- documentation audit against current files
- later `python -m infra.scripts.check_doc_links`

## Risks And Rollback

- Main risk: the inventory drifts into milestone planning instead of staying factual.
- Roll back by reducing the write set to baseline-only statements before theme ranking starts.

## Completion Evidence

- Actual modified files:
  - `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`
  - `docs/task_cards/m9_phase_0_task_cards.md`
- Validation:
  - documentation audit completed
  - `python -m infra.scripts.check_doc_links` passed during closeout
- Implementation note:
  - this card established the repository-grounded post-`M8` baseline later used by `M9-0B` and `M9-0C`
