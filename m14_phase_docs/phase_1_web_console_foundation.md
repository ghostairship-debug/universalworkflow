# M14 Phase 1 - Web Console Foundation

Status: complete

## Goal

Ship the built-in FastAPI Web console skeleton and the read-model APIs it depends on.

## Completed Outputs

- `/ui`, `/ui/runs`, `/ui/reviews`, `/ui/governance`, `/ui/config`, `/ui/runs/{id}`
- reusable server-rendered layout in `apps/orchestrator_api/web_ui.py`
- `GET /runs` with `status`, `preset_id`, `limit`
- `GET /reviews/pending`
- `GET /runs/{id}/operator-view`

## Verification

- `python -m pytest tests/test_web_ui.py tests/test_api.py -q`

## Next Phase

- `M14 Phase 2 - Run, Orchestration, And Review Surfaces`
