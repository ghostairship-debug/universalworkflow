# Universal Agentic Workflow OS

This repository now contains the local-first runtime for the Universal Agentic Workflow OS. It keeps SQLite as the only persistence layer, preserves the `RuntimeGateway` boundary, supports deterministic preset suggestion, public `compile / recompile / resume` surfaces, `HandoffLite` persistence, four executable run-level review policies (`auto_only`, `recommended`, `human_required`, `mandatory`), a multi-adapter runtime boundary through `WorkerRouter`, `ShellAdapter`, `OpenCodeAdapter`, and `NoopAdapter`, a concrete `CapabilityRegistry`, one platformized seed-backed `Domain Pack` baseline, persisted `Memory` and `Simulation` baselines, an opt-in OpenAI-backed `RuntimeGateway`, a read-mostly operator TUI, plus local claim / worker-lease guards with reconcile-aware stale-claim repair.

## Environment

- Python 3.13+
- Windows, macOS, or Linux shell access
- No external database required

## Installation

Install the package plus its runtime dependencies:

```bash
pip install -e .
```

If you also want the test toolchain:

```bash
pip install -e ".[dev]"
```

## Quick start

If GNU Make is available:

```bash
make reset-db
make smoke
```

If GNU Make is not available:

```bash
python -m infra.scripts.manage --db-path state/workflow.db reset-db
python -m infra.scripts.manage --db-path state/workflow.db smoke
python -m infra.scripts.manage --db-path state/workflow.db demo
```

## Current repository status

- Milestone baseline: through `M8`, complete
- Validated baseline note:
  - the shipped-shape claims below refer to the latest validated closeout baseline, not necessarily every transient in-progress worktree state
- Current shipped shape:
  - local-first CLI/API runtime
  - native deterministic, borrowed agent, and durable-pilot execution lanes
  - `shell`, `opencode`, `noop`, and feature-flagged `agent` adapter routing
  - router-first capability plane with built-in capability projection and local stdio MCP pilot support
  - OTel-first trace-export abstraction with an optional Langfuse sink
  - one platformized `Domain Pack`
  - persisted `Memory` baseline with retrieval preview and compile-time injection
  - deterministic local `Simulation` baseline with persisted records and selected lifecycle hooks
  - Agent Skill-compatible domain-pack export
- Current planning position:
  - `M8` is complete
  - `M8 Phase 0` through `M8 Phase 7` are complete
  - the next approved work is `M9 Phase 0 - Post-M8 Rebaseline And Scope Freeze`
  - the integrated root-level `M8` development plan is [universal_agentic_workflow_os_M8_phase_plan_v1_0.md](universal_agentic_workflow_os_M8_phase_plan_v1_0.md)
  - the GPT-Pro-driven reassessment of the `M8` plan is [docs/reviews/m8-gpt-pro-reassessment-and-plan-update.md](docs/reviews/m8-gpt-pro-reassessment-and-plan-update.md)
  - the canonical current development guide is [docs/current_development_workflow.md](docs/current_development_workflow.md)
  - the controlling closeout record is [docs/reviews/m8-freeze-review.md](docs/reviews/m8-freeze-review.md)
  - the current `M8` ecosystem reuse assessment is [docs/reviews/m8-ecosystem-reuse-and-wheel-reinvention-assessment.md](docs/reviews/m8-ecosystem-reuse-and-wheel-reinvention-assessment.md)
  - the current external-integration vs continued-self-build strategy is [docs/reviews/m8-external-tool-integration-and-self-build-plan.md](docs/reviews/m8-external-tool-integration-and-self-build-plan.md)
  - the current "do we need another optimization round before M8?" assessment is [docs/reviews/m8-pre-entry-extra-optimization-assessment.md](docs/reviews/m8-pre-entry-extra-optimization-assessment.md)
  - the M8 implementation records now live under `m8_phase_docs/`, `docs/task_cards/m8_phase_*`, and `docs/reviews/m8-phase-*`
  - the completed hardening plan remains [docs/reviews/m7-gemini-opus-pre-m8-synthesis.md](docs/reviews/m7-gemini-opus-pre-m8-synthesis.md)
  - documentation trust and source-package rules now live in [docs/documentation_governance.md](docs/documentation_governance.md) and [docs/source_package_export_policy.md](docs/source_package_export_policy.md)
  - local subprocess trust assumptions now live in [docs/architecture/local_execution_trust_boundary.md](docs/architecture/local_execution_trust_boundary.md)
  - service decomposition evidence now lives in [docs/reviews/pm8-phase-c-service-decomposition-review.md](docs/reviews/pm8-phase-c-service-decomposition-review.md)
  - structured governance sources now live in [docs/governance/README.md](docs/governance/README.md)
  - dependency/version policy now lives in [docs/dependency_locking_policy.md](docs/dependency_locking_policy.md)

