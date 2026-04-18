# M5 Phase 2 Task Cards

**Phase:** `M5 Phase 2 - Minimal Operator TUI`  
**Status:** Completed

## Scope Lock

- Build a terminal UI, not a Web app.
- Reuse existing run/status/summary data instead of creating new state.
- Keep the surface read-mostly and operator-friendly.

## Task Cards

| ID | Status | Goal | Outcome |
| --- | --- | --- | --- |
| `P2-T01` | `completed` | Add recent-run listing and dashboard projection helpers to the service/repository layer | service/repository now produce a stable recent-run list plus focus snapshot for the dashboard |
| `P2-T02` | `completed` | Add a Rich-based terminal dashboard and CLI launch command | `workflowctl tui` now renders a real operator dashboard with watch mode and single-shot mode |
| `P2-T03` | `completed` | Update README, closeout docs, and validation notes for the new TUI surface | operator docs now cover TUI launch, focused flags, and Windows UTF-8 guidance |

## Exit Criteria

- `workflowctl tui` launches a terminal dashboard
- recent-run and focused-run data projections are tested
- README and phase closeout docs explain the TUI

## Verification

- `pytest tests/test_repositories.py tests/test_execution_loop.py tests/test_cli.py -q`
  - targeted TUI coverage passed
- `pytest -q`
  - `170 passed`
- `python -m apps.operator_cli.main --db-path state/cycle_validation.db tui --once`
  - rendered a single dashboard snapshot successfully
