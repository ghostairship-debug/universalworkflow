# Phase 2 Log

Date: 2026-04-24
Status: completed

What changed:
- added `UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER` as the default-off feature flag for the integrated orchestrator
- kept `effective_config["scheduler_authority"]` present in both modes and added an explicit `enabled` field
- switched the default integrated orchestrator path to a compatibility-preserving local-only `NullSchedulerAuthorityCluster`
- preserved stable `/scheduler/cluster`, Web UI, and `workflowctl scheduler cluster` payload shape in both disabled and quorum-enabled modes
- kept the standalone scheduler-authority API on the quorum path by forcing the cluster flag on inside `apps/scheduler_authority_api/main.py`
- updated API, CLI, Web UI, validation flows, and scheduler-facing tests for dual-mode verification

Verification:
- `python -m pytest -q tests/test_scheduler_authority_api.py --no-cov --basetemp state/.pytest-phase2-auth`
- `python -m pytest -q tests/test_execution_loop.py -k external_worker_pool --no-cov --basetemp state/.pytest-phase2-exec`
- `python -m pytest -q tests/test_api.py -k "scheduler_authority or local_only_mode" --no-cov --basetemp state/.pytest-phase2-api`
- `python -m pytest -q tests/test_cli.py -k scheduler_cluster --no-cov --basetemp state/.pytest-phase2-cli`
- `python -m pytest -q tests/test_web_ui.py tests/test_remote_worker_api.py -k "operator_surfaces or stale_control_plane" --no-cov --basetemp state/.pytest-phase2-web`

Notes:
- targeted validation was run with `--no-cov` because the repository-level `pytest-cov` fail-under threshold is tuned for full-suite runs, not focused slices
- the local-only cluster shim no longer writes authority node or consensus-term rows, which prevents contamination of the standalone quorum authority API when both modes share one SQLite database
