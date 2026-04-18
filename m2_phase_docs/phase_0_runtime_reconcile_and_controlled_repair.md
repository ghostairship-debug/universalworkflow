# M2 Phase 0 - Runtime Reconcile And Controlled Repair

**Phase status:** Completed
**Verification summary:** `pytest` passed with `67 passed`; `python -m infra.scripts.offline_validation --skip-offline-probe` returned `overall_passed=true` and covered shell, human-review, noop, and reconcile / repair flows.

**Phase position:** This phase starts after `M1.5` closes `TD-005`. It turns the current read-only `inspection` surface into a minimal `inspect -> recommend -> apply` loop for safe, run-centric repairs.

**Entry condition:** `M1.5` is complete, `TD-005` is repaid, and the repository has stable shell/noop execution plus dry-run inspection.

**Sequencing note:** The canonical milestone sequence is [docs/m1_to_m2_progression.md](/D:/Universal%20Agentic%20workflow/docs/m1_to_m2_progression.md:1). `M2` does not start directly after the `M1` freeze review; it starts after `M1.5`.

---

## 1. Reassessment

Current implementation status:

- The repository already detects four classes of bad states through `inspection`.
- Diagnostics are operator-friendly, but repairs are still manual.
- `TD-008` is only partially repaid because the runtime can resume, but cannot yet reconcile drifted state safely.
- `TD-001` and `TD-009` remain M2 topics, but they are not the next step because claim/lease semantics require a safer repair baseline first.

Legacy references worth absorbing now:

- `runtime_reconcile_service.py` for the `inspect -> dry run -> apply` framing
- `test_phase_task_card_runtime.py` for drift and repair regression shapes

This phase keeps the current run-centric architecture intact:

- no project kernel
- no phase/task-card runtime backport
- no blanket auto-repair

---

## 2. In Scope

- add dedicated reconcile / repair logic for current run-centric bad states
- keep `inspection` read-only but enrich it with repairability metadata
- add safe apply actions only for repairs that preserve current repository semantics
- add operator surfaces for dry-run reconcile and apply repair
- add tests for repair planning and repair application

---

## 3. Out Of Scope

- claim / lease / barrier semantics
- parallel or distributed runtime recovery
- richer review policy enums
- replaying lost execution to reconstruct missing evidence
- porting legacy reconcile service structure into the current repository

---

## 4. Key Constraints

- every repair action must be explicit and bounded
- manual-only problems must stay manual-only
- repair actions may only mutate current repository semantics
- repairs must be auditable
- dry-run inspection must remain side-effect free

---

## 5. Phase Task Breakdown Principle

This phase is split into three complex tasks:

1. Reconcile catalog extraction and runtime-state query helpers
2. Controlled repair actions for safe, current-repo problems
3. CLI/API/docs/verification closeout

Each task must ship with tests before the next task is considered complete.

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- `inspection` reports which problems are repairable
- repository/runtime helpers can identify latest, live, and terminal runtime state refs
- safe repair actions exist for at least:
  - completed-but-live runtime
  - cancelled-but-live runtime
  - prepared snapshot residue
- manual-only problems stay non-repairable
- CLI and API both expose reconcile / apply flows
- full `pytest` passes

Gate outcome:

- Passed: `inspection` now reports `repairable` and `repair_action` metadata
- Passed: runtime-state repositories expose latest/live/terminal query helpers
- Passed: safe repair actions cover completed-but-live runtime, cancelled-but-live runtime, and prepared snapshot residue
- Passed: missing-evidence review mismatches remain manual-only and fail with a stable error
- Passed: CLI and API both expose reconcile plan and apply flows
- Passed: full `pytest` and offline validation succeeded

---

## 7. Risks And Rollback

- Risk: repairs silently rewrite history
  Control: keep dry-run and apply separate, and log every applied repair
- Risk: repair scope grows into a legacy runtime engine
  Control: only support the current run-centric failure catalog
- Risk: operator surfaces hide non-repairable cases
  Control: return explicit `repairable=false` metadata and stable errors

## 8. Outcome

- The repository now supports a minimal `inspect -> recommend -> apply` repair loop without importing legacy runtime structure.
- `TD-008` is further repaid, but not fully closed; complex interrupt / checkpoint merge work still remains outside this phase.
- The next recommended phase is to tackle claim-ready runtime lifecycle semantics, not to broaden repair actions indiscriminately.
