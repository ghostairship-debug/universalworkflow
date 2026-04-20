# M13 Freeze Review

## Result

`M13` is complete.

This milestone introduced the first formal multi-agent orchestration baseline while keeping the repository local-first, controller-owned, and truthful about what is still deferred.

## Completed Scope

`M13` closed with these repository-owned outcomes:

- formal orchestration contracts: `AgentRoleType`, `RoleAssignment`, `OrchestrationPlan`, `OrchestrationStep`, and `OrchestrationBarrier`
- a new `project_delivery` preset with `recommended` review policy
- controller-owned orchestration flow: `planner -> coder/researcher parallel batch -> reviewer`
- role-aware fallback behavior that keeps `coder` on `opencode` preference with `shell` fallback and keeps research/review agent-first with safe local fallback
- orchestration projections across `status-detail`, `summary`, `inspection`, and `replay-packet`
- CLI `workflowctl run orchestration <run_id>` and API `GET /runs/{id}/orchestration`
- real self-hosted workflow smoke paths for:
  - `workflowctl config show`
  - `workflowctl capability worker-pools`
  - `project_delivery` end-to-end execution

## Debt Outcome

Active debt after `M13`:

- `TD-019` remains active for hosted remote pools and multi-node scheduling beyond the local-first/loopback baseline
- `TD-020` is now explicitly open for the missing full operator web UI and human control surface

This means `M13` completed a truthful orchestration baseline, not a hosted/distributed final product.

## Validation Evidence

Validated on `2026-04-20` with:

- `python -m pytest -q`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
- `python -m infra.scripts.check_doc_links`

All commands passed.

Key results:

- full test suite: `245 passed`
- offline validation: `overall_passed=true`
- living-doc link audit: `passed=true`

Additional direct command evidence:

- `python -m apps.operator_cli.main config show`
- `python -m apps.operator_cli.main capability worker-pools`
- `python -m apps.operator_cli.main --db-path state/project_demo.db run create --goal "Build project delivery demo" --preset project_delivery --prepare --execute`
- `python -m apps.operator_cli.main --db-path state/project_demo.db run orchestration <run_id>`

Note:

- pytest again emitted the Windows temp-directory cleanup `PermissionError` during interpreter shutdown after successful completion; the green test results were not invalidated.

## Current Repository Position

The repository now ships:

- a local-first self-hosted workflow control plane
- explicit ownership topology plus local batch concurrency from `M10`
- configurable external worker-pool boundaries from `M11`
- unified config, durable checkpoint snapshots, and trace diagnostics from `M12`
- a formal multi-agent orchestration baseline from `M13`

The repository does **not** yet ship:

- a full operator web UI
- hosted remote worker pools
- multi-node lease arbitration
- distributed scheduler consensus

## Next Approved Work

Next approved phase:

- `M14 Phase 0 - Post-M13 Rebaseline And Scope Freeze`

Entry instruction:

- keep the next cycle grounded in the real post-`M13` repository state
- treat the orchestration baseline as shipped, but not as permission to skip UI/human-control design discipline
- do not claim hosted/distributed completion until `TD-019` is repaid explicitly
