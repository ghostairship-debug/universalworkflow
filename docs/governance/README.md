# Governance Structured Sources

This directory stores the canonical machine-readable governance inputs used by runtime reporting surfaces.

Current files:

- `tech_debt_registry.json`
- `review_policy_cases.json`

Usage rule:

- runtime/governance code should prefer these structured sources
- Markdown governance docs remain the operator-readable mirror and compatibility override path
- if the structured and Markdown sources diverge, the active phase review should reconcile them before a freeze claims the repository is current
