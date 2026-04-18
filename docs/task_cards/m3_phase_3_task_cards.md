# M3 Phase 3 Task Cards

## Reassessment

- `M3 Phase 2` completed governance visibility for the technical-debt registry.
- The next gap is review/handoff packaging: operators still need to manually assemble summary, event inspection, and state inspection into a single audit artifact.

## Phase Outcome

- `A3-T01` completed the service-level run-audit report assembly.
- `A3-T02` exposed the audit bundle through CLI/API with regression coverage.
- `A3-T03` updated docs, validation, and review materials, then closed the phase.

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `A3-T01` | `complex` | Assemble a single run-audit report from existing operator surfaces | `Phase 3 entry` | `packages/core_domain/services.py`, `m3_phase_docs/phase_2_governance_projection_and_tech_debt_visibility_baseline.md` | `packages/core_domain/services.py`, `tests/test_execution_loop.py` | service tests | audit-report baseline |
| `A3-T02` | `complex` | Expose audit-report through CLI/API and add regression coverage | `A3-T01` | `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_api.py`, `tests/test_cli.py` | CLI/API + regression tests | CLI/API tests | audit-report surfaces |
| `A3-T03` | `complex` | Update docs / validation / review closeout for audit-report packaging | `A3-T01`, `A3-T02` | `README.md`, `infra/scripts/offline_validation.py`, `docs/reviews/`, `m3_phase_docs/phase_3_run_audit_report_and_review_packet_baseline.md` | docs + validation + closeout | full `pytest` | phase closeout |

## Gate Checklist

- run-audit report stays derivative of existing run surfaces
- CLI and API expose the audit-report bundle cleanly
- offline validation checks the audit bundle
- docs and review materials describe audit-report usage
- full verification passes

## Gate Result

- `pytest tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q` passed with `115 passed`
- `pytest -q` passed with `143 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe` returned `overall_passed=true`
- `M3 Phase 3` is ready for the next reassessment
