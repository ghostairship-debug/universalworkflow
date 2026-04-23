# M2M Remediation Plan

**Full name:** Monolith-to-Modular Remediation Plan
**Audience:** executing agent (codex / Claude Code / human)
**Date:** 2026-04-24
**Baseline:** accepted `M36 Phase 0`; `pytest` 296 passing; latest freeze review is `docs/reviews/m36-workbench-ia-capability-slot-freeze-review.md`
**Owner decision (2026-04-24):** pure local single-machine for now; cloud / multi-node deferred

---

## 0. How To Read This Document

This plan is designed to be executed **phase by phase, in order, by an autonomous agent**. Do **not** skip ahead. Each phase has:

- **Goal** — what this phase produces
- **Non-goals** — what this phase must NOT touch
- **Entry conditions** — prerequisites (must be true before you start)
- **Steps** — ordered, concrete file operations
- **Verification** — commands that must pass before the phase is considered done
- **Commit shape** — how to land the work in git
- **Rollback** — how to back out if verification fails

If verification fails and you cannot resolve it in-phase, **stop and report**. Do not proceed to the next phase.

---

## 1. Hard Invariants (Never Violate)

These rules apply to every phase. A change that violates any of them must be reverted.

1. **Test suite must stay green.** `pytest` passes 296 tests at baseline. After each phase, the count must be **≥ 296** (higher is fine when you add tests; lower means regression).
2. **Public CLI surface is stable.** Every `workflowctl ...` subcommand listed in `README.md` must continue to work with identical flags and output shape.
3. **Public HTTP API surface is stable.** Every route under `apps/orchestrator_api/routers/` must remain reachable at the same path with the same request/response schema.
4. **No new runtime dependencies** are introduced by this plan. Refactor only.
5. **`packages/contracts/` must not import from `packages/core_domain/`** or from `apps/`. Dependency direction is `contracts ← core_domain ← apps`.
6. **`packages/runtime_langgraph/` remains the only module allowed to import `langchain` / `langgraph`.** Do not leak those names into `core_domain/` or `apps/`.
7. **SQLite remains the single persistence store.** Do not introduce a repository abstraction that implies multiple backends. Cloud is explicitly deferred.
8. **Do not delete scheduler-authority code.** Feature-flag or isolate only. The user reserves the right to revisit cloud/multi-node later.
9. **No new features.** This plan is purely structural. If you notice a bug along the way, note it in `docs/tech-debt-registry.md` and keep moving.
10. **Do not rename public types in `packages/contracts/models.py` or `packages/contracts/events.py`.** Downstream consumers depend on them.

---

## 2. Baseline Facts (So You Can Verify Drift)

These numbers were measured at plan authoring time. If they differ significantly when you start, re-measure and note the delta in your first commit message.

- `packages/core_domain/services.py` — **3820 lines**, 1 class (`OrchestratorService`), **164 methods**
- `packages/core_domain/repositories.py` — **1621 lines**, **19 repository classes**
- `packages/core_domain/service_projection.py` — 1572 lines (mixin)
- `packages/core_domain/service_lifecycle.py` — 1637 lines (mixin)
- `packages/core_domain/scheduler_authority.py` — 1226 lines
- `apps/operator_cli/main.py` — 1101 lines, one Typer app
- `packages/core_domain/` — 35 flat modules, no sub-packages
- Three HTTP entry points: `apps/orchestrator_api`, `apps/remote_worker_api`, `apps/scheduler_authority_api`

---

## 3. Phase Overview

| # | Phase | Risk | Est. LOC churn | Prereq |
| --- | --- | --- | --- | --- |
| 1 | Repo hygiene + test mirror skeleton | low | small | none |
| 2 | Isolate multi-control-plane behind a flag | medium | medium | Phase 1 |
| 3 | Convert service mixins to standalone services | high | large | Phase 2 |
| 4 | Split `OrchestratorService` facade into a coordinator | high | large | Phase 3 |
| 5 | Split `repositories.py` per aggregate | medium | medium | Phase 4 |
| 6 | Sub-package `core_domain/` (domain / application / infrastructure) | medium | large (mostly moves) | Phase 5 |
| 7 | Split `apps/operator_cli/main.py` into command groups | low | medium | Phase 6 |
| 8 | Unify three API processes into one with role flag | medium | medium | Phase 7 |

