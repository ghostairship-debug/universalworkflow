# Next Development Plan

Status: reference-only  
Date: 2026-04-22  
Baseline: accepted `M34 Phase 0`

## 1. Purpose

This file is the short root-level planning pointer for the repository after accepted `M34 Phase 0`.

It does **not** open `M35`, `M36`, or any later milestone by itself. Active execution truth still comes from:

1. [docs/current_development_workflow.md](docs/current_development_workflow.md)
2. [docs/reviews/m34-facade-reduction-and-authority-interior-cleanup-freeze-review.md](docs/reviews/m34-facade-reduction-and-authority-interior-cleanup-freeze-review.md)
3. [docs/tech-debt-registry.md](docs/tech-debt-registry.md)

## 2. Current Honest Position

The repository has accepted:

- `M31 Phase 0`
- `M32 Phase 0`
- `M33 Phase 0`
- `M34 Phase 0`

That means the repository now has:

- interaction / profile / cluster foundation
- shared orchestration/service contraction for the shipped multi-role presets
- a second scheduler-authority honesty cleanup line
- a minimum workbench preview

It does **not** yet mean that the older productization expectations associated with `M33-M36` have already been fulfilled.

## 3. Rebuilt Post-M34 Roadmap

The detailed rebuilt roadmap now lives in:

- [POST_M34_MULTIPHASE_ROADMAP.md](POST_M34_MULTIPHASE_ROADMAP.md)

That roadmap is also reference-only until the next bounded phase opens.

Its main conclusions are:

- the old one-milestone-one-`Phase 0` drift should stop for the productization line
- post-`M34` milestones should return to meaningful multi-phase progression
- the earlier platform product target now honestly requires `M35-M39`
- if the target also includes domain-grade design and multimodal visual verification, `M40` is likely needed

## 4. Immediate Next Step

Before `M35` opens, the repository should clear the known bug-first pre-open gate:

1. repair the two known governance tech-debt report expectation regressions
2. finish aligning living planning docs with the accepted `M34` baseline
3. then open `M35` explicitly with a real multi-phase milestone shape

## 5. Planning Boundary

This planning update is documentation-only.

- no new phase is opened here
- no implementation work is claimed here
- any code or contract changes required by the roadmap belong in future phase docs and task cards
