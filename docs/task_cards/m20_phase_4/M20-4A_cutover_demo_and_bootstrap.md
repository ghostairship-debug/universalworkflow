# M20-4A - Deliver the cutover demo, bootstrap commands, and recovery runbook.

Status: planned

## Goal

Deliver the cutover demo, bootstrap commands, and recovery runbook.

## Scope

- Provide the final cluster-backed hosted demo and operator bootstrap path.
- keep the work aligned to TD-021 retirement and core completion

## Write Set

- `README.md`
- `docs/reviews/post-m20-integrated-technical-roadmap.md`
- `infra/scripts/offline_validation.py`

## Read Set

- `apps/scheduler_authority_api/main.py`
- `apps/orchestrator_api/main.py`
- `apps/remote_worker_api/main.py`

## Tests

- `python -m infra.scripts.offline_validation --skip-offline-probe`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
