# M2 Phase 0 Task Cards

## Reassessment

- `M1.5` is complete and `TD-005` is repaid.
- The next highest-value gap is no longer adapter routing; it is the lack of safe repair after inspection detects drift.
- The phase therefore focuses on a minimal reconcile loop before touching claim / lease / concurrency topics.

Phase outcome:

- `R0-T01`, `R0-T02`, and `R0-T03` are completed.
- Verification closed with `67 passed` plus `offline_validation --skip-offline-probe` returning `overall_passed=true`.
- The next recommended phase is claim-ready runtime lifecycle hardening.

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `R0-T01` | `complex` | Extract a run-centric reconcile catalog and add runtime-state query helpers for latest/live/terminal views | `Phase 0 entry` | `packages/core_domain/services.py`, `packages/core_domain/repositories.py`, `packages/contracts/runtime.py`, `tests/test_execution_loop.py`, `docs/legacy_project_reference_uplift_plan.md` | `packages/core_domain/services.py`, `packages/core_domain/repositories.py`, `tests/test_execution_loop.py`, `tests/test_repositories.py` | repository + inspection tests | repair-aware inspection baseline |
| `R0-T02` | `complex` | Add safe apply actions for repairable problems and keep unsafe cases manual-only | `R0-T01` | `packages/core_domain/services.py`, `packages/contracts/events.py`, `tests/test_execution_loop.py`, `docs/legacy_project_reference_uplift_plan.md` | `packages/core_domain/services.py`, `packages/contracts/events.py`, `packages/core_domain/errors.py`, `tests/test_execution_loop.py`, `tests/test_api.py`, `tests/test_cli.py` | execution + API + CLI tests | controlled repair loop |
| `R0-T03` | `complex` | Expose reconcile surfaces through CLI/API, update docs/debt tracking if needed, and run full verification | `R0-T01`, `R0-T02` | `README.md`, `m2_phase_docs/phase_0_runtime_reconcile_and_controlled_repair.md`, `tests/`, `infra/scripts/offline_validation.py` | docs + surfaces + verification artifacts | full `pytest` | phase closeout |

## Gate Checklist

- `inspection` distinguishes repairable vs manual-only problems
- safe repair actions are explicit and audited
- reconcile apply does not introduce legacy kernel concepts
- shell and noop flows remain green after repair changes

Implementation status:

- `R0-T01`: completed, including repository query helpers plus repair-aware inspection metadata
- `R0-T02`: completed, including safe apply actions and audited `repair_applied` events
- `R0-T03`: completed, including CLI/API reconcile surfaces, README updates, full `pytest`, and offline validation

Gate result:

- Passed for all checklist items
