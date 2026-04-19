# M8 Freeze Review

## Decision

`M8` is **complete** and the repository is **GO** for opening `M9 Phase 0 - Post-M8 Rebaseline And Scope Freeze`.

`M8` was an integration cycle, not a generic feature-expansion cycle.
It focused on borrowing the right external substrate while preserving the repository as the local-first control plane.

## What Closed In M8

- `M8 Phase 0` froze `Borrow / Wrap / Own`, lane strategy, canonical IDs, trust tiers, fallback rules, and feature flags.
- `M8 Phase 1` added the borrowed agent foundation and execution-lane projections.
- `M8 Phase 2` added router-first MCP capability projection with a local stdio pilot.
- `M8 Phase 3` added OTel-first observability abstraction and the first sink implementation.
- `M8 Phase 4` added the durable pilot boundary and diagnostics-only runtime ref mapping.
- `M8 Phase 5` added Agent Skill-compatible domain-pack export.
- `M8 Phase 6` added direct M8 confidence tests and repaired editable-install package discovery.

## Verification Evidence

- `pytest -q`
  - `225 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`
- `python -m infra.scripts.check_doc_links`
  - `passed=true`
- `python -m pip install -e . --no-deps`
  - succeeded after the package-discovery fix

## M8 Outcome Summary

The repository now has:

- a preserved native deterministic lane for `feature_delivery`
- an opt-in borrowed standard agent lane
- a router-first MCP capability pilot using local stdio MCP
- an OTel-first trace-export abstraction with local operator projections kept canonical
- a durable pilot boundary with diagnostics-only runtime refs
- an Agent Skill-compatible domain-pack export path

The repository still does **not** make external runtime state the public business contract.

## Carry-Over Debt

Still open for `M9`:

- `TD-001`
- `TD-006`
- `TD-007`
- `TD-008`
- `TD-009`
- `TD-010`

## Next Approved Work

The next approved step is:

- `M9 Phase 0 - Post-M8 Rebaseline And Scope Freeze`

What this freeze approves:

- a fresh post-`M8` reassessment
- deciding which breadth is actually justified after the integration cycle

What it does not approve automatically:

- uncontrolled `M9` feature expansion
- promoting experimental external lanes to default paths without a new promotion decision
