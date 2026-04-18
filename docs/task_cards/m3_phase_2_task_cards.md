# M3 Phase 2 Task Cards

## Reassessment

- `M3 Phase 1` completed richer event inspection and closure discipline.
- The next gap is governance visibility: `docs/tech-debt-registry.md` is still the source of truth, but it is not yet projected into any structured operator / review surface.

## Phase Outcome

- `G2-T01` completed the tech-debt report parser and governance projection baseline.
- `G2-T02` exposed the governance report through CLI/API with regression coverage.
- `G2-T03` updated docs, validation, and review materials, then closed the phase.

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `G2-T01` | `complex` | Parse the tech-debt registry into a structured governance report | `Phase 2 entry` | `docs/tech-debt-registry.md`, `docs/legacy_project_reference_uplift_plan.md` | `packages/core_domain/governance.py`, `tests/test_governance.py` | parser tests | governance report baseline |
| `G2-T02` | `complex` | Expose governance visibility through CLI/API and add regression coverage | `G2-T01` | `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_api.py`, `tests/test_cli.py` | CLI/API + regression tests | CLI/API tests | governance surfaces |
| `G2-T03` | `complex` | Update docs / validation / review closeout for governance projection | `G2-T01`, `G2-T02` | `README.md`, `infra/scripts/offline_validation.py`, `docs/reviews/`, `m3_phase_docs/phase_2_governance_projection_and_tech_debt_visibility_baseline.md` | docs + validation + closeout | full `pytest` | phase closeout |

## Gate Checklist

- governance report stays derived from the registry markdown
- CLI and API expose the governance report cleanly
- offline validation checks the governance surface
- docs and review materials mention the governance baseline
- full verification passes

## Gate Result

- `pytest tests/test_governance.py tests/test_api.py tests/test_cli.py -q` passed with `64 passed`
- `pytest -q` passed with `139 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe` returned `overall_passed=true`
- `M3 Phase 2` is ready for the next reassessment
