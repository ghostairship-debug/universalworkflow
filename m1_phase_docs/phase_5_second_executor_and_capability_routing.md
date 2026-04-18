# M1.5 - Second Executor And Capability Routing

**Phase status:** Completed
**Verification summary:** `pytest` passed with `59 passed`; `python -m infra.scripts.offline_validation --skip-offline-probe` returned `overall_passed=true` and covered shell, human-review, and noop executor paths.

**Phase position:** This phase starts after the `M1` freeze checkpoint and the dedicated M1 legacy hardening uplift are complete. It is the post-`M1` hardening stage that closes `TD-005` by turning the single-adapter execution path into a minimal multi-adapter runtime with explicit capability routing, while keeping the current run-centric architecture intact.

**Entry condition:** `M1 Phase 0` to `M1 Phase 4` are closed, `status-detail / inspection` are stable, and the repository already supports `shell_exec` plus `noop` as public task kinds.

**Naming note:** This file keeps the historical `phase_5` path for continuity, but the milestone should be read as `M1.5`. The canonical sequence is documented in [docs/m1_to_m2_progression.md](/D:/Universal%20Agentic%20workflow/docs/m1_to_m2_progression.md:1).

**Legacy-reference note:** This phase is not a second dedicated legacy-uplift batch. The legacy-driven `Phase A/B/C` hardening work belongs to the completed [docs/m1_legacy_reference_uplift_plan.md](/D:/Universal%20Agentic%20workflow/docs/m1_legacy_reference_uplift_plan.md:1). `M1.5` uses that stabilized baseline to make the executor boundary real and to repay `TD-005`.

---

## 1. Reassessment

Current implementation status:

- The repository already exposes two task kinds in contracts and presets: `shell_exec` and `noop`.
- Runtime execution is still effectively single-adapter because `ShellAdapter` handles both task kinds.
- `compile_run()` always selects the first allowed task kind, so the second execution path is not a real routed path yet.
- The next highest-value post-`M1` phase is therefore not `M2` repair/reconcile, but `M1.5` adapter separation and deterministic capability routing.

This phase keeps the existing M1 architecture and only upgrades the execution boundary:

- separate the second executor from `ShellAdapter`
- add a capability router
- expose deterministic task-kind selection where needed
- prove the second executor path through tests and acceptance surfaces

---

## 2. In Scope

- Extract adapter base abstractions away from `shell_adapter.py`
- Add a dedicated `NoopAdapter`
- Add a `WorkerRouter` / capability routing layer
- Keep `ShellAdapter` focused on `shell_exec`
- Allow `compile / recompile` to select an allowed task kind explicitly
- Allow CLI and API surfaces to trigger the second executor path
- Add tests for routing, allowed task kind enforcement, and end-to-end noop execution
- Update docs and technical debt tracking for `TD-005`

---

## 3. Out Of Scope

- Multi-executor parallel scheduling
- Claim / lease / barrier semantics
- Rich capability scoring or cost-based scheduling
- Dynamic executor plugins
- M2 repair / reconcile actions
- Richer review policy enums

---

## 4. Key Constraints

- The system must remain run-centric; do not introduce a project/phase/task-card kernel.
- Routing must be deterministic and local-only.
- `POST /runs` still only creates a run; compile-time task-kind selection must stay on compile/recompile surfaces.
- Requested task kinds must be validated against `PresetDefinition.allowed_task_kinds`.
- If no adapter supports a task kind, the system must fail explicitly instead of silently falling back.
- Existing `shell_exec` behavior must remain backward-compatible.

---

## 5. Phase Task Breakdown Principle

This phase is split into three complex tasks:

1. Adapter base extraction, `NoopAdapter`, and capability router
2. Compile-time task-kind override plus service-layer routing
3. CLI/API/docs/validation updates plus full verification

Each task must ship with explicit tests before the next task begins.

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- `ShellAdapter` only owns `shell_exec`
- `NoopAdapter` is a real second executor
- runtime execution routes through an explicit router
- `compile / recompile` can request `noop` when the preset allows it
- invalid task-kind requests fail with a stable error
- CLI and API can both exercise the noop path
- full `pytest` passes

Gate outcome:

- Passed: `ShellAdapter` now only owns `shell_exec`
- Passed: `NoopAdapter` is a real second executor and writes deterministic artifacts
- Passed: runtime execution routes through `WorkerRouter`
- Passed: `compile / recompile` accept an explicit allowed task-kind override
- Passed: invalid task-kind requests fail with stable `unsupported_task_kind` or `task_kind_not_allowed` errors
- Passed: CLI and API both exercise the noop path
- Passed: full `pytest` and offline validation succeeded

---

## 7. Risks And Rollback

- Risk: adapter routing gets implemented as hidden fallback logic
  Control: make route selection explicit and fail fast for unsupported task kinds
- Risk: compile/task-kind selection expands beyond `M1.5` scope
  Control: keep selection to `allowed_task_kinds` only; do not add planner inference
- Risk: second executor changes shell behavior
  Control: keep shell tests unchanged and add noop-specific tests separately

## 8. Outcome

- `TD-005` is repaid in this phase.
- The repository now has a real second executor boundary instead of a contract-only `noop` path.
- The next recommended phase is to reassess M2 repair / reconcile work from the now-stable multi-adapter baseline, rather than reopening execution routing again.
