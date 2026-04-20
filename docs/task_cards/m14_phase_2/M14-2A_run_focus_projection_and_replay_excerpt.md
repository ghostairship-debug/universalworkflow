# M14-2A Run Focus Projection And Replay Excerpt

- Goal: make the run page operator-complete for inspection and explanation.
- Write set: `apps/orchestrator_api/web_ui.py`, `packages/core_domain/service_projection.py`.
- Acceptance:
  - run focus page renders summary, status detail, inspection, timeline, replay excerpt, and orchestration
  - page links remain grounded in repository truth rather than duplicated logic
