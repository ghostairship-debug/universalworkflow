# Universal Agentic Workflow OS

This repository now contains an executable M0 bootstrap for the Universal Agentic Workflow OS. The implementation stays local-first, uses SQLite, keeps the runtime behind `RuntimeGateway`, and proves a narrow execution loop without any LLM dependency.

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
- CLI flow passes
- smoke flow passes
- API flow passes

## Common commands

- `workflowctl --db-path state/workflow.db preset list`
- `workflowctl --db-path state/workflow.db run create --goal "Build a smoke artifact" --preset feature_delivery --prepare --execute`
- `workflowctl --db-path state/workflow.db run status <run_id>`
- `workflowctl --db-path state/workflow.db run timeline <run_id>`
- `workflowctl --db-path state/workflow.db task evidence <runtime_task_id>`
- `workflowctl --db-path state/workflow.db run cancel <run_id>`
- `workflowctl --db-path state/workflow.db db reset`

## API entry point

Run the orchestrator API locally with:

```bash
python -m infra.scripts.manage --db-path state/workflow.db dev
```

The M0 routes are:

- `POST /runs`
- `GET /runs/{id}`
- `GET /runs/{id}/timeline`
- `GET /presets`
- `GET /tasks/{id}/evidence`

## Notes

- `POST /runs` only creates the run and records preset selection.
- Internal prepare and execute flows are kept behind the service layer for M0.
- Smoke clears known LLM API key variables before execution and restores them afterward.
