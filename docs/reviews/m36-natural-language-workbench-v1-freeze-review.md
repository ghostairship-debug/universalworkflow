# M36 Natural-Language Workbench V1 Freeze Review

Date: 2026-04-24
Status: accepted

## Summary

`M36` is accepted as complete. Starting from accepted `M36 Phase 0`, the repository turned the minimum workbench preview into a usable natural-language workbench v1 while preserving the operator/workbench split and keeping review authority explicit.

## Landed

- completed `M36 Phase 1` through:
  - [m36_phase_docs/phase_1_conversational_workbench_flow.md](../../m36_phase_docs/phase_1_conversational_workbench_flow.md)
  - [docs/task_cards/m36_phase_1_task_cards.md](../task_cards/m36_phase_1_task_cards.md)
- completed `M36 Phase 2` through:
  - [m36_phase_docs/phase_2_followup_review_and_closeout.md](../../m36_phase_docs/phase_2_followup_review_and_closeout.md)
  - [docs/task_cards/m36_phase_2_task_cards.md](../task_cards/m36_phase_2_task_cards.md)
- expanded the workbench flow with richer goal intake, recent-session visibility, execution-default projection, active-run checkpoint visibility, and persistent follow-up queue support
- kept CLI and API interaction-session surfaces additive and aligned with the workbench

## Validation

- targeted interaction/workbench/API/CLI regression coverage passed:
  - `python -m pytest -q tests/test_api.py -k "interaction_session" --no-cov --basetemp state/.pytest-m36-api`
  - `python -m pytest -q tests/test_cli.py -k "interaction_profiles_clusters_and_session_flow" --no-cov --basetemp state/.pytest-m36-cli`
  - `python -m pytest -q tests/test_web_ui.py -k "workbench_post_flow" --no-cov --basetemp state/.pytest-m36-web`
- full repository regression passed:
  - `python -m pytest -q`
  - `299 passed`
- offline validation passed:
  - `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`
- documentation link validation passed:
  - `python -m infra.scripts.check_doc_links`
  - `passed=true`

## What Is Now True

- `M36` is complete
- the built-in Web UI now includes a usable workbench v1 rather than only a minimum preview
- natural-language launch now has coherent Web, CLI, and API entry points
- persistent follow-up capture now stays inside the same interaction-session path
