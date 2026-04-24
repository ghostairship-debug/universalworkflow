# M37 Phase 2: Automation Controller, Watchdog, And Closeout

Status: completed
Opened: 2026-04-24
Closed: 2026-04-24
Baseline: completed `M37 Phase 1`

## Purpose

Close `M37` by adding a bounded automation-controller/watchdog line on top of the now-productized interaction and workbench layers.

## Outcome

`M37` is complete.

The repository now supports:

- persisted automation watchdog registration
- watchdog evaluation across session, run, and follow-up state
- low-risk automatic session closeout when explicitly enabled and safe
- additive CLI, API, and workbench visibility for generated profiles and watchdog projections
