# Current Development Workflow

This document is the canonical living guide for what the repository should do next and how work should be executed.

## 1. Authoritative Current-State Sources

Use these in priority order when deciding what is current:

1. [docs/reviews/m34-facade-reduction-and-authority-interior-cleanup-freeze-review.md](reviews/m34-facade-reduction-and-authority-interior-cleanup-freeze-review.md)
2. [docs/tech-debt-registry.md](tech-debt-registry.md)
3. [README.md](../README.md)
4. [m34_phase_docs/phase_0_facade_reduction_and_authority_interior_cleanup.md](../m34_phase_docs/phase_0_facade_reduction_and_authority_interior_cleanup.md)
5. [docs/task_cards/m34_phase_0_task_cards.md](task_cards/m34_phase_0_task_cards.md)
6. [docs/reviews/m33-orchestration-service-contraction-freeze-review.md](reviews/m33-orchestration-service-contraction-freeze-review.md)
7. [docs/reviews/m32-interaction-profile-cluster-foundation-freeze-review.md](reviews/m32-interaction-profile-cluster-foundation-freeze-review.md)
8. [docs/reviews/m31-boundary-contraction-freeze-review.md](reviews/m31-boundary-contraction-freeze-review.md)
9. [docs/reviews/m30-operator-control-freeze-review.md](reviews/m30-operator-control-freeze-review.md)
10. [docs/reviews/m20-freeze-review.md](reviews/m20-freeze-review.md)

The repository has now accepted `M34 Phase 0`. No post-`M34` bounded phase is open yet.

Archived planning context from the pre-merge backup workspace is summarized in [docs/reviews/m32-archived-planning-inputs.md](reviews/m32-archived-planning-inputs.md). Treat it as reference-only, not as parallel execution truth.

The rebuilt post-`M34` roadmap is summarized in [POST_M34_MULTIPHASE_ROADMAP.md](../POST_M34_MULTIPHASE_ROADMAP.md). Treat it as reference-only until the next bounded phase is formally opened.

## 2. Current Repository Position

The repository has now completed:

- `M8` through `M20`
- `M21` through `M30`
- accepted `M31 Phase 0`
- accepted `M32 Phase 0`
- accepted `M33 Phase 0`
- accepted `M34 Phase 0`
- the runtime, governance, orchestration, Web operator UI, remote worker productization, repo-mutation baseline, single-store quorum-style scheduler-authority closure, interaction/profile/cluster foundation, and the first shared orchestration/service contraction line
- a second bounded scheduler-authority/service honesty cleanup line
- retirement of `TD-021`

Current status:

- the mainline product is `v1 core complete`
- the latest accepted freeze is `M34 Facade Reduction / Authority Interior Cleanup Freeze`
- no post-`M34` bounded phase is open yet
- `TD-STRUCT-001` and `TD-STRUCT-003` remain partially repaid and carried forward
- `TD-STRUCT-005` and `TD-STRUCT-006` remain deferred to a post-`M34` bounded follow-on
- `TD-STRUCT-004` remains repaid in accepted `M33 Phase 0`
- the latest accepted foundation is interaction-first, role-profile-aware, and cluster-aware, with a shared orchestration-plan builder for the shipped multi-role presets
- automation-plane breadth remains deferred
- the built-in Web UI and TUI remain operator surfaces rather than chat-style natural-language workbenches
- natural-language goal planning and launch exist today through CLI/API plus the minimum workbench preview, not through a front-end conversational shell
- the rebuilt post-`M34` roadmap restores a meaningful multi-phase shape for future product milestones, but it is not active execution truth yet
- a known pre-open bug-first gate remains: the current governance tech-debt report expectations need to be repaired before `M35` opens

## 3. What Must Happen Next

The next step is to clear the known pre-open gate and then open the next bounded post-`M34` phase before resuming later breadth work.

The repository should proceed by:

1. treating accepted [docs/reviews/m34-facade-reduction-and-authority-interior-cleanup-freeze-review.md](reviews/m34-facade-reduction-and-authority-interior-cleanup-freeze-review.md) as the latest completed bounded baseline
2. repairing the known governance tech-debt report regressions before opening `M35`
3. opening the next bounded phase explicitly before resuming new structural or breadth work
4. executing bug-first: repair real workflow/runtime regressions before continuing new scope
5. using [docs/tech-debt-registry.md](tech-debt-registry.md) together with [POST_M34_MULTIPHASE_ROADMAP.md](../POST_M34_MULTIPHASE_ROADMAP.md) to choose the next bounded product milestone honestly
6. keeping automation-plane breadth plus `TD-STRUCT-005` / `TD-STRUCT-006` expansion deferred until a later bounded follow-on says otherwise

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
- post-`M34` product milestones should normally use meaningful multi-phase progression; a single `Phase 0` is only the default when the milestone is intentionally debt-bounded

## 5. Collaboration Mode

Default collaboration remains:

- architecture, high-risk semantics, and final release decisions are human-led
- workflow is used as the bounded execution engine, validation surface, and audit/replay control plane
- bug-first always applies: if workflow self-dogfood exposes a real bug, repair it before continuing feature scope

## 6. Minimal Documentation Rule

Keep the working tree small.

- prefer keeping only the latest accepted freeze review, current README, current workflow guide, living debt registry, and any currently active phase materials as the active truth set
- if useful long-horizon planning rationale must be retained, collapse it into one clearly non-authoritative root roadmap or archive note instead of restoring multiple competing plans
- treat other plans, phase docs, task-card packs, and historical review bundles as disposable once their conclusions are absorbed
- if historical detail is needed later, use git history instead of restoring large doc packs by default

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

Treat accepted `M34 Phase 0` as the latest completed freeze baseline, clear the known pre-open bug-first gate, keep later productization planning reference-only, and do not resume later breadth work until the next bounded phase is explicitly opened.