## Offline validation

If you want one-shot offline acceptance after disconnecting the machine from the network:

```powershell
powershell -ExecutionPolicy Bypass -File .\infra\scripts\run_offline_validation.ps1
```

The script writes a JSON report to `state/offline_validation_report.json` and verifies:

- offline reachability probes fail
- CLI auto path passes
- CLI human-review path passes
- CLI noop executor path passes
- CLI capability/domain-pack visibility passes
- CLI M8 capability-source / projection / skill-export surfaces pass
- CLI simulation visibility passes
- CLI simulation record persistence passes
- CLI release-readiness surface passes
- CLI reconcile / repair path passes
- smoke flow passes
- API auto path passes
- API human-review path passes
- API noop executor path passes
- API capability/domain-pack visibility passes
- API M8 capability-source / projection / skill-export surfaces pass
- API simulation visibility passes
- API simulation record persistence passes
- API release-readiness surface passes
- API reconcile / repair path passes

The current green closeout baseline is:

- `pytest -q`
  - `225 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`
- `python -m infra.scripts.check_doc_links`
  - `passed=true`
- `python -m infra.scripts.manage --db-path state/cycle_validation.db demo`
  - `status=completed`
- `python -m apps.operator_cli.main --db-path state/cycle_validation.db tui --once`
  - renders a single dashboard snapshot successfully
- `python -m pip install -e . --no-deps`
  - succeeds after the package-discovery fix

## Common commands

If the project is installed as a package, the `workflowctl` entry point is available. Otherwise use `python -m apps.operator_cli.main`.

