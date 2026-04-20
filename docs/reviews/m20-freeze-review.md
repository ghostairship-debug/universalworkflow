# M20 Freeze Review

## Result

`M20` is complete. The mainline product is now `v1 core complete`.

## Completed Scope

- completed majority-quorum scheduler-authority peers, committed lease fencing, and cross-control-plane takeover lineage
- bound worker dispatch, heartbeat, completion, and renewal writes to quorum-committed lease ownership
- rejected stale-plane and stale-callback writes fail-closed while preserving conflict diagnostics and replay evidence
- exposed cluster topology, leadership, committed leases, takeover history, and stale-plane evidence through CLI, API, and Web operator surfaces
- added a repeatable cluster cutover demo and offline validation cluster smoke so `TD-021` could be retired with executable proof

## Validation Evidence

- `tests/test_contracts.py`
- `tests/test_repositories.py`
- `tests/test_execution_loop.py`
- `tests/test_cli.py`
- `tests/test_api.py`
- `tests/test_governance.py`
- `tests/test_scheduler_authority_api.py`
- `tests/test_remote_worker_api.py`
- `tests/test_web_ui.py`
- `python -m pytest -q`
- `python -m infra.scripts.run_cluster_cutover_demo --db-path state/cluster_cutover_demo.db --report-path state/cluster_cutover_demo_report.json`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
- `python -m infra.scripts.check_doc_links`

## Notes

- `TD-021` is retired in this freeze review; no open structural debt remains on the mainline product path.
- The repository can now honestly claim majority-quorum authority, multi-control-plane failover, committed cross-plane lease ownership, and fenced remote-worker callbacks while still keeping repository truth inside the control planes.
- `M21+` is no longer needed for core control-plane completion. Any later milestone should start from a fresh post-`M20` rebaseline and focus only on autonomy, ecosystem, multimodal, or other breadth work.

## Next Approved Work

- `M21 Phase 0 - Post-M20 Rebaseline And Expansion Freeze`
