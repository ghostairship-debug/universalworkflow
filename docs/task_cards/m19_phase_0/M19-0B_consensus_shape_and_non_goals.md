# M19-0B - Freeze the cluster shape, authority responsibilities, and explicit non-goals for M19.

Status: planned

## Goal

Freeze the cluster shape, authority responsibilities, and explicit non-goals for M19.

## Scope

- Freeze M19 as the majority-consensus and control-plane takeover milestone.
- keep the work aligned to TD-021 final repayment track

## Write Set

- `docs/reviews/post-m18-integrated-technical-roadmap.md`
- `packages/core_domain/services.py`
- `apps/orchestrator_api/main.py`

## Read Set

- `packages/core_domain/config.py`
- `infra/seeds/worker_pool_profiles.json`

## Tests

- `python -m infra.scripts.check_doc_links`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