- `workflowctl --db-path state/workflow.db preset list`
- `workflowctl --db-path state/workflow.db domain-pack list --json`
- `workflowctl --db-path state/workflow.db domain-pack resolve --preset feature_delivery --task-kind shell_exec`
- `workflowctl --db-path state/workflow.db domain-pack validate`
- `workflowctl --db-path state/workflow.db capability list`
- `workflowctl --db-path state/workflow.db capability sources`
- `workflowctl --db-path state/workflow.db capability mcp-profiles`
- `workflowctl --db-path state/workflow.db capability projection --preset research_spike_reviewable`
- `workflowctl --db-path state/workflow.db simulation policy list`
- `workflowctl --db-path state/workflow.db memory namespace list`
- `workflowctl --db-path state/workflow.db domain-pack export-skill --domain-pack-id software_delivery_pack`
- `workflowctl --db-path state/workflow.db run suggest-presets --goal "Research runtime strategy"`
- `workflowctl governance tech-debt`
- `workflowctl governance review-policy`
- `workflowctl --db-path state/workflow.db governance release-readiness`
- `workflowctl governance domain-pack`
- `workflowctl --db-path state/workflow.db tui --once`
- `workflowctl --db-path state/workflow.db run create --goal "Build a smoke artifact" --preset feature_delivery --prepare --execute`
- `workflowctl --db-path state/workflow.db run create --goal "Ship with advisory escalation" --preset advisory_delivery`
- `workflowctl --db-path state/workflow.db run create --goal "Research a design choice" --preset research_spike`
- `workflowctl --db-path state/workflow.db run create --goal "Ship with mandatory sign-off" --preset guarded_delivery --prepare --execute`
- `workflowctl --db-path state/workflow.db run compile <run_id>`
- `workflowctl --db-path state/workflow.db run compile <run_id> --adapter opencode`
- `workflowctl --db-path state/workflow.db run compile <run_id> --memory-item-id <memory_item_id>`
- `workflowctl --db-path state/workflow.db run compile <run_id> --task-kind noop`
- `workflowctl --db-path state/workflow.db run resume <run_id>`
- `workflowctl --db-path state/workflow.db run approve <run_id>`
- `workflowctl --db-path state/workflow.db run reject <run_id>`
- `workflowctl --db-path state/workflow.db run status-detail <run_id>`
- `workflowctl --db-path state/workflow.db run summary <run_id>`
- `workflowctl --db-path state/workflow.db run simulation <run_id>`
- `workflowctl --db-path state/workflow.db run record-simulation <run_id>`
- `workflowctl --db-path state/workflow.db run simulations <run_id>`
- `workflowctl --db-path state/workflow.db run event-inspection <run_id>`
- `workflowctl --db-path state/workflow.db run audit-report <run_id>`
- `workflowctl --db-path state/workflow.db run memory-candidates <run_id>`
- `workflowctl --db-path state/workflow.db run materialize-memory <run_id> --candidate-id <candidate_id>`
- `workflowctl --db-path state/workflow.db run memory-items <run_id>`
- `python -m infra.scripts.check_doc_links`
- `python -m infra.scripts.export_source_package --dry-run`
- `python -m infra.scripts.pre_m8_gates`
- `workflowctl --db-path state/workflow.db memory item list --namespace policy`
- `workflowctl --db-path state/workflow.db memory retrieve-preview --preset feature_delivery --namespace policy`
- `workflowctl --db-path state/workflow.db run attempts <run_id>`
- `workflowctl --db-path state/workflow.db run claims <run_id>`
- `workflowctl --db-path state/workflow.db run leases <run_id>`
- `workflowctl --db-path state/workflow.db run snapshots <run_id>`
- `workflowctl --db-path state/workflow.db run budget <run_id>`
- `workflowctl --db-path state/workflow.db run inspect <run_id>`
- `workflowctl --db-path state/workflow.db run reconcile <run_id>`
- `workflowctl --db-path state/workflow.db run reconcile <run_id> --apply`
- `workflowctl --db-path state/workflow.db run handoffs <run_id>`
- `workflowctl --db-path state/workflow.db task evidence <runtime_task_id>`
- `workflowctl --db-path state/workflow.db run cancel <run_id>`
- `workflowctl --db-path state/workflow.db db reset`

## Live LLM gateway

The default runtime provider remains `null`, so smoke tests and offline validation still work without any model access. This direct OpenAI path is an opt-in live provider lane, not the only model-backed execution route in the repository.

To enable the live OpenAI-backed gateway:

```powershell
$env:WORKFLOW_RUNTIME_GATEWAY="openai"
$env:OPENAI_API_KEY="<your key>"
$env:WORKFLOW_OPENAI_MODEL="gpt-5.4-mini"
$env:WORKFLOW_OPENAI_REASONING_EFFORT="low"
```

Then run a normal lifecycle:

```powershell
python -m apps.operator_cli.main --db-path state/workflow.db run create --goal "Produce an execution brief" --preset feature_delivery
python -m apps.operator_cli.main --db-path state/workflow.db run compile <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run resume <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run status-detail <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db task evidence <runtime_task_id>
```

When the live gateway is active:

- `status` / `status-detail` / `inspection` expose a `runtime_gateway` block
- the latest runtime state may contain `runtime_brief`, `llm_model`, and `llm_response_id`
- shell-generated artifacts can include `runtime_gateway`, `runtime_model`, and `runtime_brief`

If `WORKFLOW_RUNTIME_GATEWAY` is unset, empty, `null`, `none`, or `disabled`, the service falls back to `NullRuntimeGateway`.