Each phase lands on its own branch and merges cleanly before the next phase opens.

---

## 4. Phase 1 — Repo Hygiene + Test Mirror Skeleton

### Goal
- Land the currently uncommitted work (or deliberately stash it).
- Clean root-level planning-doc clutter.
- Create an empty mirror structure under `tests/` that will be populated in later phases.

### Non-goals
- No code refactor.
- No behavior change.

### Entry conditions
- `git status` is understood: 35+ modified files and several untracked folders exist. Read them first. If any contain real intent, ask the owner before archiving.

### Steps

1. **Audit uncommitted changes.** Run `git status --short` and `git diff --stat`. For each modified file, decide: land, revert, or stash. Produce a one-paragraph summary at the top of your PR.
2. **Archive stale root-level planning docs.** Create `docs/archive/` if missing. Move these files into it (git mv):
   - `EVALUATION_REPORT.md`
   - `M31_ARCHITECTURE_EVALUATION.md`
   - `M31_CURRENT_STAGE_REMEDIATION_PLAN.md`
   - `M31_DEVELOPMENT_PLAN.md`
   - `M31_FUTURE_IMPLEMENTATION_PLAN.md`
   - `M34_POST_EVALUATION.md`
   - `AI_AGENT_LEGACY_WHITELIST.md`
   - `GPT_PRO_ROADMAP .md` (note: filename contains a space; preserve it with quotes, OR rename to `GPT_PRO_ROADMAP.md` during the move and update any inbound links)
3. **Keep at root:** `README.md`, `README.zh-CN.md`, `NEXT_DEVELOPMENT_PLAN.md`, `POST_M34_MULTIPHASE_ROADMAP.md`, `M2M_REMEDIATION_PLAN.md` (this file), `Makefile`, `pyproject.toml`, `.gitignore`.
4. **Update inbound links.** Grep for references to the moved files in `README.md`, `README.zh-CN.md`, `NEXT_DEVELOPMENT_PLAN.md`, `POST_M34_MULTIPHASE_ROADMAP.md`, and anything under `docs/`. Rewrite relative paths to point at `docs/archive/...`. Run `python -m infra.scripts.check_doc_links`.
5. **Delete the binary artifact** `universalworkflow_m36_bundle.zip` from root if it is not referenced anywhere (verify with `grep -r "universalworkflow_m36_bundle" .`). If unreferenced, `git rm` it.
6. **Create empty test mirror.** Make these directories with a `.gitkeep` file in each:
   - `tests/core_domain/`
   - `tests/core_domain/application/`
   - `tests/core_domain/domain/`
   - `tests/core_domain/infrastructure/`
   - `tests/apps/`
   - `tests/contracts/`
   - `tests/worker_adapters/`
   Do not move any existing test yet. The mirror is just the target shape.

### Verification
```
pytest
python -m infra.scripts.offline_validation --skip-offline-probe
python -m infra.scripts.check_doc_links
```
All three must pass. Test count must remain ≥ 296.

### Commit shape
- Commit 1: `chore: land or stash pre-m2m uncommitted work` (one atomic commit; describe decisions in the message)
- Commit 2: `docs: archive stale root-level planning inputs`
- Commit 3: `test: add empty test mirror skeleton for upcoming phases`

### Rollback
If doc-link check fails: restore the moved file, fix the link, retry.

---

## 5. Phase 2 — Isolate Multi-Control-Plane Behind A Flag

### Goal
- Encode the local-only stance into config.
- Keep `scheduler_authority` code compilable and testable, but **off by default**.
- Prevent `OrchestratorService.__init__` from instantiating the cluster service when the flag is off.

### Non-goals
- Do **not** delete `packages/core_domain/scheduler_authority.py`.
- Do **not** delete `apps/scheduler_authority_api/`.
- Do **not** change `apps/orchestrator_api/routers/scheduler.py` behavior when the flag is on.

### Entry conditions
- Phase 1 landed; suite green.

### Steps

1. **Introduce a feature flag.** In `packages/core_domain/m8_flags.py` (existing file), add:
   ```python
   UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER = "UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER"
   ```
   Add a helper `is_scheduler_authority_cluster_enabled() -> bool` defaulting to `False`.
