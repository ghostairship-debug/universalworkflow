# M27 Phase 0 - Operator Packet Standardization

Status: completed
Opened: 2026-04-21
Milestone: M27

## Purpose

Standardize a compact operator packet so the main operator surfaces can consume one stable read model instead of reassembling the same policy, session, and summary fields repeatedly.

## Scope

- add a run-level operator packet service surface
- expose the packet through CLI and API
- reuse the packet in operator view assembly

## Outcome

- `get_run_operator_packet()` landed as the primary compact operator read model
- `workflowctl run operator-packet` and `GET /runs/{run_id}/operator-packet` landed
- `get_operator_view()` now embeds the standardized operator packet instead of requiring clients to recompose equivalent state