## M8 external lanes

`M8` external lanes are opt-in and disabled by default.

Feature flags:

```powershell
$env:UAWO_ENABLE_AGENT_LANE="1"
$env:UAWO_ENABLE_MCP_SOURCE="1"
$env:UAWO_ENABLE_EXTERNAL_TRACE_EXPORT="1"
$env:UAWO_ENABLE_DURABLE_PILOT="1"
$env:UAWO_ENABLE_SKILL_EXPORT="1"
```

Optional runtime dependencies for the borrowed agent and LangGraph-oriented durable pilot lanes:

```powershell
python -m pip install "langchain>=1.0.0,<2.0.0" "langchain-openai>=1.0.0,<2.0.0" "langgraph>=1.0.0,<2.0.0"
```

The base package metadata is validated against `openai>=2.26.0,<3.0.0`, which matches the current live gateway and `langchain-openai` runtime baseline.

Borrowed-agent capability preview:

```powershell
$env:UAWO_ENABLE_AGENT_LANE="1"
$env:UAWO_ENABLE_MCP_SOURCE="1"
workflowctl --db-path state/workflow.db capability projection --preset research_spike_reviewable
```

Skill export:

```powershell
$env:UAWO_ENABLE_SKILL_EXPORT="1"
workflowctl --db-path state/workflow.db domain-pack export-skill --domain-pack-id software_delivery_pack
```

## CLI-backed GPT route

The current CLI-first GPT-capable lane is `OpenCodeAdapter`.

Requirements:

- `opencode` available on `PATH`
- local `opencode` authentication already configured on the machine

Useful environment overrides:

```powershell
$env:WORKFLOW_OPENCODE_MODEL="openai/gpt-5.4-mini"
$env:WORKFLOW_OPENCODE_VARIANT="<optional variant>"
```

Example flow:

```powershell
python -m apps.operator_cli.main --db-path state/workflow.db capability list
python -m apps.operator_cli.main --db-path state/workflow.db run create --goal "Produce a GPT-backed artifact through opencode" --preset feature_delivery
python -m apps.operator_cli.main --db-path state/workflow.db run compile <run_id> --adapter opencode
python -m apps.operator_cli.main --db-path state/workflow.db run resume <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run status-detail <run_id>
```

The adapter currently uses `opencode run --format json --dir ... --pure` and freezes the chosen adapter into compile-time capability resolution so later status/detail views remain stable.

Local trust boundary notes:

- subprocess-backed adapters now enforce declared timeout budgets
- subprocess-backed adapters inherit an allowlisted subset of the parent environment plus explicit workflow packet values
- compile-generated Python commands use the current interpreter via `sys.executable`
- see [docs/architecture/local_execution_trust_boundary.md](docs/architecture/local_execution_trust_boundary.md)

## Operator TUI

Launch the read-mostly terminal dashboard with:

```bash
python -m apps.operator_cli.main --db-path state/workflow.db tui
```

For a single non-interactive render:

```bash
python -m apps.operator_cli.main --db-path state/workflow.db tui --once
```

Useful flags:

- `--run-id <run_id>` to focus a specific run
- `--limit <n>` to change the recent-run list size
- `--refresh-seconds <seconds>` to slow down or speed up watch mode
- `--cycles <n>` to auto-stop after a fixed number of refreshes

On Windows terminals with a non-UTF-8 code page, run `chcp 65001` first if the dashboard border or table text looks garbled.

## Manual paths

Auto-review path:

```bash
python -m apps.operator_cli.main --db-path state/workflow.db db reset
python -m apps.operator_cli.main --db-path state/workflow.db run create --goal "Build a smoke artifact" --preset feature_delivery
python -m apps.operator_cli.main --db-path state/workflow.db domain-pack list --json
python -m apps.operator_cli.main --db-path state/workflow.db domain-pack resolve --preset feature_delivery --task-kind shell_exec
python -m apps.operator_cli.main --db-path state/workflow.db domain-pack validate
python -m apps.operator_cli.main --db-path state/workflow.db governance domain-pack
python -m apps.operator_cli.main --db-path state/workflow.db capability list
python -m apps.operator_cli.main --db-path state/workflow.db run compile <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run status-detail <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run summary <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run simulation <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run record-simulation <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run simulations <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run event-inspection <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run audit-report <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run attempts <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run snapshots <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run budget <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run claims <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run leases <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run inspect <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run resume <run_id>
```