2. **Gate instantiation.** In `packages/core_domain/services.py` around line 318–329 (the block that builds `self.scheduler_authority_cluster` and `self.scheduler_authority_support`), wrap construction in the flag. When disabled, set both attributes to a `NullSchedulerAuthorityCluster` stub that returns empty snapshots.
3. **Define the null stub.** Add `class NullSchedulerAuthorityCluster` in `packages/core_domain/scheduler_authority.py` with the minimum surface the routers and web UI consume:
   - `cluster_snapshot() -> dict` returning `{"enabled": False, ...}`
   - any other method touched by `apps/orchestrator_api/routers/scheduler.py`, `routers/ui.py`, `web_ui.py` (grep and enumerate before adding).
4. **Router guard.** In `apps/orchestrator_api/routers/scheduler.py`, when the flag is off, each route returns HTTP 200 with `{"enabled": false}` rather than 404. Do not remove the route.
5. **Web UI guard.** In `apps/orchestrator_api/web_ui.py`, when `scheduler_authority.enabled` is false, render a short banner saying "Scheduler authority cluster disabled (local-only mode)." Do not remove the panel.
6. **Update README.** In the "Remote worker productization and scheduler-authority peers" section, add a note: "This path is opt-in. Set `UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER=1` to enable. Default is local-only."
7. **Update `workflow.toml` defaults** in `packages/core_domain/config.py` so the `[scheduler_authority]` block is only materialized when the flag is set. Otherwise, skip it.
8. **Test coverage.** Add a small test in `tests/test_api.py` (or a new `tests/test_local_only_mode.py`) verifying: with the flag unset, `GET /ui` loads, `GET /runs` works, and `GET /scheduler/cluster` returns `{"enabled": false}`. With the flag set to `1`, existing behavior is preserved.

### Verification
```
pytest                                                 # ≥ 296 passing
UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER=1 pytest       # also green
python -m infra.scripts.offline_validation --skip-offline-probe
```

### Commit shape
- Commit 1: `feat(config): add scheduler-authority cluster feature flag (default off)`
- Commit 2: `refactor(services): instantiate null cluster when flag disabled`
- Commit 3: `test: verify local-only default works without scheduler authority`
- Commit 4: `docs(readme): note scheduler-authority is opt-in`

### Rollback
If any route crashes when the flag is off, restore the previous instantiation and convert the route guard into a simple config read. Do not push the phase until both states are green.

---

## 6. Phase 3 — Convert Service Mixins To Standalone Services

### Goal
- Replace the four `*ServiceMixin` classes with plain classes that `OrchestratorService` **composes** rather than **inherits**.
- This is the enabler for Phase 4. Do not attempt Phase 4 until this is done.

### Non-goals
- Do not delete methods.
- Do not change public method names or signatures on `OrchestratorService`.
- Do not split any file beyond the mixin itself.

### Entry conditions
- Phase 2 landed; suite green in both flag states.

### Current mixins (measured at plan authoring)
| File | Current class | Rename target |
| --- | --- | --- |
| `service_interaction.py` | `InteractionServiceMixin` | `InteractionService` |
| `service_memory_simulation.py` | `MemorySimulationServiceMixin` | `MemorySimulationService` |
| `service_lifecycle.py` | `LifecycleServiceMixin` | `LifecycleService` |
| `service_projection.py` | `ProjectionServiceMixin` | `ProjectionService` |

### Steps (repeat for each of the four mixins)

1. **Pick one mixin.** Start with the smallest (`service_interaction.py`, 701 lines) to prove the recipe.
2. **Change class signature.** Convert `class InteractionServiceMixin:` to `class InteractionService:` with `def __init__(self, orchestrator: "OrchestratorService") -> None: self._o = orchestrator`.
3. **Rewrite method bodies.** Replace every `self.foo` that currently resolves through `OrchestratorService` with `self._o.foo`. This is mechanical. Grep for `self\.` in the mixin and enumerate attributes that do not exist on the mixin itself — those are the ones to rewrite.
4. **Update `OrchestratorService` in `services.py`.**
   - Remove `InteractionServiceMixin` from the class bases.
   - In `__init__`, add `self.interaction = InteractionService(self)`.
   - For every public method that used to live on the mixin (still callable through inheritance), add a **thin delegate**: `def start_interaction(self, *a, **kw): return self.interaction.start_interaction(*a, **kw)`. This preserves the public facade surface; Phase 4 will remove the delegates.
