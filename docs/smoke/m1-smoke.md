# M1 Smoke

## Purpose

Prove that the M1 runtime can reset state, seed presets, compile a run, persist `HandoffLite` and `RuntimeStateRef`, complete the auto-review path, suspend the human-review path at `awaiting_review`, and finish that path through an explicit operator approval without any LLM API key.

## Coverage

- deterministic preset suggestion stays offline
- `feature_delivery` follows `create -> compile -> resume -> review_submitted -> run_completed`
- `research_spike` follows `create -> compile -> resume -> review_requested -> approve -> run_completed`
- `status-detail`, `handoffs`, and `task evidence` stay readable
- CLI, smoke script, and offline validation use the same lifecycle semantics

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

## Expected outcome

- `python -m infra.scripts.manage ... smoke` returns `status = completed`
- the auto path returns `status = completed` and the timeline includes:
  `run_created`, `preset_selected`, `phase_created`, `phase_created`, `handoff_created`, `runtime_task_created`, `run_compiled`, `runtime_resumed`, `runtime_task_started`, `runtime_task_completed`, `evidence_submitted`, `review_submitted`, `run_completed`
- the human path returns `status = completed` after approval and the timeline includes:
  `run_created`, `preset_selected`, `phase_created`, `phase_created`, `handoff_created`, `runtime_task_created`, `run_compiled`, `runtime_resumed`, `runtime_task_started`, `runtime_task_completed`, `evidence_submitted`, `review_requested`, `review_submitted`, `run_completed`
- no network or LLM key is required

## Manual spot checks

1. Run `workflowctl run suggest-presets --goal "Research runtime architecture"` and confirm the top suggestion is `research_spike`.
2. Run one `feature_delivery` flow and confirm `run status` ends at `completed`.
3. Run one `research_spike` flow and confirm `run resume` ends at `awaiting_review`.
4. Run `workflowctl run approve <run_id>` and confirm the run becomes `completed`.
5. Run `workflowctl run handoffs <run_id>` and `workflowctl run status-detail <run_id>` and confirm both surfaces contain persisted compile artifacts.
