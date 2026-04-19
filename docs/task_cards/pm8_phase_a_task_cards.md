# Pre-M8 Phase A Task Cards

**Phase:** `Pre-M8 Phase A - Trust Recovery And Scope Freeze`  
**Goal:** Turn the approved pre-`M8` hardening gate into a real phase/task execution series and restore trust in the repository's current-state documentation before runtime hardening begins.

## Task Cards

| Task | Size | Goal | Depends On | Primary Files | Verification | Done When |
| --- | --- | --- | --- | --- | --- | --- |
| `PM8-A1` | `medium` | Write the hardening boundary and current baseline inventory | `Phase A entry` | `pm8_phase_docs/phase_a_trust_recovery_and_scope_freeze.md`, `docs/architecture/pre_m8_hardening_boundary.md` | documentation audit | the pre-`M8` boundary, evidence sources, and non-goals are explicit |
| `PM8-A2` | `medium` | Define trustworthy current-status/reporting rules and align living docs | `PM8-A1` | `README.md`, `docs/current_development_workflow.md`, `docs/documentation_governance.md` | documentation audit | current-state language distinguishes validated baseline from active worktree reality |
| `PM8-A3` | `medium` | Define portable-link policy and current/review/archive/reference doc taxonomy | `PM8-A1` | `docs/documentation_governance.md`, `README.md`, `docs/current_development_workflow.md` | documentation audit | new living docs have a clear portability rule and doc-category taxonomy |
| `PM8-A4` | `medium` | Specify clean source-package/export flow and worktree hygiene gate | `PM8-A1`, `PM8-A2`, `PM8-A3` | `docs/source_package_export_policy.md`, `docs/documentation_governance.md`, `docs/reviews/pm8-phase-a-trust-recovery-review.md` | documentation audit | future handoff/export expectations are explicit and phase-closeout records them |

## Closeout

- `PM8-A1` completed: the pre-`M8` hardening boundary, baseline evidence sources, and out-of-scope lines are now written in a dedicated architecture doc and mirrored in the phase doc.
- `PM8-A2` completed: living docs now describe current repository status in a trust-preserving way and point to the next approved phase rather than implying open-ended feature continuation.
- `PM8-A3` completed: portable-link rules and doc taxonomy are now explicit for living docs, while historical docs remain historical rather than being retrofitted as if they were current-state sources.
- `PM8-A4` completed: clean source-package/export expectations and worktree hygiene rules now exist as a written gate for later hardening and freeze work.