Human-review path:

```bash
python -m apps.operator_cli.main --db-path state/workflow.db run create --goal "Research a design choice" --preset research_spike
python -m apps.operator_cli.main --db-path state/workflow.db run compile <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run status-detail <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run summary <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run simulation <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run inspect <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run resume <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run event-inspection <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run audit-report <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run attempts <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run claims <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run leases <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run snapshots <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run budget <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run approve <run_id>
```

Recommended-review path (`advisory_delivery`):

```bash
python -m apps.operator_cli.main --db-path state/workflow.db run create --goal "Advisory delivery" --preset advisory_delivery
python -m apps.operator_cli.main --db-path state/workflow.db run compile <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run status-detail <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run resume <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run status-detail <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run approve <run_id>
```

Mandatory-review path (`guarded_delivery`):

```bash
python -m apps.operator_cli.main --db-path state/workflow.db run create --goal "Guarded delivery" --preset guarded_delivery
python -m apps.operator_cli.main --db-path state/workflow.db run compile <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run resume <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run status-detail <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run approve <run_id>
```

Second executor path (`noop` on `research_spike`):

```bash
python -m apps.operator_cli.main --db-path state/workflow.db run create --goal "Research without shell execution" --preset research_spike
python -m apps.operator_cli.main --db-path state/workflow.db run compile <run_id> --task-kind noop
python -m apps.operator_cli.main --db-path state/workflow.db run status-detail <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run resume <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run leases <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db task evidence <runtime_task_id>
python -m apps.operator_cli.main --db-path state/workflow.db run approve <run_id>
```

Minimal Domain Pack path (`software_delivery_pack` on `feature_delivery` / `advisory_delivery` / `guarded_delivery`):

```bash
python -m apps.operator_cli.main --db-path state/workflow.db domain-pack list --json
python -m apps.operator_cli.main --db-path state/workflow.db capability list
python -m apps.operator_cli.main --db-path state/workflow.db run create --goal "Ship a software-delivery artifact" --preset feature_delivery
python -m apps.operator_cli.main --db-path state/workflow.db run compile <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run status-detail <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run resume <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db task evidence <runtime_task_id>
```

TUI path:

```bash
python -m apps.operator_cli.main --db-path state/workflow.db db reset
python -m apps.operator_cli.main --db-path state/workflow.db run create --goal "Watch the dashboard" --preset feature_delivery --prepare --execute
python -m apps.operator_cli.main --db-path state/workflow.db tui --once
```

Repair path:

```bash
python -m apps.operator_cli.main --db-path state/workflow.db run inspect <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run summary <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run attempts <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run reconcile <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run reconcile <run_id> --apply
python -m apps.operator_cli.main --db-path state/workflow.db run claims <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run leases <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run snapshots <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run inspect <run_id>
```

## API entry point

Run the orchestrator API locally with:

```bash
python -m infra.scripts.manage --db-path state/workflow.db dev
```

The current routes are:

