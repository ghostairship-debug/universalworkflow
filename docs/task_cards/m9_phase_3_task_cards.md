# M9 Phase 3 Task Cards

**Phase:** `M9 Phase 3 - Governance Metrics And Alerting`  
**Status:** Complete

This is a complex phase. Every task below has a standalone detailed card.

## Scope Lock

- add quantitative governance metrics and alerts
- stay within local repo/operator surfaces
- do not introduce an external dashboard stack

## Task Cards

| ID | Complexity | Goal | Depends On | Primary Files | Verification | Exit Signal | Doc Link |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `M9-3A` | `complex` | Add quantitative governance metrics over debt, validation, policy/runtime coverage, and repository activity | `M9 Phase 2 complete` | `packages/core_domain/governance.py`, `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_governance.py`, `tests/test_cli.py`, `tests/test_api.py` | targeted governance tests | governance metrics report exists end to end | [M9-3A](m9_phase_3/M9-3A_governance_metrics_projection.md) |
| `M9-3B` | `complex` | Add governance alerts/reporting automation and project it through CLI/API | `M9-3A` | `packages/core_domain/governance.py`, `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_governance.py`, `tests/test_cli.py`, `tests/test_api.py` | targeted governance tests | governance alerts surface blocking/degraded conditions automatically | [M9-3B](m9_phase_3/M9-3B_governance_alerts_and_cli_api_surfaces.md) |
| `M9-3C` | `medium` | Update docs/reviews for the governance automation baseline | `M9-3A`, `M9-3B` | `m9_phase_docs/`, `docs/reviews/`, `docs/tech-debt-registry.md` if needed | docs audit | phase can close cleanly | [M9-3C](m9_phase_3/M9-3C_docs_reviews_and_phase_closeout.md) |
