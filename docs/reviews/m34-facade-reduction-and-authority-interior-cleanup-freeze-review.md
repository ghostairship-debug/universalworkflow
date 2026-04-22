# M34 Facade Reduction / Authority Interior Cleanup Freeze Review

Date: 2026-04-22  
Status: accepted

## Summary

`M34 Phase 0` is accepted as a bounded cleanup closeout. Starting from the accepted `M33 Phase 0` baseline, the repository pulled another scheduler-authority support seam out of `OrchestratorService`, pushed authority-oriented aliases deeper into direct payloads and runtime read models, and updated dogfood/validation surfaces so the accepted authority semantics now reach farther into diagnostics without breaking compatibility.

This closeout is not a zero-debt claim. No structural debt is fully retired in `M34`, but both targeted debts receive another honest bounded repayment and the remaining work is carried forward explicitly.

## Landed

- kept the `M34-0B` seam extraction in place:
  - [packages/core_domain/service_scheduler_authority_support.py](../../packages/core_domain/service_scheduler_authority_support.py) now owns scheduler-authority payload shaping, dispatch-context shaping, and arbitration update assembly behind the `OrchestratorService` facade
- renamed the remaining private scheduler-authority helper symbols toward authority-oriented wording where the change stayed implementation-only
- propagated additive `authority_term_no` / `decision_index` aliases deeper into:
  - direct scheduler-authority committed-lease payloads
  - runtime-state `scheduler_authority` payloads
  - cluster-summary and arbitration-provenance read models
  - worker dispatch context, remote-worker execution targets, and lease-renewal diagnostics
- updated [packages/core_domain/service_projection.py](../../packages/core_domain/service_projection.py) so `status-detail`, `operator-view`, and related packetized read surfaces stop bypassing the new alias-shaping seam
- refreshed offline validation read checks to match the current authority-oriented UI wording and nested cluster-summary shape

## Validation

- targeted scheduler-authority / API / remote-worker / execution-loop regression passed:
  - `171 passed`
- offline validation passed after refreshing the authority-oriented read checks:
  - `python -m infra.scripts.offline_validation --skip-offline-probe --report-path state/offline_validation_report.json`
  - `overall_passed: true`
- full repository regression passed:
  - `python -m pytest -q --basetemp state/.pytest-final-<pid>`
  - `282 passed`
- documentation link validation passed:
  - `python -m infra.scripts.check_doc_links`

## Workflow Dogfood

Using dedicated local DBs under `state/`, workflow dogfood covered:

- shipped orchestration path
  - CLI `run create --goal "M34 project dogfood" --preset project_delivery --prepare --execute`
  - final run status: `completed`
  - orchestration cluster: `dev_cluster`
  - planner / coder / researcher / reviewer child lanes completed
- scheduler-authority / operator read path
  - `python -m infra.scripts.run_cluster_cutover_demo --db-path state/cluster_cutover_demo.db --report-path state/cluster_cutover_demo_report.json`
  - dogfood remote worker dispatch mode: `remote_http`
  - takeover committed owner moved to `control_plane_beta`
  - stale callback returned `409` with `scheduler_arbitration_error`
  - operator handoff count: `1`
  - operator authority-topology node count: `4`

## What Is Now True

- `OrchestratorService` still exists as the public facade, but scheduler-authority shaping and arbitration assembly now sit behind a more honest bounded delegate seam
- scheduler-authority compatibility surfaces still preserve `term_no` / `commit_index`, but the authority-oriented aliases now reach deeper into direct scheduler responses, projections, dispatch context, and worker diagnostics
- `status-detail`, `operator-view`, and dogfood validation now read the same authority-oriented shapes that the runtime produces
- accepted `M34 Phase 0` is now the latest completed bounded baseline
- no post-`M34` bounded phase is open yet

## Repaid In M34 Phase 0

- no structural debt was fully repaid in `M34 Phase 0`

## Carried Forward

- `TD-STRUCT-001`
  - partially repaid
  - `OrchestratorService` lost another bounded scheduler-authority seam, but it still concentrates broader cross-plane wiring and helper logic
- `TD-STRUCT-003`
  - partially repaid
  - internal helper naming, projection payloads, dispatch context, and worker diagnostics are now more authority-oriented, but storage-backed models/tables and persisted event vocabulary still retain consensus-era names
- `TD-STRUCT-005`
  - deferred
  - capability health still needs fuller runtime-backed telemetry
- `TD-STRUCT-006`
  - deferred
  - governed promotion of future platform-object material still lacks a fuller reusable mechanism

## Residual Risk

- full regression is green, but the pre-existing SQLite `ResourceWarning` noise still appears in parts of the suite
- this warning set was not introduced by `M34` and did not prevent a green full-suite closeout
- treat it as hygiene debt unless it escalates into instability, flaky tests, or hidden correctness failures
