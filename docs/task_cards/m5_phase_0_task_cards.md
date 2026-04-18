# M5 Phase 0 Task Cards

**Phase:** `M5 Phase 0 - Cycle Revalidation And Next-Cycle Scope Freeze`  
**Status:** Completed

## Scope Lock

- Revalidate the shipped `M4` baseline before changing runtime behavior again.
- Fix operator-facing regressions exposed by revalidation immediately.
- Freeze the next cycle to LLM integration plus minimal TUI only.

## Task Cards

| ID | Status | Goal | Outcome |
| --- | --- | --- | --- |
| `P0-T01` | `completed` | Re-run the current-cycle acceptance proofs and record the actual baseline | `pytest -q`, `offline_validation`, and `manage.py demo` reran successfully from the current checkout |
| `P0-T02` | `completed` | Fix any operator/governance regression surfaced by revalidation | governance release-readiness now falls back to seed presets when the DB has not been bootstrapped |
| `P0-T03` | `completed` | Freeze the next cycle around `RuntimeGateway + TUI` and write closeout notes | M5 is explicitly scoped to `OpenAI RuntimeGateway + minimal operator TUI` |

## Exit Criteria

- acceptance proofs rerun successfully
- governance/operator regression is fixed if found
- next-cycle scope is frozen to LLM + TUI

## Verification

- `pytest tests/test_governance.py tests/test_cli.py -q`
  - `39 passed`
- `pytest -q`
  - `170 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`
