# Current Development Workflow

This document is the canonical living guide for what the repository should do next and how work should be executed.

## 1. Authoritative Current-State Sources

Use these in priority order when deciding what is current:

1. [m32_phase_docs/phase_0_interaction_profile_cluster_foundation.md](../m32_phase_docs/phase_0_interaction_profile_cluster_foundation.md)
2. [docs/task_cards/m32_phase_0_task_cards.md](task_cards/m32_phase_0_task_cards.md)
3. [docs/reviews/m31-boundary-contraction-freeze-review.md](reviews/m31-boundary-contraction-freeze-review.md)
4. [docs/reviews/m30-operator-control-freeze-review.md](reviews/m30-operator-control-freeze-review.md)
5. [docs/reviews/m20-freeze-review.md](reviews/m20-freeze-review.md)
6. [docs/tech-debt-registry.md](tech-debt-registry.md)
7. [README.md](../README.md)

The repository is now in an active `M32 Phase 0` line. Older plans and retained reference bundles remain secondary to the active phase doc, task cards, accepted `M31` freeze review, and living debt registry.

## 2. Current Repository Position

The repository has now completed:

- `M8` through `M20`
- `M21` through `M30`
- accepted `M31 Phase 0`
- the runtime, governance, orchestration, Web operator UI, remote worker productization, repo-mutation baseline, and single-store quorum-style scheduler-authority closure
- retirement of `TD-021`
- capability descriptors / health surfaces, sessionful external-agent lane, orchestration plan graphs, natural-language launch surfaces, capability policy preview, operator packets, goal packets, and dashboard operator convergence

Current status:

- the mainline product is `v1 core complete`
- the latest accepted freeze is `M31 Boundary Contraction And Semantic Honesty Freeze`
- `M32 Phase 0` is the active bounded phase now open in the working tree
- the current phase is interaction-first, role-profile-aware, and cluster-ready
- automation-plane breadth remains deferred
- the built-in Web UI and TUI remain operator surfaces rather than chat-style natural-language workbenches
- natural-language goal planning and launch exist today through CLI/API surfaces, not through a front-end conversational shell

## 3. What Must Happen Next

`M32 Phase 0` is open. The repository should execute only the current task-card pack and should not expand into automation-plane or later breadth until a later bounded phase explicitly opens that work.

The current cycle proceeds by:

1. reading [m32_phase_docs/phase_0_interaction_profile_cluster_foundation.md](../m32_phase_docs/phase_0_interaction_profile_cluster_foundation.md)
2. reading [docs/task_cards/m32_phase_0_task_cards.md](task_cards/m32_phase_0_task_cards.md)
3. reading [docs/reviews/m31-boundary-contraction-freeze-review.md](reviews/m31-boundary-contraction-freeze-review.md)
4. carrying `TD-STRUCT-*` items into the active `M32` work
5. executing bug-first: repair real workflow/runtime regressions before continuing feature scope
6. keeping automation-plane and later breadth deferred

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

- prefer keeping only the active phase doc, active task-card pack, current README, current workflow guide, controlling freeze review, and living debt registry as the active truth set
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

Treat accepted `M31 Phase 0` as the last completed freeze baseline, treat `M32 Phase 0` as the active bounded implementation line, and execute only the current `M32` task-card pack while keeping bug-first and deferred automation-plane rules in force.
