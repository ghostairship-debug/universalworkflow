# M29 Phase 0 - Dashboard Operator Convergence

Status: completed
Opened: 2026-04-21
Milestone: M29

## Purpose

Converge dashboard and list views onto the same operator packet family so focus detail and run rows carry policy-aware operator hints.

## Scope

- project recommended operator mode into run rows
- add focus operator packet to dashboard snapshot
- keep compatibility for existing focus detail and summary consumers

## Outcome

- dashboard snapshot now includes `focus_operator_packet`
- operator rows now include `recommended_operator_mode`
- no existing dashboard payload fields were removed
