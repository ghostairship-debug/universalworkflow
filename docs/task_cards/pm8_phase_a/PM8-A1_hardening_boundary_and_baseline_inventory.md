# PM8-A1 - Hardening Boundary And Baseline Inventory

**Phase:** `Pre-M8 Phase A - Trust Recovery And Scope Freeze`  
**Status:** Completed

## Goal

Make the pre-`M8` hardening boundary explicit so later phases can tell what is baseline truth, what is in scope for hardening, and what is still deferred.

## Deliverables

- phase doc opened under `pm8_phase_docs/`
- baseline inventory recorded in `docs/architecture/pre_m8_hardening_boundary.md`
- explicit in-scope / out-of-scope split for the whole pre-`M8` gate

## Notes

- This task is documentation-governance only.
- It should not sneak feature work into the branch.
- It should capture the difference between the validated `M7` baseline and the currently in-progress worktree.

## Verification

- documentation audit

## Outcome

- Added a dedicated pre-`M8` hardening boundary document.
- Recorded the baseline evidence sources and the non-goals that stay deferred until after the hardening gate.
