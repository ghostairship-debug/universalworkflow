# M14-1B Operator Read Models And API Projection

- Goal: expose the list, pending-review, and operator-view APIs that the Web UI consumes.
- Write set: `packages/core_domain/repositories.py`, `packages/core_domain/services.py`, `packages/core_domain/service_projection.py`, `apps/orchestrator_api/main.py`.
- Acceptance:
  - `GET /runs` supports `status`, `preset_id`, and `limit`
  - `GET /reviews/pending` returns awaiting-review projections
  - `GET /runs/{id}/operator-view` aggregates summary/detail/inspection/timeline/replay/orchestration
