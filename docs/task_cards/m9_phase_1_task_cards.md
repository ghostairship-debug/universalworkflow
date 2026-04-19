# M9 Phase 1 Task Cards

**Phase:** `M9 Phase 1 - Replay Linkage And Metrics Baseline`  
**Status:** Complete

This is a complex phase. Every task below has a standalone detailed card.

## Scope Lock

- add replay-grade linkage and first-class run metrics
- expose them through existing operator surfaces
- do not yet change durable merge policy, governance automation, or review-policy breadth

## Task Cards

| ID | Complexity | Goal | Depends On | Primary Files | Verification | Exit Signal | Doc Link |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `M9-1A` | `complex` | Add replay-packet projection across timeline/state/attempt/ownership/review artifacts | `M9 Phase 0 complete` | `packages/core_domain/service_projection.py`, `packages/core_domain/services.py`, `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_execution_loop.py`, `tests/test_cli.py`, `tests/test_api.py` | targeted projection/CLI/API tests | replay packet is available end to end | [M9-1A](m9_phase_1/M9-1A_replay_packet_projection.md) |
| `M9-1B` | `complex` | Add first-class run metrics to status/summary/audit surfaces and operator diagnostics | `M9-1A` | `packages/core_domain/service_projection.py`, `packages/core_domain/services.py`, `tests/test_execution_loop.py`, `tests/test_cli.py`, `tests/test_api.py` | targeted projection tests | metrics are visible in operator-facing diagnostics | [M9-1B](m9_phase_1/M9-1B_run_metrics_surfaces_and_focus_data.md) |
| `M9-1C` | `medium` | Update docs/reviews for the new replay/metrics baseline | `M9-1A`, `M9-1B` | `m9_phase_docs/`, `docs/reviews/`, `README.md` if needed | docs audit | phase can close cleanly | [M9-1C](m9_phase_1/M9-1C_docs_reviews_and_phase_closeout.md) |
