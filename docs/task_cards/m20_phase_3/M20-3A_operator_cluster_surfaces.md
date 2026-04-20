# M20-3A - Expose cluster topology, leadership, and takeover lineage through operator surfaces.

Status: planned

## Goal

Expose cluster topology, leadership, and takeover lineage through operator surfaces.

## Scope

- Make CLI, API, and Web UI explain the cluster state in one place.
- keep the work aligned to TD-021 retirement and core completion

## Write Set

- `apps/orchestrator_api/main.py`
- `apps/orchestrator_api/web_ui.py`
- `packages/core_domain/service_projection.py`
- `tests/test_api.py`

## Read Set

- `packages/core_domain/services.py`
- `packages/core_domain/scheduler_authority.py`

## Tests

- `python -m pytest tests/test_api.py -q -k cluster`

## Completion Evidence

- implementation lands only in the declared write set
- declared tests pass
- closeout folds into the phase review or freeze review
