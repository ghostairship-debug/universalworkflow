# M0 Smoke

## Purpose

Prove that the M0 bootstrap can reset state, seed presets, create one run, execute one task, persist evidence, and return a readable timeline without any LLM API key.

## Manual flow

1. Reset the local database.
2. Apply migrations.
3. Remove or override LLM API keys for the shell session.
4. Seed presets.
5. Create one `feature_delivery` run.
6. Prepare and execute the run.
7. Query the run timeline.
8. Query task evidence.
9. Confirm the terminal event is `run_completed`.

## Command path

If GNU Make is available:

```bash
make smoke
```

If GNU Make is not available:

```bash
python -m infra.scripts.manage --db-path state/workflow.db smoke
```

For a stricter offline acceptance run after physically disconnecting the machine from the network:

```powershell
powershell -ExecutionPolicy Bypass -File .\infra\scripts\run_offline_validation.ps1
```

That wrapper runs the offline probe, CLI flow, smoke flow, and API flow, then writes a JSON report to `state/offline_validation_report.json`.

## Expected outcome

- The command completes in a few seconds on a local machine.
- The returned event list includes:
  `run_created`, `preset_selected`, `phase_created`, `runtime_task_created`, `runtime_task_started`, `runtime_task_completed`, `evidence_submitted`, `review_submitted`, `run_completed`
- No network or LLM key is required.
