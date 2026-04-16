# Universal Agentic Workflow OS

This repository now contains the M1 local-first runtime for the Universal Agentic Workflow OS. It keeps SQLite as the only persistence layer, preserves the `RuntimeGateway` boundary, supports deterministic preset suggestion, public `compile / recompile / resume` surfaces, `HandoffLite` persistence, and both `auto_only` and `human_required` review loops without any LLM dependency.

## Environment

- Python 3.13+
- Windows, macOS, or Linux shell access
- No external database required

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
```

## Offline validation

If you want one-shot offline acceptance after disconnecting the machine from the network:

```powershell
powershell -ExecutionPolicy Bypass -File .\infra\scripts\run_offline_validation.ps1
```

The script writes a JSON report to `state/offline_validation_report.json` and verifies:

- offline reachability probes fail
- CLI auto path passes
- CLI human-review path passes
- smoke flow passes
- API auto path passes
- API human-review path passes

## Common commands

If the project is installed as a package, the `workflowctl` entry point is available. Otherwise use `python -m apps.operator_cli.main`.

- `workflowctl --db-path state/workflow.db preset list`
- `workflowctl --db-path state/workflow.db run suggest-presets --goal "Research runtime strategy"`
- `workflowctl --db-path state/workflow.db run create --goal "Build a smoke artifact" --preset feature_delivery --prepare --execute`
- `workflowctl --db-path state/workflow.db run create --goal "Research a design choice" --preset research_spike`
- `workflowctl --db-path state/workflow.db run compile <run_id>`
- `workflowctl --db-path state/workflow.db run resume <run_id>`
- `workflowctl --db-path state/workflow.db run approve <run_id>`
- `workflowctl --db-path state/workflow.db run reject <run_id>`
- `workflowctl --db-path state/workflow.db run status-detail <run_id>`
- `workflowctl --db-path state/workflow.db run inspect <run_id>`
- `workflowctl --db-path state/workflow.db run handoffs <run_id>`
- `workflowctl --db-path state/workflow.db task evidence <runtime_task_id>`
- `workflowctl --db-path state/workflow.db run cancel <run_id>`
- `workflowctl --db-path state/workflow.db db reset`

## Manual paths

Auto-review path:

```bash
python -m apps.operator_cli.main --db-path state/workflow.db db reset
python -m apps.operator_cli.main --db-path state/workflow.db run create --goal "Build a smoke artifact" --preset feature_delivery
python -m apps.operator_cli.main --db-path state/workflow.db run compile <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run status-detail <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run inspect <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run resume <run_id>
```

Human-review path:

```bash
python -m apps.operator_cli.main --db-path state/workflow.db run create --goal "Research a design choice" --preset research_spike
python -m apps.operator_cli.main --db-path state/workflow.db run compile <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run status-detail <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run inspect <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run resume <run_id>
python -m apps.operator_cli.main --db-path state/workflow.db run approve <run_id>
```

## API entry point

Run the orchestrator API locally with:

```bash
python -m infra.scripts.manage --db-path state/workflow.db dev
```

The M1 routes are:

- `POST /runs`
- `GET /runs/{id}`
- `POST /runs/{id}/compile`
- `POST /runs/{id}/recompile`
- `POST /runs/{id}/resume`
- `POST /runs/{id}/approve`
- `POST /runs/{id}/reject`
- `GET /runs/{id}/timeline`
- `GET /runs/{id}/status-detail`
- `GET /runs/{id}/inspection`
- `GET /runs/{id}/handoffs`
- `GET /presets`
- `GET /tasks/{id}/evidence`

## Notes

- `POST /runs` only creates the run and records preset selection.
- `compile`, `recompile`, `resume`, `approve`, and `reject` are explicit lifecycle steps in M1.
- `research_spike` enters `awaiting_review` after `resume`; it does not auto-complete.
- `status-detail` now includes operator-facing diagnostics such as `failure_reason`, `waiting_reason`, `last_runtime_state`, and `recoverability_hint`.
- `inspection` is a read-only dry-run surface that flags inconsistent states without mutating the database.
- Smoke clears known LLM API key variables before execution and restores them afterward.
- See [docs/smoke/m1-smoke.md](/D:/Universal%20Agentic%20workflow/docs/smoke/m1-smoke.md:1) for the M1 acceptance flow.
