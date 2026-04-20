# M11 Freeze Review

## Result

`M11` is complete.

This milestone turned the repository into a safer self-hosted development control plane before expanding breadth. The emphasis stayed on local-first truth, DB stability, and an explicit external-execution boundary instead of jumping straight to hosted scheduling claims.

## Completed Scope

`M11` closed with these repository-owned outcomes:

- workspace-scoped DB path helpers and lock-aware reset/error handling for shared SQLite usage
- SQLite busy-timeout hardening plus structured `DatabaseBusyError` reporting
- seed-backed `WorkerPoolProfile` loading with explicit external-worker boundary contracts
- `ExecutionDispatcher` / `ExternalWorkerGateway`-style substrate through loopback external dispatch
- `execution_target` and `lease_renewals` projection surfaces across status, summary, inspection, replay, CLI, and API
- CLI/API visibility for worker-pool inventory
- repository truth preserved even when dispatch crosses the external-worker boundary

## Debt Outcome

`M11` substantially paid down the entry portion of `TD-019`, but did not retire it.

What is now complete:

- external worker pools have a supported contract boundary
- loopback external dispatch is real and testable
- DB/bootstrapping stability is materially stronger for self-hosted workflow usage

What remains deferred:

- hosted remote pools
- distributed lease renewal
- multi-node scheduler consensus

## Validation Evidence

The integrated closeout baseline that includes `M11` passed on `2026-04-20` with:

- `python -m pytest -q`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
- `python -m infra.scripts.check_doc_links`

Those milestone-level validations remained green through the later `M12` and `M13` closeout work.

## Current Repository Position After M11

After `M11`, the repository could truthfully say:

- self-hosted workflow usage no longer depends on a single shared DB path with weak error handling
- external worker pools are no longer only planning vocabulary
- the repository still remains a local-first control plane rather than a hosted scheduler

## Follow-on Scope

Next milestone:

- `M12`

Planned focus:

- productize configuration
- make durable and trace paths operationally trustworthy
- keep external lanes opt-in and diagnosable
