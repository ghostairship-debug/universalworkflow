# M14-3B Batch Resume Feedback And Review Escalation

- Goal: expose batch-resume as an operator action and keep human-review escalations visible.
- Write set: `apps/orchestrator_api/main.py`, `apps/orchestrator_api/web_ui.py`, `tests/test_web_ui.py`.
- Acceptance:
  - batch-resume is callable from the Web surface
  - UI paths keep `human_required`, `mandatory`, and recommended-fail review states legible
