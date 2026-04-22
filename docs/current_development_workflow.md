# Current Development Workflow

This document is the canonical living guide for what the repository should do next and how work should be executed.

## 1. Authoritative Current-State Sources

Use these in priority order when deciding what is current:

1. [m34_phase_docs/phase_0_facade_reduction_and_authority_interior_cleanup.md](../m34_phase_docs/phase_0_facade_reduction_and_authority_interior_cleanup.md)
2. [docs/task_cards/m34_phase_0_task_cards.md](task_cards/m34_phase_0_task_cards.md)
3. [docs/reviews/m33-orchestration-service-contraction-freeze-review.md](reviews/m33-orchestration-service-contraction-freeze-review.md)
4. [docs/tech-debt-registry.md](tech-debt-registry.md)
5. [README.md](../README.md)
6. [docs/reviews/m32-interaction-profile-cluster-foundation-freeze-review.md](reviews/m32-interaction-profile-cluster-foundation-freeze-review.md)
7. [docs/reviews/m31-boundary-contraction-freeze-review.md](reviews/m31-boundary-contraction-freeze-review.md)
8. [docs/reviews/m30-operator-control-freeze-review.md](reviews/m30-operator-control-freeze-review.md)
9. [docs/reviews/m20-freeze-review.md](reviews/m20-freeze-review.md)

The repository is now in active `M34 Phase 0` work. Accepted `M33 Phase 0` remains the latest completed bounded baseline.

Archived planning context from the pre-merge backup workspace is summarized in [docs/reviews/m32-archived-planning-inputs.md](reviews/m32-archived-planning-inputs.md). Treat it as reference-only, not as parallel execution truth.

## 2. Current Repository Position

The repository has now completed:

- `M8` through `M20`
- `M21` through `M30`
- accepted `M31 Phase 0`
- accepted `M32 Phase 0`
- accepted `M33 Phase 0`
- the runtime, governance, orchestration, Web operator UI, remote worker productization, repo-mutation baseline, single-store quorum-style scheduler-authority closure, interaction/profile/cluster foundation, and the first shared orchestration/service contraction line
- retirement of `TD-021`

Current status:

- the mainline product is `v1 core complete`
- the latest accepted freeze is `M33 Orchestration / Service Contraction Freeze`
- the active bounded phase is `M34 Phase 0: Facade Reduction / Authority Interior Cleanup`
- the current bounded debt focus is `TD-STRUCT-001` and `TD-STRUCT-003`
- `TD-STRUCT-005` and `TD-STRUCT-006` remain deferred to a post-`M34 Phase 0` bounded follow-on
- `TD-STRUCT-004` remains repaid in accepted `M33 Phase 0`
- the latest accepted foundation is interaction-first, role-profile-aware, and cluster-aware, with a shared orchestration-plan builder for the shipped multi-role presets
- automation-plane breadth remains deferred
- the built-in Web UI and TUI remain operator surfaces rather than chat-style natural-language workbenches
- natural-language goal planning and launch exist today through CLI/API plus the minimum workbench preview, not through a front-end conversational shell

## 3. What Must Happen Next

The next cycle is now active as `M34 Phase 0`. The repository should execute that bounded cleanup line before opening later breadth work.

`M34 Phase 0` should proceed by:

1. using [m34_phase_docs/phase_0_facade_reduction_and_authority_interior_cleanup.md](../m34_phase_docs/phase_0_facade_reduction_and_authority_interior_cleanup.md) as the active phase truth
2. using [docs/task_cards/m34_phase_0_task_cards.md](task_cards/m34_phase_0_task_cards.md) as the execution index
3. keeping accepted `M33 Phase 0` as the latest completed freeze baseline
4. executing bug-first: repair real workflow/runtime regressions before continuing refactor scope
5. focusing on `TD-STRUCT-001` and `TD-STRUCT-003`
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

## 5. Collaboration Mode

Default collaboration remains:

- architecture, high-risk semantics, and final release decisions are human-led
- workflow is used as the bounded execution engine, validation surface, and audit/replay control plane
- bug-first always applies: if workflow self-dogfood exposes a real bug, repair it before continuing feature scope

## 6. Minimal Documentation Rule

Keep the working tree small.

- prefer keeping only the latest accepted freeze review, current README, current workflow guide, living debt registry, and any currently active phase materials as the active truth set
- if useful long-horizon planning rationale must be retained, collapse it into one clearly non-authoritative archive note instead of restoring multiple root-level plans
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

Treat accepted `M33 Phase 0` as the latest completed freeze baseline, execute active `M34 Phase 0` bug-first, and do not open later breadth work until this bounded cleanup phase closes honestly.
