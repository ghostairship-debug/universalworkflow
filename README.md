# Universal Agentic Workflow OS

This repository now contains the local-first runtime for the Universal Agentic Workflow OS. It keeps SQLite as the only persistence layer, preserves the `RuntimeGateway` boundary, supports deterministic preset suggestion, public `compile / recompile / resume` surfaces, `HandoffLite` persistence, five executable run-level review policies (`auto_only`, `optional`, `recommended`, `human_required`, `mandatory`), a multi-adapter runtime boundary through `WorkerRouter`, `ShellAdapter`, `OpenCodeAdapter`, and `NoopAdapter`, a concrete `CapabilityRegistry`, one platformized seed-backed `Domain Pack` baseline, persisted `Memory` and `Simulation` baselines, replay-packet and run-metrics projections, governance metrics/alerts, explicit ownership-topology lineage, local batch-barrier / parallel-batch resume support, unified `workflow.toml`-backed configuration, real remote HTTP worker-pool productization, real durable checkpoint snapshots, a shared `project_delivery` / `guarded_project_delivery` orchestration substrate, bounded repo-mutation contracts for semi-automatic workflow-driven development, a single-store quorum-style scheduler-authority layer with committed cross-control-plane lease ownership and takeover lineage, an opt-in OpenAI-backed `RuntimeGateway`, a built-in FastAPI Web operator UI, the existing terminal TUI, plus local claim / worker-lease guards with reconcile-aware stale-claim repair.

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

If you also want the optional MCP pilot support:

