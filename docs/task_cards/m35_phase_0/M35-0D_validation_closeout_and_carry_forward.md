# M35-0D Validation, Closeout, And Carry-Forward

Status: completed

## Goal

Close `M35 Phase 0` with targeted regression evidence, workflow dogfood, and an honest carry-forward judgment for the remaining structural debt.

## Acceptance

- targeted validation for interaction/config/API/CLI/Web surfaces passes
- workflow dogfood covers at least one implementation-oriented `dev_cluster` path and one evidence-oriented `research_cluster` path
- doc link validation passes
- phase closeout/freeze review is written
- debt registry updates record what remains deferred or carried forward after the phase
- no later `M35` phase is opened until `M35 Phase 0` closeout evidence is recorded honestly

## Notes

- closeout is not complete unless the repository can explain the frozen contract, the frozen precedence line, the validation evidence, and the remaining deferred debt in one coherent story
- the expected closeout validation set is:
  - `pytest tests/test_api.py tests/test_cli.py tests/test_web_ui.py tests/test_governance.py --no-cov`
  - `pytest`
  - `python -m infra.scripts.check_doc_links`
- the expected workflow dogfood set is:
  - one `interaction create-session` or launch path using `project_delivery` with `dev_cluster`
  - one `interaction create-session` or launch path using `research_spike_reviewable` with `research_cluster`

## Result

- targeted execution-profile regression passed:
  - `pytest tests/test_execution_loop.py --no-cov --basetemp state/.pytest-tmp-m35-loop -q`
  - `104 passed`
- targeted API and CLI regression for the new execution-profile surfaces passed:
  - `pytest tests/test_api.py -k "api_exposes_effective_config_and_worker_pools or api_compile_and_status_detail_are_public_in_m1 or api_exposes_capability_mcp_sources_for_agent_lane" --no-cov --basetemp state/.pytest-tmp-m35-api -q`
  - `pytest tests/test_cli.py -k "cli_config_show_reads_workflow_toml_and_worker_pools or cli_compile_recompile_status_detail_and_handoffs or projection" --no-cov --basetemp state/.pytest-tmp-m35-cli -q`
  - selected API subset passed
  - `6 passed`
- full repository regression passed:
  - `pytest --basetemp state/.pytest-tmp-m35-all`
  - `289 passed`
- offline validation passed:
  - `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed: true`
- doc link validation passed:
  - `python -m infra.scripts.check_doc_links`
- workflow dogfood used the dedicated phase DB at `state/workspaces/ed57374f70/m35_phase0.db` and covered both required kickoff paths:
  - `intent_session_259ebdada96e` with `project_delivery` + `dev_cluster`
  - `intent_session_60b818313eb1` with `research_spike_reviewable` + `research_cluster`
- wrote the accepted milestone closeout in [docs/reviews/m35-role-execution-productization-freeze-review.md](../../reviews/m35-role-execution-productization-freeze-review.md)
- carry-forward remains explicit and unchanged:
  - `TD-STRUCT-001`: bounded carry-forward, partially repaid
  - `TD-STRUCT-003`: bounded carry-forward, partially repaid
  - `TD-STRUCT-005`: deferred to `M38-M39`
  - `TD-STRUCT-006`: deferred to `M39`
