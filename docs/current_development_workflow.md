# Current Development Workflow

This document is the canonical living guide for what the repository should do next and how work should be executed.

## 1. Authoritative Current-State Sources

Use these in priority order when deciding what is current:

1. [docs/reviews/m20-freeze-review.md](reviews/m20-freeze-review.md)
2. [docs/reviews/m25-beta-freeze-review.md](reviews/m25-beta-freeze-review.md)
3. [docs/tech-debt-registry.md](tech-debt-registry.md)
4. [README.md](../README.md)

Older milestone plans, route syntheses, phase reviews, governance side docs, and task-card packs have been intentionally pruned from the working tree. Use git history rather than the current checkout when you need deep historical detail.

## 2. Current Repository Position

The repository has now completed:

- `M8` through `M20`
- `M21` through `M25`
- the runtime, governance, orchestration, Web operator UI, remote worker productization, repo-mutation baseline, and multi-control-plane consensus closure
- retirement of `TD-021`
- capability descriptors / health surfaces, sessionful external-agent lane, orchestration plan graphs, and natural-language launch surfaces

Current status:

- the mainline product is `v1 core complete`
- the active bounded work is `M26 Phase 0 - Post-M25 Policy Control And Operator Convergence Freeze`
- current phase assets live at:
  - [m26_phase_docs/phase_0_post_m25_policy_control_and_operator_convergence_freeze.md](../m26_phase_docs/phase_0_post_m25_policy_control_and_operator_convergence_freeze.md)
  - [docs/task_cards/m26_phase_0_task_cards.md](task_cards/m26_phase_0_task_cards.md)

## 3. What Must Happen Next

`M26 Phase 0` is now open. The repository should not auto-start any new breadth beyond the active phase task cards.

The active cycle must continue by:

1. reading [docs/reviews/m20-freeze-review.md](reviews/m20-freeze-review.md)
2. reading [docs/reviews/m25-beta-freeze-review.md](reviews/m25-beta-freeze-review.md)
3. reading [docs/tech-debt-registry.md](tech-debt-registry.md)
4. executing the active `M26 Phase 0` task cards
4. deferring any breadth decision until the phase closeout can justify the next track:
   - workflow autonomy
   - selective ecosystem expansion
   - multimodal / provider breadth

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

- prefer keeping only the current README, current workflow guide, controlling freeze review, and living debt registry
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

Follow the task-card protocol, treat `M25` as the latest beta freeze baseline, and execute only the active `M26 Phase 0 - Post-M25 Policy Control And Operator Convergence Freeze` work until its closeout says otherwise.
