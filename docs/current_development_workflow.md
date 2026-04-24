# Current Development Workflow

This document is the canonical living guide for what the repository should do next and how work should be executed.

## 1. Authoritative Current-State Sources

Use these in priority order when deciding what is current:

1. [docs/reviews/m37-generated-roles-and-automation-plane-freeze-review.md](reviews/m37-generated-roles-and-automation-plane-freeze-review.md)
2. [docs/reviews/m36-natural-language-workbench-v1-freeze-review.md](reviews/m36-natural-language-workbench-v1-freeze-review.md)
3. [docs/tech-debt-registry.md](tech-debt-registry.md)
4. [README.md](../README.md)
5. [m37_phase_docs/phase_2_automation_controller_watchdog_and_closeout.md](../m37_phase_docs/phase_2_automation_controller_watchdog_and_closeout.md)
6. [docs/task_cards/m37_phase_2_task_cards.md](task_cards/m37_phase_2_task_cards.md)
7. [docs/reviews/m36-workbench-ia-capability-slot-freeze-review.md](reviews/m36-workbench-ia-capability-slot-freeze-review.md)
8. [docs/reviews/m35-role-execution-productization-freeze-review.md](reviews/m35-role-execution-productization-freeze-review.md)

The repository has accepted `M37` and currently has no open post-`M37` bounded phase.

Archived planning context from the pre-merge backup workspace is summarized in [docs/reviews/m32-archived-planning-inputs.md](reviews/m32-archived-planning-inputs.md). Treat it as reference-only, not as parallel execution truth.

The rebuilt post-`M34` roadmap is summarized in [POST_M34_MULTIPHASE_ROADMAP.md](../POST_M34_MULTIPHASE_ROADMAP.md). Treat it as reference-only until the next bounded phase opens.

## 2. Current Repository Position

The repository has now completed:

- `M8` through `M30`
- accepted `M31 Phase 0`
- accepted `M32 Phase 0`
- accepted `M33 Phase 0`
- accepted `M34 Phase 0`
- accepted `M35`
- accepted `M36`
- accepted `M37`

Current status:

- the mainline product remains `v1 core complete`
- the latest accepted freeze is `M37 Generated Roles And Automation Plane`
- there is no currently active bounded phase
- the built-in Web UI now includes a usable natural-language workbench v1
- interaction sessions now keep persistent follow-up queues
- generated roles now exist as governed generated profiles scoped to existing sessions and runs
- automation now exists as a bounded watchdog/controller line with explicit review-gated high-risk actions
- `TD-STRUCT-001` and `TD-STRUCT-003` remain partially repaid carry-forward debt
- `TD-STRUCT-005` remains deferred and is aligned mainly to `M38-M39`
- `TD-STRUCT-006` remains deferred and is aligned mainly to `M39`
- broader capability-ecosystem productization, eval/promotion, and design-grade multimodal validation remain later work

## 3. What Must Happen Next

The next honest step is to open `M38 Phase 0` only after its phase doc and task-card pack exist.

The repository should proceed by:

1. treating accepted [docs/reviews/m37-generated-roles-and-automation-plane-freeze-review.md](reviews/m37-generated-roles-and-automation-plane-freeze-review.md) as the latest completed bounded baseline
2. keeping the retained `M36` and `M37` phase materials as closeout evidence rather than active execution truth
3. opening `M38 Phase 0` only after writing its phase doc, task-card index, and detailed cards
4. continuing bug-first: repair real workflow/runtime regressions before continuing new scope
5. preserving the additive `execution_profile` family, interaction-session family, generated-profile family, and bounded watchdog semantics shipped through accepted `M35-M37`
6. keeping high-risk automation and promotion behavior review-gated and auditable
7. continuing to defer broad `MMX CLI`, `gcloud` / Vertex AI, `TD-STRUCT-005`, and `TD-STRUCT-006` breadth until a later bounded phase says otherwise

## 4. Task-Card Protocol

The repository continues to use the task-card protocol for every new active phase:

1. write the current phase doc first
2. write the current phase task-card index
3. write the current phase detailed task cards
4. execute only after the detailed cards exist
5. update cards with actual results while implementing
6. close the phase with tests, review, and living-doc updates

Rules:

- generate task cards only for the current active phase
- do not pre-generate future phase task-card packs
- closed task-card packs are not retained by default; once their conclusions are absorbed into freeze reviews and integrated roadmaps, prefer pruning them
- complex phases require standalone detailed cards for every task
- every mutating workflow run should still carry bounded mutation contracts, read/write scope, and explicit tests
- every completed card should record real workflow evidence back into the card or accepted review bundle

## 5. Collaboration Mode

Default collaboration remains:

- architecture, high-risk semantics, and final release decisions are human-led
- workflow is used as the bounded execution engine, validation surface, and audit/replay control plane
- generated profiles and automation watchdogs stay additive and governed
- bug-first always applies

## 6. Minimal Documentation Rule

Keep the working tree small.

- prefer keeping only the latest accepted freeze review, current README, current workflow guide, living debt registry, and any currently active phase materials as the active truth set
- if useful long-horizon planning rationale must be retained, collapse it into one clearly non-authoritative roadmap or archive note instead of restoring multiple competing plans
- treat older plans, phase docs, task-card packs, and historical review bundles as disposable once their conclusions are absorbed

## 7. What Counts As Done

### Task done

- code or documentation delta is implemented
- declared tests pass
- task-card status is updated
- any promised evidence is recorded

### Phase done

- every task card in the active phase is complete
- phase-level verification passes
- phase review or equivalent closeout is written

### Milestone done

- freeze review exists
- living docs are updated
- debt implications are recorded
- the repository can state what is complete and what remains deferred

## 8. Current One-Line Instruction

Treat accepted `M37` as the latest completed bounded baseline, keep no post-`M37` phase active until the next phase doc and task-card pack exist, and open `M38+` breadth only through the task-card protocol.
