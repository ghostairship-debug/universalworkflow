# M14-3A Web Action Binding For Lifecycle Mutations

- Goal: wire the Web UI to the canonical lifecycle mutations.
- Write set: `apps/orchestrator_api/main.py`, `apps/orchestrator_api/web_ui.py`.
- Acceptance:
  - Web routes exist for `resume`, `approve`, `reject`, `reconcile`, and `cancel`
  - actions reuse existing service/API semantics
  - operator feedback is visible after redirects
