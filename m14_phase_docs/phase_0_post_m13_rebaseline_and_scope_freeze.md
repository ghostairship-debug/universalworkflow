# M14 Phase 0 - Post-M13 Rebaseline And Scope Freeze

Status: complete

## Goal

Freeze `M14` as the operator-surface milestone that turns the shipped CLI/API/TUI baseline into a full built-in Web operator UI without reopening hosted/distributed scope.

## In Scope

- freeze authoritative `/ui/*` surfaces
- confirm Web UI remains API-first and controller-owned
- keep `TD-019` out of `M14`
- define verification gates for HTML, operator aggregation, and human actions

## Out Of Scope

- remote worker pools
- multi-control-plane consensus
- multimodal expansion
- standalone frontend stack

## Completed Freeze Decisions

- `M14` uses the existing FastAPI app and server-rendered HTML
- Web UI consumes repository truth from `status-detail`, `summary`, `inspection`, `replay-packet`, and governance reports
- new read APIs are limited to `GET /runs`, `GET /reviews/pending`, and `GET /runs/{id}/operator-view`
- mutation semantics remain the existing lifecycle actions

## Verification Anchor

- `tests/test_web_ui.py`
- `tests/test_api.py`

## Next Phase

- `M14 Phase 1 - Web Console Foundation`
