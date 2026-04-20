# Current Development Workflow

This document is the canonical living guide for what the repository should do next and how work should be executed.

## 1. Authoritative Current-State Sources

Use these in priority order when deciding what is current:

1. [docs/reviews/post-m20-integrated-technical-roadmap.md](reviews/post-m20-integrated-technical-roadmap.md)
2. [docs/reviews/m20-freeze-review.md](reviews/m20-freeze-review.md)
3. [docs/tech-debt-registry.md](tech-debt-registry.md)
4. [README.md](../README.md)

Historical phase reviews, older freeze reviews, and old task-card packs remain historical evidence. Do not rewrite them as if they were current-state guides.

## 2. Current Repository Position

The repository has now completed:

- `M8` through `M20`
- the runtime, governance, orchestration, Web operator UI, remote worker productization, repo-mutation baseline, and multi-control-plane consensus closure
- retirement of `TD-021`

Current status:

- the mainline product is `v1 core complete`
- no open structural debt remains on the mainline control-plane path
- the next approved work is `M21 Phase 0 - Post-M20 Rebaseline And Expansion Freeze`

## 3. What Must Happen Next

Until `M21 Phase 0` is opened, the repository should not auto-start new breadth work.

The next cycle must begin by:

1. reading [docs/reviews/m20-freeze-review.md](reviews/m20-freeze-review.md)
2. reading [docs/reviews/post-m20-integrated-technical-roadmap.md](reviews/post-m20-integrated-technical-roadmap.md)
3. opening `M21 Phase 0 - Post-M20 Rebaseline And Expansion Freeze`
4. deciding which breadth track, if any, is justified next:
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
- completed historical task cards may remain in the repo as records
- complex phases require standalone detailed cards for every task

## 5. Collaboration Mode

Default collaboration remains:

- architecture, high-risk semantics, and final release decisions are human-led
- workflow is used as the bounded execution engine, validation surface, and audit/replay control plane
- bug-first always applies: if workflow self-dogfood exposes a real bug, repair it before continuing feature scope

## 6. What Counts As Done

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

## 7. Current One-Line Instruction

Follow the task-card protocol, treat `M20` as the completed core-complete baseline, and do not begin any new breadth until `M21 Phase 0 - Post-M20 Rebaseline And Expansion Freeze` is explicitly opened.