- `POST /runs`
- `GET /runs/{id}`
- `POST /runs/{id}/compile`
- `POST /runs/{id}/recompile`
- `POST /runs/{id}/resume`
- `POST /runs/{id}/approve`
- `POST /runs/{id}/reject`
- `GET /runs/{id}/timeline`
- `GET /runs/{id}/status-detail`
- `GET /runs/{id}/summary`
- `GET /runs/{id}/simulation`
- `POST /runs/{id}/simulation-records`
- `GET /runs/{id}/simulation-records`
- `GET /runs/{id}/event-inspection`
- `GET /runs/{id}/audit-report`
- `GET /runs/{id}/memory-candidates`
- `POST /runs/{id}/memory-items`
- `GET /runs/{id}/memory-items`
- `GET /memory/retrieval-preview`
- `GET /runs/{id}/inspection`
- `GET /runs/{id}/attempts`
- `GET /runs/{id}/claims`
- `GET /runs/{id}/leases`
- `GET /runs/{id}/snapshots`
- `GET /runs/{id}/budget`
- `POST /runs/{id}/reconcile`
- `GET /runs/{id}/handoffs`
- `GET /presets`
- `GET /domain-packs`
- `GET /domain-packs/resolve`
- `GET /domain-packs/validate`
- `GET /capability-routes`
- `GET /simulation/policies`
- `GET /memory/namespaces`
- `GET /memory/items`
- `GET /governance/tech-debt`
- `GET /governance/review-policy`
- `GET /governance/release-readiness`
- `GET /governance/domain-packs`
- `GET /tasks/{id}/evidence`

`POST /runs/{id}/compile` and `POST /runs/{id}/recompile` may optionally receive a JSON body such as `{"task_kind": "noop"}` when the selected preset allows that task kind, `{"adapter_name": "opencode"}` when a capability route should be pinned explicitly, or `{"memory_item_ids": ["memory_..."]}` for the explicit memory-aware compile bridge.

## Notes

