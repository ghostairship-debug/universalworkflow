# M33 Orchestration / Service Contraction Freeze Review

Date: 2026-04-22  
Status: accepted

## Summary

`M33 Phase 0` is accepted as a bounded contraction closeout. The repository used the accepted `M32 Phase 0` foundation to contract the remaining `project_delivery`-shaped orchestration assumptions, extract another bounded orchestration delegate from `OrchestratorService`, and make scheduler-authority read surfaces more semantically honest without breaking compatibility.

This closeout is not a zero-debt claim. It records one repaid structural debt, two partial repayments, and an explicit carry-forward for the remaining bounded debt.

## Landed

- added [packages/core_domain/service_orchestration.py](../../packages/core_domain/service_orchestration.py) as the shared orchestration-plan construction and runtime execution delegate
- moved `project_delivery` and `guarded_project_delivery` default orchestration plans onto cluster-template-driven plan construction
- switched interaction preview and orchestration plan-graph projection onto the same canonical plan builder used by execution
- replaced the previous hardcoded multi-role execution branch with plan-step-driven orchestration execution
- preserved shipped compatibility for `project_delivery`, `guarded_project_delivery`, `DevCluster`, CLI, API, packet families, and the minimum workbench preview
- added additive scheduler-authority aliases:
  - `authority_node_id`
  - `authority_term_no`
  - `decision_index`
- updated operator-facing Web UI wording from legacy `Cluster Topology` / `Leader` / `Term` / `Commit Index` labels to `Authority Topology` / `Authority Node` / `Authority Term` / `Decision Index`

## Validation

- targeted orchestration and scheduler-authority regression passed:
  - `9 passed`
- full repository regression passed:
  - `python -m pytest -q --basetemp state/.pytest-full-<pid>`
  - `282 passed`

## Workflow Dogfood

Using a dedicated local DB (`state/m33_dogfood.db`), workflow dogfood covered:

- `project_delivery`
  - CLI `run create / compile / resume`
  - final run status: `completed`
  - orchestration cluster: `dev_cluster`
- `guarded_project_delivery`
  - CLI `run create / compile / resume`
  - final run status: `awaiting_review`
  - orchestration cluster: `dev_cluster`
- cluster-aware interaction path
  - CLI `interaction create-session / plan-draft / launch --execute`
  - interaction session status moved from `ready_to_launch` to `launched`
  - launched run status: `completed`
  - selected cluster: `dev_cluster`

## What Is Now True

- orchestration preview, default planning, and runtime execution now share one canonical orchestration-plan construction path for the shipped multi-role presets
- `OrchestratorService` still acts as the public facade, but orchestration compile/execute helpers now live behind a bounded delegate
- scheduler-authority public/operator surfaces now expose more honest authority-oriented wording without breaking the older compatibility keys
- accepted `M33 Phase 0` is now the latest completed bounded baseline
- no post-`M33` bounded phase is open yet

## Repaid In M33 Phase 0

- `TD-STRUCT-004`
  - residual `project_delivery`-shaped orchestration execution assumptions were contracted behind a shared orchestration service and canonical plan builder

## Carried Forward

- `TD-STRUCT-001`
  - partially repaid
  - `OrchestratorService` still concentrates broader cross-plane wiring beyond orchestration
- `TD-STRUCT-003`
  - partially repaid
  - additive authority aliases and honest wording landed, but legacy internal storage/event naming still remains
- `TD-STRUCT-005`
  - deferred
  - capability health still needs fuller runtime-backed telemetry
- `TD-STRUCT-006`
  - deferred
  - governed promotion of future platform-object material still lacks a fuller reusable mechanism

## Residual Risk

- full regression is green, but existing SQLite `ResourceWarning` noise still appears during some tests
- this warning set predates the `M33` changes and did not cause a red full-suite run once `pytest` used an isolated `--basetemp`
- treat it as hygiene debt until it becomes a real stability or correctness blocker