5. **Run the suite.** Fix any `AttributeError` before moving on.
6. **Repeat** for `service_memory_simulation.py`, `service_projection.py`, `service_lifecycle.py`.

### Verification
```
pytest                                                 # ≥ 296 passing
grep -rn "Mixin" packages/core_domain/service_*.py     # should return 0 matches
grep -rn "class OrchestratorService" packages/core_domain/services.py
# the class declaration should have NO mixin bases remaining
```

### Commit shape
- One commit per mixin conversion. Four commits total.
- Message template: `refactor(core_domain): convert <name>Mixin to standalone service`

### Rollback
If a mixin method depends on *another* mixin's attribute that has not been converted yet, finish converting that mixin first (or postpone the current one). The conversion order does not matter; only that each commit is individually green.

---

## 7. Phase 4 — Split OrchestratorService Facade

### Goal
- Replace the 3820-line, 164-method `OrchestratorService` class with a **thin coordinator** (`OrchestratorApp` or keep the name `OrchestratorService` but make it a container).
- Each logical capability becomes an independently constructed service exposed as an attribute: `app.runs`, `app.memory`, `app.projection`, `app.lifecycle`, `app.governance`, `app.capability`, `app.scheduler`.
- Callers move from `service.some_method(...)` to `service.runs.some_method(...)` etc.

### Non-goals
- Do not change wire-level API behavior.
- Do not change the CLI output shape.
- Do not rename any method. Move methods; do not rename them.

### Entry conditions
- Phase 3 done.
- The four standalone services are already in place.
- Six other standalone services already exist: `OrchestrationExecutionService`, `ReviewPolicyService`, `RunLifecycleService`, `AuditReplayService`, `SchedulerAuthoritySupportService`, `OwnershipLeaseService`.

### Steps

1. **Inventory the 164 methods.** Produce a CSV at `docs/m2m/orchestrator_service_method_inventory.csv` with columns: method name, current line, target sub-service, public (imported by apps yes/no).
2. **Define sub-service targets.** For each method, assign it to one of:
   - `RunsService` (create/compile/recompile/resume/approve/reject/cancel)
   - `ProjectionService` (status/summary/inspection/replay-packet/audit-report)
   - `MemorySimulationService` (memory/simulation)
   - `LifecycleService` (claims/leases/attempts/snapshots/budget/handoffs/reconcile)
   - `CapabilityService` (capability routes / domain packs / worker pools)
   - `GovernanceService` (tech-debt / review-policy / metrics / alerts / release-readiness)
   - `InteractionService` (plan-graph / policy-preview / goal-packet / launch / operator-packet)
   - `SchedulerService` (cluster / leases / handoffs)
3. **Move methods in batches.** Move one sub-service at a time. Each batch:
   - Cut-paste the methods from `services.py` into the target service class.
   - Update `OrchestratorService` to expose them via `self.<sub>.method_name(...)` passthrough delegates **temporarily** (these delegates go away in step 5).
   - Run `pytest`. Fix breakage before the next batch.
4. **Update router imports.** In `apps/orchestrator_api/routers/*.py`, change call sites from `service.method(...)` to `service.<sub>.method(...)`. Example:
   - Before: `service.status_detail(run_id)`
   - After: `service.projection.status_detail(run_id)`
5. **Update CLI call sites** in `apps/operator_cli/main.py` and `apps/operator_tui/dashboard.py` the same way.
6. **Remove the passthrough delegates** from `OrchestratorService`. The class should now be ≤ 400 lines and mostly `__init__` wiring + attribute exposure.
7. **Break the back-references.** Delete `if TYPE_CHECKING: from ...services import OrchestratorService` imports in:
   - `service_audit_replay.py`
   - `service_orchestration.py`
   - `service_ownership_lease.py`
   - `service_review_policy.py`
   - `service_run_lifecycle.py`
   - `service_scheduler_authority_support.py`
   Each sub-service should take only the specific collaborators it needs (e.g., a repository, another service) through `__init__`, not the whole facade.

### Verification
```
pytest
python -m infra.scripts.offline_validation --skip-offline-probe
wc -l packages/core_domain/services.py      # should be ≤ 500 lines
grep -c "^    def\|^    async def" packages/core_domain/services.py
# should be ≤ 20 methods (just __init__, properties, factory helpers)
```

