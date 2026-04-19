# PM8-A4 - Source Package Export And Worktree Hygiene Gate

**Phase:** `Pre-M8 Phase A - Trust Recovery And Scope Freeze`  
**Status:** Completed

## Goal

Define what a trustworthy source-package/handoff bundle should include and what worktree conditions must be true before a freeze or external handoff claims the repository is clean.

## Deliverables

- `docs/source_package_export_policy.md`
- closeout note in the phase review documenting that the policy now exists

## Notes

- This task defines the rules only; it does not yet automate export generation.
- The rules must exclude local DBs, artifacts, caches, and machine-specific noise.
- The rules must also allow explicitly documented exceptions for evaluator-supplied or review-supplied files.

## Verification

- documentation audit

## Outcome

- The repository now has an explicit clean source-package/export policy and a written worktree hygiene gate for later freeze work.