```bash
pip install -e ".[mcp]"
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

- Chinese overview:
  - [README.zh-CN.md](README.zh-CN.md)
- Milestone baseline: through accepted `M32 Phase 0`, complete
- Validated baseline note:
  - the shipped-shape claims below refer to the latest validated closeout baseline, not necessarily every transient in-progress worktree state
- Current shipped shape:
  - local-first CLI/API runtime
  - native deterministic, borrowed agent, durable-pilot, and orchestration-aware execution lanes
  - `shell`, `opencode`, `noop`, and feature-flagged `agent` adapter routing
  - router-first capability plane with built-in capability projection and local stdio MCP pilot support
  - capability descriptors / health, additive capability invocation / receipt surfaces, capability policy preview, and operator-facing packetized read models
  - unified `workflow.toml` + env + explicit override config precedence
  - productized worker-pool boundary with local/loopback and real remote HTTP dispatch support
  - OTel-first trace-export abstraction with an optional Langfuse sink
  - one platformized `Domain Pack`
  - persisted `Memory` baseline with retrieval preview and compile-time injection
  - deterministic local `Simulation` baseline with persisted records and selected lifecycle hooks
  - durable pilot checkpoint snapshots in `state/durable`
  - shared orchestration graph substrate with `project_delivery` and `guarded_project_delivery`
  - orchestration plan graphs plus natural-language `plan-graph` / `policy-preview` / `goal-packet` / `launch` surfaces
  - sessionful external-agent lane with projected external session refs
  - controlled repo mutation through explicit write-sets, patch apply, and bounded test/fix loops
  - a single-store quorum-style scheduler-authority layer, committed cross-control-plane lease ownership, and fenced takeover lineage
  - Agent Skill-compatible domain-pack export
  - built-in FastAPI Web operator console and terminal TUI dashboard
  - `v1 core complete` mainline product status
- Current planning position:
  - `M8-M30`, accepted `M31 Phase 0`, and accepted `M32 Phase 0` are complete
  - the active bounded phase is [m33_phase_docs/phase_0_orchestration_service_contraction.md](m33_phase_docs/phase_0_orchestration_service_contraction.md)
  - the active task-card pack is [docs/task_cards/m33_phase_0_task_cards.md](docs/task_cards/m33_phase_0_task_cards.md)
  - the latest accepted freeze is [docs/reviews/m32-interaction-profile-cluster-foundation-freeze-review.md](docs/reviews/m32-interaction-profile-cluster-foundation-freeze-review.md)
  - the current bounded debt focus is `TD-STRUCT-004`, `TD-STRUCT-001`, and `TD-STRUCT-003`
  - `TD-STRUCT-005` and `TD-STRUCT-006` remain deferred to a post-`M33 Phase 0` bounded follow-on
  - the latest accepted foundation is interaction-first, role-profile-aware, and cluster-aware
  - the canonical current development guide is [docs/current_development_workflow.md](docs/current_development_workflow.md)
  - archived planning context from the pre-merge workspace is retained as reference-only in [docs/reviews/m32-archived-planning-inputs.md](docs/reviews/m32-archived-planning-inputs.md)
  - the previous bounded expansion freeze remains [docs/reviews/m31-boundary-contraction-freeze-review.md](docs/reviews/m31-boundary-contraction-freeze-review.md)
  - the previous milestone freeze remains [docs/reviews/m30-operator-control-freeze-review.md](docs/reviews/m30-operator-control-freeze-review.md)
  - the deep core-complete baseline remains [docs/reviews/m20-freeze-review.md](docs/reviews/m20-freeze-review.md)
  - the latest recorded local full-suite validation for the accepted `M32 Phase 0` closeout is `python -m pytest -q` -> `281 passed`

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
- cluster cutover flow passes

The latest validated `M20` closeout baseline is:

- `pytest -q`
  - `264 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`
- `python -m infra.scripts.check_doc_links`
  - `passed=true`

## Common commands

If the project is installed as a package, the `workflowctl` entry point is available. Otherwise use `python -m apps.operator_cli.main`.

- `workflowctl --db-path state/workflow.db preset list`
- `workflowctl --db-path state/workflow.db domain-pack list --json`
- `workflowctl --db-path state/workflow.db domain-pack resolve --preset feature_delivery --task-kind shell_exec`
- `workflowctl --db-path state/workflow.db domain-pack validate`
- `workflowctl --db-path state/workflow.db capability list`
- `workflowctl capability worker-pools`
- `workflowctl scheduler cluster`
- `workflowctl scheduler lease <lease_id>`
- `workflow-remote-worker`
- `workflow-scheduler-authority`
- `python -m apps.operator_cli.main --db-path state/workflow.db run create --goal "Ship through remote workers" --preset feature_delivery`
- `workflowctl --db-path state/workflow.db capability sources`
- `workflowctl --db-path state/workflow.db capability mcp-profiles`
- `workflowctl --db-path state/workflow.db capability projection --preset research_spike_reviewable`
- `workflowctl config show`
- `workflowctl --db-path state/workflow.db simulation policy list`
- `workflowctl --db-path state/workflow.db memory namespace list`
- `workflowctl --db-path state/workflow.db domain-pack export-skill --domain-pack-id software_delivery_pack`
- `workflowctl db workspace-path --label dev`
- `workflowctl --db-path state/workflow.db run suggest-presets --goal "Research runtime strategy"`
- `workflowctl governance tech-debt`
- `workflowctl governance review-policy`
- `workflowctl --db-path state/workflow.db governance release-readiness`
- `workflowctl governance domain-pack`
- `workflowctl --db-path state/workflow.db tui --once`
- `python -m infra.scripts.manage --db-path state/workflow.db dev --host 127.0.0.1 --port 8000`
- `workflow-remote-worker`
- `workflowctl --db-path state/workflow.db run create --goal "Build a smoke artifact" --preset feature_delivery --prepare --execute`
- `workflowctl --db-path state/workflow.db run create --goal "Ship with advisory escalation" --preset advisory_delivery`
- `workflowctl --db-path state/workflow.db run create --goal "Research a design choice" --preset research_spike`
- `workflowctl --db-path state/workflow.db run create --goal "Ship a multi-role delivery slice" --preset project_delivery --prepare --execute`
- `workflowctl --db-path state/workflow.db run create --goal "Ship with mandatory sign-off" --preset guarded_delivery --prepare --execute`
- `workflowctl --db-path state/workflow.db run compile <run_id>`
- `workflowctl --db-path state/workflow.db run compile <run_id> --adapter opencode`
- `workflowctl --db-path state/workflow.db run compile <run_id> --memory-item-id <memory_item_id>`
- `workflowctl --db-path state/workflow.db run compile <run_id> --task-kind noop`
- `workflowctl --db-path state/workflow.db run resume <run_id>`
- `workflowctl --db-path state/workflow.db run batch-resume <run_id_1> <run_id_2> --max-workers 2`
- `workflowctl --db-path state/workflow.db run approve <run_id>`
- `workflowctl --db-path state/workflow.db run reject <run_id>`
- `workflowctl --db-path state/workflow.db run status-detail <run_id>`
- `workflowctl --db-path state/workflow.db run summary <run_id>`
- `workflowctl --db-path state/workflow.db run orchestration <run_id>`
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
- `workflowctl --db-path state/workflow.db run mutation-report <run_id>`
- `workflowctl --db-path state/workflow.db run reconcile <run_id>`
- `workflowctl --db-path state/workflow.db run reconcile <run_id> --apply`
- `workflowctl --db-path state/workflow.db run handoffs <run_id>`
- `workflowctl --db-path state/workflow.db task evidence <runtime_task_id>`
- `workflowctl --db-path state/workflow.db run cancel <run_id>`
- `workflowctl --db-path state/workflow.db db reset`
- `python -m infra.scripts.run_cluster_cutover_demo --db-path state/cluster_cutover_demo.db --report-path state/cluster_cutover_demo_report.json`

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

## Unified config

The repository now supports a local config file in addition to environment variables.

Default config filename:

- `workflow.toml`

Optional override:

```powershell
$env:WORKFLOW_CONFIG_PATH="D:\\path\\to\\workflow.toml"
```

Effective precedence:

1. explicit CLI/API parameters
2. environment variables
3. `workflow.toml`
4. built-in defaults

Inspect the effective config with:

```powershell
workflowctl config show
```

The Web operator surface is now built in as an operator console:

```powershell
python -m infra.scripts.manage --db-path state/workflow.db dev --host 127.0.0.1 --port 8000
```

Then open:

- `http://127.0.0.1:8000/ui`
- `http://127.0.0.1:8000/ui/runs`
- `http://127.0.0.1:8000/ui/reviews`
- `http://127.0.0.1:8000/ui/governance`
- `http://127.0.0.1:8000/ui/config`

