# M35-0A Phase Opening And Workflow Orchestration Freeze

Status: completed

## Goal

Open `M35 Phase 0` formally and freeze the workflow-driven execution model that the repository will use for the rest of `M35`.

## Acceptance

- add the `M35` phase doc
- add the `M35` task-card index and detailed cards
- update the current workflow guide so `M35 Phase 0` is the active bounded phase
- update README and the root planning docs so repository truth points at an active `M35`
- record the repaired governance-report regressions and no-behavior-change `APIRouter` split as absorbed pre-open work, not active `M35` scope
- update the technical debt registry so `TD-STRUCT-005` and `TD-STRUCT-006` remain explicitly deferred and the remaining open-debt repayment labels are no longer left at the generic post-`M34` placeholder
- freeze the default workflow-orchestration model for `M35`: workspace-scoped DB, interaction-session kickoff, task-card-to-run mapping, explicit mutation contracts, explicit review gates, and evidence writeback

## Notes

- do not start `M35 Phase 1` implementation work under `M35-0A`
- do not generate `M35 Phase 1` or `M35 Phase 2` task-card packs yet
- workflow remains the bounded execution and evidence plane; final milestone judgment remains human-led

## Result

- opened `M35 Phase 0` formally through the phase doc and task-card pack
- updated the workflow guide, README, root roadmap pointer, and rebuilt roadmap so the repository now points at an active post-`M34` bounded phase
- recorded the pre-open governance-report fix and `APIRouter` split as already completed pre-open work
- updated the technical debt registry so `TD-STRUCT-005` and `TD-STRUCT-006` remain deferred and later repayment labels are more specific than the old generic post-`M34` placeholder
- froze the workflow-driven execution model for the rest of `M35`
