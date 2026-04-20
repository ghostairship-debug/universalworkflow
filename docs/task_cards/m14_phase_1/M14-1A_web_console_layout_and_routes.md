# M14-1A Web Console Layout And Routes

- Goal: add the FastAPI-hosted Web shell and route skeleton without introducing a second control plane.
- Write set: `apps/orchestrator_api/main.py`, `apps/orchestrator_api/web_ui.py`.
- Acceptance:
  - all six `/ui/*` routes render successfully
  - HTML is server-rendered and controller-owned
  - no React/Vite dependency is introduced
