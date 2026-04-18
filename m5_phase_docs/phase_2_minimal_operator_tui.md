# M5 Phase 2 - Minimal Operator TUI

**Phase status:** Completed  
**Phase position:** This phase starts after `M5 Phase 1` makes the runtime capable of surfacing live-gateway metadata.

**Entry condition:** The runtime has stable status/detail, summary, and live-gateway visibility, but operators still need to stitch them together manually from CLI/API calls.

---

## 1. Reassessment

Current implementation status:

- the project already has enough structured data to explain runs
- the operator surface is still command-by-command and not session-shaped
- the roadmap explicitly preferred a minimal TUI over a heavier frontend

Decision:

- add a CLI-launched terminal dashboard
- keep it read-mostly and local-first
- build on existing summaries instead of inventing new runtime state

---

## 2. In Scope

- add a minimal terminal dashboard launched from CLI
- show recent runs plus focused run detail
- refresh from the existing service layer
- document usage and add focused tests

---

## 3. Out Of Scope

- Web UI
- inline mutation workflows beyond existing CLI commands
- remote multi-user dashboards
- charting or complex visualization subsystems

---

## 4. Target Baseline

- `workflowctl tui` launches a readable terminal dashboard
- the dashboard shows recent runs and key operator detail
- the dashboard can render a single snapshot for tests or non-interactive use
- the header shows runtime-gateway status so LLM activation is visible

---

## 5. Phase Task Breakdown Principle

This phase is expected to split into:

1. Run-list / dashboard data projection
2. Rich-based TUI renderer and CLI entry point
3. Tests, README, and phase closeout

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- `workflowctl tui` works
- the dashboard is readable on a fresh local DB
- tests cover the data projection and render entry point

---

## 7. Verification Outcome

Completed in this phase:

- added recent-run listing plus dashboard snapshot projection in the service layer
- added a Rich-based TUI with header, recent runs, focus detail, and timeline tail
- added `workflowctl tui` with watch mode and `--once` render support
- documented TUI usage and Windows console UTF-8 guidance

Verification:

- `pytest tests/test_repositories.py tests/test_execution_loop.py tests/test_cli.py -q`
  - targeted TUI and dashboard coverage passed
- `pytest -q`
  - `170 passed`
- `python -m apps.operator_cli.main --db-path state/cycle_validation.db tui --once`
  - rendered a single dashboard snapshot successfully

Result:

- Phase gate passed.
- The current cycle now has a real terminal operator surface without adding a Web stack.
