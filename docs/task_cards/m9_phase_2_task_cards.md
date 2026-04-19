# M9 Phase 2 Task Cards

**Phase:** `M9 Phase 2 - Durable Recovery Lineage And Reconciliation`  
**Status:** Complete

This is a complex phase. Every task below has a standalone detailed card.

## Scope Lock

- deepen durable lineage and reconciliation only
- keep the durable lane opt-in
- do not promote it to default behavior

## Task Cards

| ID | Complexity | Goal | Depends On | Primary Files | Verification | Exit Signal | Doc Link |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `M9-2A` | `complex` | Persist durable checkpoint lineage/history through start, resume, review, terminal, and cancel transitions | `M9 Phase 1 complete` | `packages/core_domain/services.py`, `packages/core_domain/service_lifecycle.py`, `tests/test_execution_loop.py` | targeted lifecycle tests | durable runs keep lineage rather than only latest refs | [M9-2A](m9_phase_2/M9-2A_durable_lineage_history_persistence.md) |
| `M9-2B` | `complex` | Add durable-specific diagnostics and reconciliation checks to inspection/audit surfaces | `M9-2A` | `packages/core_domain/services.py`, `packages/core_domain/service_projection.py`, `tests/test_execution_loop.py`, `tests/test_api.py` | targeted inspection/audit tests | durable inconsistencies are visible and actionable | [M9-2B](m9_phase_2/M9-2B_durable_diagnostics_and_reconciliation_checks.md) |
| `M9-2C` | `medium` | Update docs/reviews for the durable hardening result | `M9-2A`, `M9-2B` | `m9_phase_docs/`, `docs/reviews/`, `README.md` if needed | docs audit | phase can close cleanly | [M9-2C](m9_phase_2/M9-2C_docs_reviews_and_phase_closeout.md) |
