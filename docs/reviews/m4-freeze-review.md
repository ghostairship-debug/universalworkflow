# M4 Freeze Review

## Scope

This review closes the current local-first delivery cycle from `M0` through `M4`.

Closed in the current cycle:

- run-centric lifecycle spine
- human-review loop and richer executable review policies (`auto_only`, `recommended`, `human_required`, `mandatory`)
- second executor and capability routing
- reconcile / repair / snapshot / claim / lease / attempt / budget baseline
- operator summary / inspection / audit / governance surfaces
- minimal domain-pack proof
- release-readiness report and golden demo packet

Explicitly deferred beyond the current cycle:

- `optional` review policy
- Web UI / TUI expansion
- deeper domain-pack platformization
- next-cycle expansion items from the long-term plan

## Verification Baseline

Latest green baseline:

- `pytest -q`
  - `162 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`
- `python -m infra.scripts.manage --db-path state/demo_phase2.db demo`
  - `status=completed`

## Debt Decision

- `TD-006` remains partially repaid, but it is no longer treated as unfinished `M4` scope.
- The remaining `optional` gap is moved into the next cycle as an explicit expansion candidate.

## Conclusion

- Current cycle: **complete**
- Further work: **next-cycle expansion**, not baseline completion work
