# M14 Phase 4 - Governance, Config, And UX Hardening

Status: complete

## Goal

Promote governance and config visibility into the Web operator surface and close the remaining product-surface debt for `M14`.

## Completed Outputs

- governance page for debt, policy, metrics, alerts, readiness, and domain-pack posture
- config page for effective config and precedence visibility
- README/workflow docs updated to elevate Web UI as the formal operator surface
- `TD-020` retired

## Verification

- `python -m pytest tests/test_web_ui.py tests/test_api.py -q`
- `python -m infra.scripts.check_doc_links`

## Next Phase

- `M14 Phase 5 - Freeze Review And Scope Closure`
