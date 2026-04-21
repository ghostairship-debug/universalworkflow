# Current Development Workflow

This document is the canonical living guide for what the repository should do next and how work should be executed.

## 1. Authoritative Current-State Sources

Use these in priority order when deciding what is current:

1. [docs/reviews/m30-operator-control-freeze-review.md](reviews/m30-operator-control-freeze-review.md)
2. [docs/reviews/m20-freeze-review.md](reviews/m20-freeze-review.md)
3. [docs/tech-debt-registry.md](tech-debt-registry.md)
4. [README.md](../README.md)

Older milestone plans, route syntheses, phase reviews, governance side docs, and task-card packs have been intentionally pruned from the working tree. Use git history rather than the current checkout when you need deep historical detail.

## 2. Current Repository Position

The repository has now completed:

- `M8` through `M20`
- `M21` through `M30`
- the runtime, governance, orchestration, Web operator UI, remote worker productization, repo-mutation baseline, and multi-control-plane consensus closure
- retirement of `TD-021`
- capability descriptors / health surfaces, sessionful external-agent lane, orchestration plan graphs, natural-language launch surfaces, capability policy preview, operator packets, goal packets, and dashboard operator convergence

Current status:

- the mainline product is `v1 core complete`
- the latest accepted freeze is `M30 Operator Control Freeze`
- there is no new active post-`M30` phase open in the working tree yet
- the built-in Web UI and TUI remain operator surfaces rather than chat-style natural-language workbenches
- natural-language goal planning and launch exist today through CLI/API surfaces, not through a front-end conversational shell

## 3. What Must Happen Next

No new post-`M30` phase is open. The repository should not auto-start new breadth until the next bounded phase is explicitly opened.

The next cycle must begin by:

1. reading [docs/reviews/m30-operator-control-freeze-review.md](reviews/m30-operator-control-freeze-review.md)
2. reading [docs/reviews/m20-freeze-review.md](reviews/m20-freeze-review.md)
3. reading [docs/tech-debt-registry.md](tech-debt-registry.md)
4. opening a new bounded phase doc and task-card pack only after the intended next track is justified
5. deferring breadth decisions until that next phase explicitly names them

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

Treat `M30` as the latest operator-control freeze baseline, and do not open the next phase until its bounded scope is explicitly justified from the freeze review.
