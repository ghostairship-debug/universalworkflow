# M18-0A - Post-M17 Rebaseline And Scope Freeze

Status: complete

## Goal

Freeze M18 as the scheduler-authority first-slice milestone.

## Scope

- Lock the centralized authority scope and explicitly defer full consensus retirement.
- keep the work aligned to TD-021 Multi-Control-Plane First Slice

## Write Set

- `m18_phase_docs`
- `docs/task_cards/m18_phase_0*`
- `docs/reviews/m18-freeze-review.md`
- `docs/current_development_workflow.md`

## Read Set

- `docs/reviews/m17-freeze-review.md`
- `docs/tech-debt-registry.md`
- `docs/reviews/post-m18-integrated-technical-roadmap.md`

## Tests

- `python -m infra.scripts.check_doc_links`

## Completion Evidence

- implementation landed in the declared write set
- declared tests passed for the shipped baseline
- closeout folded into the milestone freeze review
