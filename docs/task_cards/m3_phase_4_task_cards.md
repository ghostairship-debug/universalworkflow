# M3 Phase 4 Task Cards

## Reassessment

- `M3 Phase 3` completed a review-ready run audit bundle.
- The next gap is policy governance: current runtime behavior is visible, but richer review-policy semantics are still not surfaced in a structured way.

## Task Index

| Task ID | Type | Summary | Depends On | Read Set | Write Set | Tests | Output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P4-T01` | `complex` | Add a review-policy catalog / semantics report over current presets and current behavior | `Phase 4 entry` | `packages/core_domain/`, `docs/reviews/m1_review_semantics_decision_table.md`, `docs/tech-debt-registry.md` | policy report module + tests | policy report tests | review-policy governance baseline |
| `P4-T02` | `complex` | Expose review-policy governance through CLI/API and add regression coverage | `P4-T01` | `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_api.py`, `tests/test_cli.py` | CLI/API + regression tests | CLI/API tests | review-policy governance surfaces |
| `P4-T03` | `complex` | Update docs / decision table / validation and close the phase | `P4-T01`, `P4-T02` | `README.md`, `docs/reviews/`, `infra/scripts/offline_validation.py` | docs + validation + closeout | full `pytest` | phase closeout |

## Phase Outcome

- `P4-T01` completed the review-policy catalog and semantics report baseline.
- `P4-T02` exposed review-policy governance through CLI/API with regression coverage.
- `P4-T03` updated docs, decision-table notes, validation, and closeout materials.

## Gate Checklist

- review-policy governance report stays honest about implemented vs reference-only policies
- CLI and API expose the governance report cleanly
- offline validation touches the report
- docs and decision-table notes reflect the current baseline
- full verification passes

## Gate Result

- `pytest tests/test_governance.py tests/test_api.py tests/test_cli.py -q` passed with `69 passed`
- `pytest -q` passed with `146 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe` returned `overall_passed=true`
- `M3 Phase 4` is ready for the next reassessment