### Commit shape
- One commit per sub-service batch (8 commits).
- Final commit: `refactor(core_domain): remove facade passthroughs; OrchestratorService becomes a container`

### Rollback
If a router or CLI call site references a method that ended up in the wrong sub-service, fix the assignment in the inventory CSV and redo that single batch. Do not hand-edit the final layout.

---

## 8. Phase 5 — Split `repositories.py` Per Aggregate

### Goal
- Break the 1621-line `repositories.py` into **one file per aggregate** under `packages/core_domain/infrastructure/repositories/` (directory will be formalized in Phase 6; for now create it as a flat sibling package).

### Non-goals
- Do not introduce a `Repository` interface / protocol. Keep concrete classes.
- Do not change SQL. This is a pure move.

### Entry conditions
- Phase 4 done.

### Target layout
Create `packages/core_domain/repositories/` as a package (`__init__.py` re-exports everything for backward compatibility), then one file per class:

```
packages/core_domain/repositories/
├── __init__.py              # re-exports all 19 classes
├── base.py                  # RepositoryBase
├── run.py                   # RunRepository
├── preset.py                # PresetRepository
├── intent_session.py        # IntentSessionRepository
├── task.py                  # TaskRepository
├── evidence.py              # EvidenceRepository
├── review.py                # ReviewRepository
├── event.py                 # EventRepository
├── memory_item.py           # MemoryItemRepository
├── simulation_record.py     # SimulationRecordRepository
├── handoff.py               # HandoffRepository
├── runtime_state.py         # RuntimeStateRepository
├── runtime_claim.py         # RuntimeClaimRepository
├── run_snapshot.py          # RunSnapshotRepository
├── runtime_attempt.py       # RuntimeAttemptRepository
├── budget_ledger.py         # BudgetLedgerRepository
├── worker_lease.py          # WorkerLeaseRepository
└── scheduler/
    ├── __init__.py
    ├── lease_proposal.py    # SchedulerLeaseProposalRepository
    ├── lease_decision.py    # SchedulerLeaseDecisionRepository
    └── peer_heartbeat.py    # SchedulerPeerHeartbeatRepository
```

### Steps

1. Delete the old `packages/core_domain/repositories.py`; replace with the directory above.
2. Move each class to its own file verbatim. Only adjust imports.
3. In `packages/core_domain/repositories/__init__.py`, re-export every repository class so the existing `from packages.core_domain.repositories import RunRepository, ...` in `services.py` still works.
4. Run `pytest`. Fix any missed import.

### Verification
```
pytest
grep -rn "from packages.core_domain.repositories import" packages/ apps/ tests/
# every match must still resolve
wc -l packages/core_domain/repositories/*.py
# no single file should exceed 400 lines
```

### Commit shape
- Commit 1: `refactor(repositories): split per aggregate, preserve re-exports`

