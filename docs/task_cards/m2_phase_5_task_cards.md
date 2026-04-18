# M2 Phase 5 Task Cards

## Reassessment

- `M2 Phase 4` completed the local worker-lease baseline and lease-aware operator surfaces.
- The next gap is no longer raw worker ownership visibility; it is the lack of explicit runtime-attempt lineage for interrupted or superseded execution.
- This phase therefore introduces a local runtime-attempt baseline before any stronger barrier or concurrency semantics are attempted.

## Phase Outcome

- `A5-T01` completed the runtime-attempt contract, migration, and repository baseline.
- `A5-T02` wired compile / recompile / resume / repair flows into explicit attempt lineage and interrupted-attempt diagnostics.
- `A5-T03` exposed attempt history through CLI/API, updated docs and validation, and closed the phase gate.

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `A5-T01` | `complex` | Add the runtime-attempt contract, migration, repository methods, and query surfaces | `Phase 5 entry` | `packages/contracts/runtime.py`, `packages/core_domain/repositories.py`, `infra/migrations/`, `tests/test_contracts.py`, `tests/test_repositories.py`, `docs/legacy_project_reference_uplift_plan.md` | `packages/contracts/*`, `packages/core_domain/repositories.py`, `infra/migrations/*`, `tests/test_contracts.py`, `tests/test_repositories.py` | contract + repository tests | persisted runtime-attempt baseline |
| `A5-T02` | `complex` | Integrate attempt creation, supersede / interruption diagnostics, and bounded repair into services | `A5-T01` | `packages/core_domain/services.py`, `packages/contracts/events.py`, `tests/test_execution_loop.py`, `docs/legacy_project_reference_uplift_plan.md` | `packages/core_domain/services.py`, `packages/contracts/events.py`, `tests/test_execution_loop.py`, `tests/test_api.py`, `tests/test_cli.py` | service + API + CLI tests | attempt lifecycle and interrupted-run diagnostics |
| `A5-T03` | `complex` | Expose attempt surfaces through CLI/API, update docs/validation, and run full verification | `A5-T01`, `A5-T02` | `README.md`, `infra/scripts/offline_validation.py`, `m2_phase_docs/phase_5_runtime_attempt_lifecycle_and_interrupted_recovery.md`, `tests/` | docs + validation + surfaces | full `pytest` | phase closeout |

## Gate Checklist

- runtime attempts are persisted and auditable
- compile / recompile / resume update attempt lineage consistently
- inspection exposes interrupted or superseded attempt mismatches
- claim / worker-lease / snapshot / attempt projections remain comprehensible together
- shell and noop execution paths remain green

## Gate Result

- `pytest -q` passed with `126 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe` returned `overall_passed=true`
- `M2 Phase 5` is ready to close and hand off to the next reassessment