Current Web UI scope:

- browse runs, focus detail, review queues, governance, and effective config
- trigger lifecycle actions such as `resume`, `approve`, `reject`, `reconcile`, `cancel`, and `batch-resume`
- inspect packetized operator state through the existing run detail views

Current Web UI non-goals:

- it is not yet a chat-style natural-language workbench
- it does not yet expose streaming conversation, inline replanning, or free-form operator chat with the model

## Natural-language launch surfaces

The repository now has natural-language goal entry points, but they currently live in CLI/API rather than the Web UI or TUI.

CLI:

```powershell
workflowctl --db-path state/workflow.db run suggest-presets --goal "Research runtime strategy"
workflowctl --db-path state/workflow.db run plan-graph --goal "Ship a guarded delivery slice"
workflowctl --db-path state/workflow.db run policy-preview --goal "Ship a guarded delivery slice"
workflowctl --db-path state/workflow.db run goal-packet --goal "Ship a guarded delivery slice"
workflowctl --db-path state/workflow.db run launch --goal "Ship a guarded delivery slice" --execute
workflowctl --db-path state/workflow.db run operator-packet <run_id>
```

API:

- `POST /runs/plan-graph`
- `POST /runs/policy-preview`
- `POST /runs/goal-packet`
- `POST /runs/launch`
- `GET /runs/{run_id}/operator-packet`

Important boundary:

- the backend can already plan and launch from a natural-language goal
- the built-in Web UI and TUI remain operator surfaces, not full natural-language interaction terminals

Remote worker productization and scheduler-authority peers are both built in for the shipped multi-control-plane core-complete path:

```powershell
$env:UAWO_ENABLE_EXTERNAL_WORKER_POOLS="1"
$env:WORKFLOW_WORKER_POOL_ID="remote_http_shell"
$env:WORKFLOW_REMOTE_WORKER_SHARED_SECRET="<shared secret>"
$env:WORKFLOW_CONTROL_PLANE_ID="control_plane_alpha"
$env:WORKFLOW_SCHEDULER_AUTHORITY_NODE_ID="authority-a"
$env:WORKFLOW_SCHEDULER_AUTHORITY_BIND_URL="http://127.0.0.1:8020"
workflow-scheduler-authority
workflow-remote-worker
```

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