- `POST /runs` only creates the run and records preset selection.
- `compile`, `recompile`, `resume`, `approve`, and `reject` are explicit lifecycle steps in M1.
- `research_spike` can be compiled with `--task-kind noop`; `feature_delivery` rejects `noop` with the structured error code `task_kind_not_allowed`.
- `feature_delivery` can be compiled through `shell` or `opencode`; compile/recompile pin the selected adapter into the run's capability resolution.
- `feature_delivery` stays `auto_only`.
- `feature_delivery`, `advisory_delivery`, and `guarded_delivery` now resolve the platformized `software_delivery_pack`; compile/status surfaces project the selected domain pack and adapter route.
- `advisory_delivery` uses `recommended`: auto pass completes, auto fail escalates into `awaiting_review`.
- `research_spike` uses `human_required`: execution completes, then it waits for human review without an auto-review gate.
- `guarded_delivery` uses `mandatory`: auto review always runs, but the run still waits for human sign-off.
- `status-detail` now includes operator-facing diagnostics such as `failure_reason`, `waiting_reason`, `last_runtime_state`, `recoverability_hint`, `active_claims`, `latest_claim`, and `latest_snapshot`.
- `status` now also includes `latest_simulation_record`, so the most recent simulation lineage source is visible without switching to the full detail payload.
- `status` / `status-detail` / `inspection` now also expose the active `runtime_gateway` projection so live LLM activation is visible without guessing from env vars.
- `status-detail` and `inspection` now also include `runtime_attempts`, `current_runtime_attempt`, `latest_runtime_attempt`, and `runtime_attempt_projection`.
- when the OpenAI-backed gateway is enabled, the resumed runtime state can carry a short `runtime_brief`, and shell artifacts can persist that brief alongside `runtime_gateway` / `runtime_model`.
- `run summary` and `GET /runs/{id}/summary` provide a concise operator view of failure taxonomy, review state, timeline digest, and ownership projections.
- `run simulation` and `GET /runs/{id}/simulation` expose the first deterministic local simulation report, including whether policy triggered and which checks failed.
- `run record-simulation` / `POST /runs/{id}/simulation-records` persist the current simulation report as an auditable local record.
- `run simulations` / `GET /runs/{id}/simulation-records` expose the persisted simulation history for a run, including whether each record came from a manual request or a selected lifecycle hook.
- selected lifecycle control points now auto-record simulation for triggered policies at `cancelled`, `awaiting_review`, and terminal completion/failure.
- `run event-inspection` and `GET /runs/{id}/event-inspection` provide a richer event digest plus closure-audit framing for completed, awaiting-review, and terminal runs.
- `run audit-report` and `GET /runs/{id}/audit-report` export a review-ready audit bundle that combines summary, event inspection, state inspection, and recent timeline context.
- `simulation policy list` and `GET /simulation/policies` expose the seed-backed simulation policy catalog that currently gates which presets receive the local simulation slice.
- `governance tech-debt` and `GET /governance/tech-debt` expose the current technical-debt registry as a structured governance report.
- `governance review-policy` and `GET /governance/review-policy` expose the current supported review-policy catalog, operator state matrix, and future reference-only expansion candidates.
- `governance release-readiness` and `GET /governance/release-readiness` expose a release-shaped closeout view that combines validation, capability routes, platformized domain-pack baseline, and milestone gates.
- `governance domain-pack` and `GET /governance/domain-packs` expose the current domain-pack platform report with match/capability/compile/runtime sections.
- `domain-pack list` / `GET /domain-packs` expose the currently enabled domain-pack catalog with platform-shaped sections.
- `domain-pack resolve` / `GET /domain-packs/resolve` preview the selected pack and adapter before compile.
- `domain-pack validate` / `GET /domain-packs/validate` expose a structured catalog-validation report for preset/task-kind/adapter consistency.
- `capability list` / `GET /capability-routes` expose the concrete `CapabilityRegistry` routes that bind task kinds to adapters.
- `memory namespace list` / `GET /memory/namespaces` expose the seed-backed memory namespace catalog.
- `run memory-candidates` / `GET /runs/{id}/memory-candidates` expose read-only memory candidates derived from run summary, review, evidence, and audit state.
- `run materialize-memory` / `POST /runs/{id}/memory-items` turn a selected run memory candidate into the first persisted `memory_item` baseline.
- `run memory-items` / `GET /runs/{id}/memory-items` / `memory item list` / `GET /memory/items` expose stored memory items by run and namespace.
- `memory retrieve-preview` / `GET /memory/retrieval-preview` expose a non-injective retrieval brief preview over stored memory items, with optional namespace and explicit item-id filters.
- `run compile --memory-item-id ...` / `POST /runs/{id}/compile` with `memory_item_ids` turns retrieval preview into an explicit, opt-in compile-time memory brief; default compile behavior stays unchanged when no memory items are passed.
- `workflowctl tui` provides a read-mostly terminal dashboard for recent runs, focus detail, runtime-gateway status, and timeline tail.
- `python -m infra.scripts.manage --db-path <db> demo` runs the canonical local golden demo packet across auto, human-review, recommended, mandatory, and noop paths on a fresh database.
- `run attempts` and `GET /runs/{id}/attempts` expose explicit compile/resume/recompile lineage for interrupted or superseded execution debugging.
- `run claims` and `GET /runs/{id}/claims` expose persisted claim history for local debugging and audit.
- `run leases` and `GET /runs/{id}/leases` expose persisted worker-lease history for heartbeat-aware ownership debugging.
- `run snapshots` and `GET /runs/{id}/snapshots` expose replay-friendly checkpoint history for recovery analysis.
- `run budget` and `GET /runs/{id}/budget` expose persisted budget-ledger state plus remaining retry / timeout headroom.
- `inspection` is a read-only dry-run surface that flags inconsistent states without mutating the database.
- `resume` acquires a local runtime claim before execution; terminal and review-handoff paths release it explicitly.
- `reconcile` reuses the same bad-state catalog, but only applies explicit safe repairs; manual-only problems still fail with structured errors.
- Claim semantics are local-only lease guards. They improve correctness and auditability, but they are not distributed locking or full parallel scheduling.
- Worker-lease semantics are local-only worker ownership projections. They improve heartbeat and interrupt-safety diagnostics, but they are not a distributed lease manager.
- Snapshot semantics are recovery-oriented projections. They improve checkpoint visibility, but they are not a full replay engine.
- Smoke clears known LLM API key variables before execution and restores them afterward.
- See [docs/smoke/m1-smoke.md](docs/smoke/m1-smoke.md) for the M1 acceptance flow.
