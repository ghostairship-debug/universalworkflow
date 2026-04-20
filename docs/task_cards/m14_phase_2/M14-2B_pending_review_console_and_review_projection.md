# M14-2B Pending Review Console And Review Projection

- Goal: expose awaiting-review runs and their latest review posture through the Web console.
- Write set: `packages/core_domain/service_projection.py`, `apps/orchestrator_api/web_ui.py`, `apps/orchestrator_api/main.py`.
- Acceptance:
  - pending-review console shows awaiting-review runs, latest auto verdict, and recommended action
  - no new review semantics are introduced
