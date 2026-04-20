# M14-0B Operator Surface Contract And Acceptance Gate

- Goal: define the authoritative Web routes, read-model APIs, and acceptance evidence for `M14`.
- Read set: current API routes, service projection surfaces, TUI/dashboard projection.
- Write set: `m14_phase_docs/phase_0_post_m13_rebaseline_and_scope_freeze.md`.
- Acceptance:
  - `/ui`, `/ui/runs`, `/ui/runs/{id}`, `/ui/reviews`, `/ui/governance`, `/ui/config` are frozen as shipped surfaces.
  - `GET /runs`, `GET /reviews/pending`, `GET /runs/{id}/operator-view` are frozen as supporting APIs.