External worker-pool boundary:

```powershell
$env:UAWO_ENABLE_EXTERNAL_WORKER_POOLS="1"
$env:WORKFLOW_WORKER_POOL_ID="mock_remote_shell"
workflowctl capability worker-pools
```

The `M8` borrowed-agent, MCP, durable, trace-export, and skill-export lanes remain opt-in.
The shipped `M20` baseline now includes the completed majority-quorum scheduler-authority and cross-control-plane failover path.

## Project orchestration baseline

`project_delivery` is the first formal multi-agent orchestration preset.

It uses a controller-owned flow:

- `planner`
- `coder` and `researcher` in a parallel batch
- `reviewer`

Example:

```powershell
python -m apps.operator_cli.main --db-path state/project_demo.db db reset
python -m apps.operator_cli.main --db-path state/project_demo.db run create --goal "Build project delivery demo" --preset project_delivery --prepare --execute
python -m apps.operator_cli.main --db-path state/project_demo.db run orchestration <run_id>
```

The `coder` role prefers `opencode` and falls back to `shell`.
Research and review roles prefer the borrowed-agent lane and fall back safely to local execution.

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

Current TUI scope:

- recent runs
- focus detail
- runtime-gateway snapshot
- timeline tail

Current TUI non-goals:

- it is not yet a full interactive operator shell
- it is not yet a natural-language chat console or workbench

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
- `GET /runs/{id}/orchestration`
- `POST /runs/batch-resume`
- `GET /presets`
- `GET /domain-packs`
- `GET /domain-packs/resolve`
- `GET /domain-packs/validate`
- `GET /capability-routes`
- `GET /worker-pools`
- `GET /config/effective`
- `GET /simulation/policies`
- `GET /memory/namespaces`
- `GET /memory/items`
- `GET /governance/tech-debt`
- `GET /governance/review-policy`
- `GET /governance/metrics`
- `GET /governance/alerts`
- `GET /governance/release-readiness`
- `GET /governance/domain-packs`
- `GET /runs/{id}/replay-packet`
- `GET /tasks/{id}/evidence`

`POST /runs/{id}/compile` and `POST /runs/{id}/recompile` may optionally receive a JSON body such as `{"task_kind": "noop"}` when the selected preset allows that task kind, `{"adapter_name": "opencode"}` when a capability route should be pinned explicitly, or `{"memory_item_ids": ["memory_..."]}` for the explicit memory-aware compile bridge.

## Notes

