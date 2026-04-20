# M12 Freeze Review

## Result

`M12` is complete.

This milestone turned the external and durable lanes from "can be enabled" into "can be operated, inspected, and reasoned about" without moving product truth out of the repository.

## Completed Scope

`M12` closed with these repository-owned outcomes:

- a unified config layer backed by `workflow.toml`, `WORKFLOW_CONFIG_PATH`, env overrides, and explicit CLI/API override precedence
- `workflowctl config show` and `GET /config/effective` for effective-config visibility
- runtime gateway, borrowed-agent, opencode, trace, durable, and worker-pool builders now read from one config source instead of scattered `os.getenv(...)`
- the durable pilot now writes real checkpoint snapshots through a LangGraph-backed saver path
- durable checkpoint references now carry file-backed state snapshots in `state/durable`
- the Langfuse exporter exposes success/failure counters, last-trace diagnostics, and redaction-aware attribute handling

## Debt Outcome

`M12` did not retire the remaining distributed-hosting debt, but it closed the productization gap that had made external lanes hard to operate consistently.

What is now true:

- configuration precedence is explicit and inspectable
- durable refs are no longer UUID-only placeholders
- trace/export failures can be diagnosed without changing run outcomes

## Validation Evidence

The integrated closeout baseline that includes `M12` passed on `2026-04-20` with:

- `python -m pytest -q`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
- `python -m infra.scripts.check_doc_links`

These validations remained green after the `M13` orchestration baseline landed.

## Current Repository Position After M12

After `M12`, the repository could truthfully say:

- external and durable lanes are configurable rather than environment-variable folklore
- operator-facing config state is visible from both CLI and API
- durable and trace behavior are still bounded pilots, but no longer empty shells

## Follow-on Scope

Next milestone:

- `M13`

Planned focus:

- formal multi-agent role contracts
- controller-owned orchestration planning
- planner to parallel-worker to reviewer execution flow