(single commit is fine because it's a mechanical move)

### Rollback
If any caller breaks, make sure the `__init__.py` re-exports the missing name.

---

## 9. Phase 6 — Sub-package `core_domain/`

### Goal
- Impose DDD-style sub-packaging on `core_domain/`: `domain/`, `application/`, `platform/`, `infrastructure/`.
- Reduce the flat dump of 35 modules to a navigable tree.

### Non-goals
- Do not split any file further than it already is.
- Do not change any class or function. This is move-only.

### Target layout

```
packages/core_domain/
├── __init__.py
├── domain/                       # entities, value objects, domain errors
│   ├── errors.py                 # was: errors.py
│   └── service_types.py          # was: service_types.py
├── application/                  # use-case services (orchestrator sub-services)
│   ├── run_lifecycle.py          # was: service_run_lifecycle.py
│   ├── lifecycle.py              # was: service_lifecycle.py (renamed from Mixin in Phase 3)
│   ├── projection.py             # was: service_projection.py
│   ├── memory_simulation.py      # was: service_memory_simulation.py
│   ├── interaction.py            # was: service_interaction.py
│   ├── orchestration.py          # was: service_orchestration.py
│   ├── ownership_lease.py        # was: service_ownership_lease.py
│   ├── review_policy.py          # was: service_review_policy.py
│   ├── audit_replay.py           # was: service_audit_replay.py
│   └── scheduler_authority_support.py  # was: service_scheduler_authority_support.py
├── platform/                     # cross-cutting platform services
│   ├── capability_plane.py
│   ├── orchestration_engine.py
│   ├── scheduler_authority.py
│   ├── domain_packs.py
│   ├── interaction_catalog.py
│   ├── execution_profiles.py
│   ├── cluster_router.py
│   ├── presets.py
│   ├── resolver.py
│   ├── governance.py
│   ├── simulation.py
│   ├── memory.py
│   ├── auto_review.py
│   ├── compile.py
│   ├── repo_mutation.py
│   ├── evidence_builder.py
│   ├── external_workers.py
│   ├── context_budget.py
│   ├── agent_tools.py
│   ├── skills.py
│   ├── observability.py
│   └── m8_flags.py
├── infrastructure/
│   ├── db.py
│   └── repositories/             # from Phase 5
└── services.py                   # thin coordinator from Phase 4
```

### Steps

1. **Move in this order** (to minimize the number of files with broken imports at any one time):
   - First: `domain/` (errors, service_types)
   - Second: `infrastructure/` (db, repositories — repositories already a package from Phase 5, just move the whole thing)
   - Third: `application/` (all `service_*.py`)
   - Fourth: `platform/` (everything else)
2. **Update imports.** Use a single pass with a scripted search-and-replace. Maintain a mapping file at `docs/m2m/import_rewrites.txt` that lists each old→new module path. Apply it to `packages/`, `apps/`, `infra/`, and `tests/`.
3. **Keep `packages/core_domain/__init__.py` as a compatibility shim.** Re-export the most-used names so old imports still work. The shim stays for one milestone, then is removed (out of this plan's scope).
4. Run `pytest`.

### Verification
```
pytest
python -m infra.scripts.offline_validation --skip-offline-probe
ls packages/core_domain/           # no longer a flat dump of .py files
```

### Commit shape
- Commit 1: `refactor(core_domain): carve out domain/ sub-package`
- Commit 2: `refactor(core_domain): carve out infrastructure/ sub-package`
- Commit 3: `refactor(core_domain): carve out application/ sub-package`
- Commit 4: `refactor(core_domain): carve out platform/ sub-package`
- Commit 5: `refactor(core_domain): leave compatibility shim in __init__`

### Rollback
This phase is a pure move. If anything breaks, it is a missed import rewrite. Fix the import, retry.

---

## 10. Phase 7 — Split `apps/operator_cli/main.py`

### Goal
- Break the 1101-line CLI into command-group files.

### Target layout

```
apps/operator_cli/
├── __init__.py
├── main.py                       # entry point only: builds Typer app, registers groups
├── _context.py                   # shared Typer context / DI wiring
└── commands/
    ├── __init__.py
    ├── run.py                    # run create/compile/resume/approve/... (largest)
    ├── capability.py             # capability list/sources/mcp-profiles/worker-pools/projection
    ├── domain_pack.py            # domain-pack list/resolve/validate/export-skill
    ├── governance.py             # governance tech-debt/review-policy/release-readiness/domain-pack
    ├── memory.py                 # memory namespace/item/retrieve-preview
    ├── simulation.py             # simulation policy list
    ├── config.py                 # config show
    ├── db.py                     # db reset/workspace-path
    ├── scheduler.py              # scheduler cluster/lease
    ├── task.py                   # task evidence
    └── tui.py                    # tui subcommand
```

### Steps

1. Create `commands/` with one file per group.
2. Use Typer sub-apps: each command file defines a `app = typer.Typer()` and is registered in `main.py` with `main_app.add_typer(run.app, name="run")`.
3. Move each subcommand to its file. Do not change the CLI invocation syntax. Validate with a golden script that runs representative commands and diffs against captured output.
4. Target: `main.py` ≤ 150 lines.

### Verification
```
pytest tests/test_cli.py
workflowctl --help                              # subcommand tree matches README
workflowctl run --help                          # all run subcommands present
workflowctl governance --help
```

### Commit shape
- One commit per command group. ~10 commits.

### Rollback
Typer sub-app registration order matters for help output. If help text regresses, reorder `add_typer` calls.

---

## 11. Phase 8 — Unify Three API Processes Into One

### Goal
- Keep all existing HTTP behavior, but run from a single `apps/api/main.py` with a `--role` flag: `orchestrator`, `remote-worker`, `scheduler-authority`, `all`.
- Reduce operational surface for local users: one process, one port.

### Non-goals
- Do not remove `apps/remote_worker_api/` or `apps/scheduler_authority_api/` code — merge their routers into the unified app.
- Do not change route paths or response shapes.

### Steps

1. Create `apps/api/` with:
   - `main.py` — builds FastAPI app, adds role-gated routers, exposes uvicorn entry point.
   - `roles.py` — enum of roles and which router sets each exposes.
2. Move each existing `apps/<name>_api/main.py` to `apps/api/roles/<name>.py` as a **router bundle** (a function `register(app: FastAPI) -> None`).
3. Update console scripts in `pyproject.toml`:
   - Keep legacy entry points (`workflow-remote-worker`, `workflow-scheduler-authority`) but have them call the unified app with a preset role.
   - Add a new `workflow-api` that takes `--role`.
4. Update `infra/scripts/manage.py dev` to use the unified entry.
5. Update README to reflect the unified form; keep legacy forms documented as aliases.

### Verification
```
pytest
workflow-api --role=orchestrator --host 127.0.0.1 --port 8000 &
curl http://127.0.0.1:8000/ui
workflow-remote-worker &                        # legacy alias still works
workflow-scheduler-authority &                  # legacy alias still works (flag-gated)
```

### Commit shape
- Commit 1: `feat(api): add unified api entry point with role flag`
- Commit 2: `refactor(api): route legacy entry points through unified app`
- Commit 3: `docs(readme): document unified api entry point`

### Rollback
If a legacy entry point breaks for an existing user, keep its original `main.py` alive as a thin shim that imports the unified app.

---

## 12. Out Of Scope (Do Not Do In This Plan)

- Introducing a `Repository` protocol or any multi-backend abstraction. SQLite stays.
- Replacing SQLite with Postgres / a networked store.
- Deleting `scheduler_authority.py` or the cluster API. They are feature-flagged off, not removed.
- Any new feature (workbench UI, generated roles, automation, eval pipeline). Those belong to M36+.
- Rewriting tests from scratch. Move them when a module moves; otherwise leave them.
- Changing `packages/contracts/models.py` shapes.
- Renaming any CLI subcommand or HTTP route.

---

## 13. Completion Criteria

All of the following must be true to declare the plan complete:

1. `pytest` passes ≥ 296 tests (target: more, if move triggers finer-grained tests).
2. `python -m infra.scripts.offline_validation --skip-offline-probe` passes.
3. `python -m infra.scripts.check_doc_links` passes.
4. `wc -l packages/core_domain/services.py` ≤ 500.
5. `grep -c "Mixin" packages/core_domain/application/*.py` == 0.
6. No file in `packages/core_domain/application/` or `packages/core_domain/platform/` exceeds 1200 lines. (Projection and Lifecycle may still be large; that is acceptable after Phase 6 because they are *one* service each, not mixed.)
7. `packages/core_domain/` has at most **6 top-level `.py` files** (`__init__.py`, `services.py`, plus compatibility shims). Everything else lives in sub-packages.
8. `docs/tech-debt-registry.md` has `TD-STRUCT-001` moved from "Open Debt" to "Repaid Debt".
9. A final freeze review doc lands at `docs/reviews/m2m-monolith-to-modular-remediation-review.md` summarizing the phases, verification evidence, and residual risks.

---

## 14. Handoff Notes For The Executing Agent

- If you are an LLM executor (codex / Claude Code), run one phase per session. Do not attempt multiple phases in a single session — the context window and the risk of mis-merged state are both real.
- After each phase, before opening the next, re-read this document from the top. The invariants in Section 1 are easy to forget after a few hours of mechanical work.
- If a verification command fails with output you do not understand, **stop and ask the repository owner**. Do not "fix" a test by deleting assertions, and never use `pytest --no-verify`-style bypasses.
- Every phase should produce a short dated log entry at `docs/m2m/phase_<n>_log.md` with: what changed, what verification was run, what drift from this plan was observed, and any TODOs that were deferred.
- When in doubt, preserve behavior. The explicit goal of this plan is that **external observers (CLI users, API consumers, dashboard viewers) cannot tell the refactor happened**. If they can tell, you went too far.