- `POST /runs` only creates the run and records preset selection.
- `compile`, `recompile`, `resume`, `approve`, and `reject` are explicit lifecycle steps in M1.
- `research_spike` can be compiled with `--task-kind noop`; `feature_delivery` rejects `noop` with the structured error code `task_kind_not_allowed`.
- `feature_delivery` can be compiled through `shell` or `opencode`; compile/recompile pin the selected adapter into the run's capability resolution.
- `feature_delivery` stays `auto_only`.
- `optional_delivery` uses `optional`: auto review always runs, but terminal status still follows execution success or failure.
- `feature_delivery`, `optional_delivery`, `advisory_delivery`, and `guarded_delivery` now resolve the platformized `software_delivery_pack`; compile/status surfaces project the selected domain pack and adapter route.
- `advisory_delivery` uses `recommended`: auto pass completes, auto fail escalates into `awaiting_review`.
- `research_spike` uses `human_required`: execution completes, then it waits for human review without an auto-review gate.
- `guarded_delivery` uses `mandatory`: auto review always runs, but the run still waits for human sign-off.
- `status-detail` now includes operator-facing diagnostics such as `failure_reason`, `waiting_reason`, `last_runtime_state`, `recoverability_hint`, `active_claims`, `latest_claim`, and `latest_snapshot`.
- `status-detail`, `summary`, `inspection`, and `replay-packet` now also expose `execution_target`, `lease_renewals`, and orchestration state when present.
- `status` now also includes `latest_simulation_record`, so the most recent simulation lineage source is visible without switching to the full detail payload.
- `status` / `status-detail` / `inspection` now also expose the active `runtime_gateway` projection so live LLM activation is visible without guessing from env vars.
- `status-detail` and `inspection` now also include `runtime_attempts`, `current_runtime_attempt`, `latest_runtime_attempt`, `runtime_attempt_projection`, `durable_lineage`, and first-class `run_metrics`.
- `workflowctl config show` and `GET /config/effective` expose the unified config view and its source precedence.
- `capability worker-pools` and `GET /worker-pools` expose the seed-backed external worker-pool catalog.
- when the OpenAI-backed gateway is enabled, the resumed runtime state can carry a short `runtime_brief`, and shell artifacts can persist that brief alongside `runtime_gateway` / `runtime_model`.
- `run summary` and `GET /runs/{id}/summary` provide a concise operator view of failure taxonomy, review state, timeline digest, and ownership projections.
- `run simulation` and `GET /runs/{id}/simulation` expose the first deterministic local simulation report, including whether policy triggered and which checks failed.
- `run record-simulation` / `POST /runs/{id}/simulation-records` persist the current simulation report as an auditable local record.
- `run simulations` / `GET /runs/{id}/simulation-records` expose the persisted simulation history for a run, including whether each record came from a manual request or a selected lifecycle hook.
- selected lifecycle control points now auto-record simulation for triggered policies at `cancelled`, `awaiting_review`, and terminal completion/failure.
- `run event-inspection` and `GET /runs/{id}/event-inspection` provide a richer event digest plus closure-audit framing for completed, awaiting-review, and terminal runs.
- `run audit-report` and `GET /runs/{id}/audit-report` export a review-ready audit bundle that combines summary, event inspection, state inspection, and recent timeline context.
- `run replay-packet` and `GET /runs/{id}/replay-packet` export replay-grade linkage across task packets, state refs, attempts, claims, leases, evidence, review history, metrics, and timeline artifacts.
- `simulation policy list` and `GET /simulation/policies` expose the seed-backed simulation policy catalog that currently gates which presets receive the local simulation slice.
- `governance tech-debt` and `GET /governance/tech-debt` expose the current technical-debt registry as a structured governance report.
- `governance review-policy` and `GET /governance/review-policy` expose the current supported review-policy catalog, operator state matrix, and runtime-shape mapping for all executable policies.
- `governance metrics` / `GET /governance/metrics` expose quantitative governance inventory over debt, policy coverage, validation, platform, and runtime DB state.
- `governance alerts` / `GET /governance/alerts` expose blocking vs degraded governance conditions automatically.
- `governance release-readiness` and `GET /governance/release-readiness` expose a release-shaped closeout view that combines validation, capability routes, platformized domain-pack baseline, governance automation, and current milestone gates.
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
- `run batch-resume` and `POST /runs/batch-resume` expose the local batch barrier plus parallel resume surface for multiple prepared runs.
- `run orchestration` and `GET /runs/{id}/orchestration` expose controller-owned orchestration plans, role progress, barrier state, and child-run lineage for `project_delivery`.
- `run snapshots` and `GET /runs/{id}/snapshots` expose replay-friendly checkpoint history for recovery analysis.
- `run budget` and `GET /runs/{id}/budget` expose persisted budget-ledger state plus remaining retry / timeout headroom.
- `inspection` is a read-only dry-run surface that flags inconsistent states without mutating the database.
- `resume` acquires a local runtime claim before execution; terminal and review-handoff paths release it explicitly.
- `reconcile` reuses the same bad-state catalog, but only applies explicit safe repairs; manual-only problems still fail with structured errors.
- Claim semantics now carry explicit local ownership topology and batch-domain lineage. They improve correctness and auditability, but they are not distributed locking or multi-node scheduler consensus.
- Worker-lease semantics are local-first worker ownership projections with explicit claim / attempt linkage. They improve heartbeat and interrupt-safety diagnostics, but they are not a distributed lease manager.
- External worker-pool dispatch is real and testable, but the shipped path remains opt-in and loopback-safe. It is not yet a hosted multi-node scheduler.
- Snapshot semantics are recovery-oriented projections. They improve checkpoint visibility, but they are not a full replay engine.
- Durable pilot snapshots now persist under `state/durable`, but repository truth still remains canonical.
- Smoke clears known LLM API key variables before execution and restores them afterward.
