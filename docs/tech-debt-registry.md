# Technical Debt Registry

**Document role:** a living architecture debt register for the current repository, not a milestone-specific appendix.  
**Usage rule:** this file should be reviewed in freeze reviews, governance reports, and any scope-rebaseline discussion before new breadth work is approved.

---

# 1. Registry Rules

- Record only debt that has been explicitly accepted or clearly observed in the repository.
- Do not use this file as a generic backlog for untriaged ideas.
- Every item must describe:
  - where it was introduced
  - where it is planned to be repaid
  - whether it is still active, partially repaid, or fully retired
  - what it blocks
- Historical debt may be moved into the repaid section, but should not disappear without review evidence.
- Cross-milestone structural debt belongs here even if it spans several cycles.

---

# 2. Repaid Debt

| ID | Description | Introduced In | Repaid In | Result |
| --- | --- | --- | --- | --- |
| TD-002 | `PresetResolver` only supported `manual_select` and had no deterministic suggestion path | M0 | M1 | Added deterministic offline `suggest()` while keeping execution explicit |
| TD-003 | `HandoffLite` was frozen only as a contract and not persisted | M0 | M1 | Added persistence plus `status-detail`, `handoffs`, smoke, and offline-validation coverage |
| TD-004 | thin compile existed only as an internal placeholder and not as a public lifecycle surface | M0 | M1 | Added explicit public `compile / recompile / resume` lifecycle surfaces |
| TD-005 | execution initially relied on a shell-only lane with no stable GPT-capable CLI route | M0 | M5 Phase 3 | `WorkerRouter`, multi-route capability selection, adapter pinning, `NoopAdapter`, and `OpenCodeAdapter` now provide a real multi-adapter execution baseline |
| TD-011 | `packages/core_domain/services.py` concentrated too much orchestration, projection, memory, simulation, and lifecycle logic in one file | M2-M7 | Pre-M8 Phase C | Extracted bounded service modules for projection/reporting, memory/simulation, and lifecycle/review while keeping `OrchestratorService` as the public facade |
| TD-016 | subprocess-backed adapters did not enforce declared timeout budgets and inherited too much parent environment state | M5-M7 | Pre-M8 Phase B | Added timeout enforcement, subprocess env allowlisting, interpreter-portable compile commands, and explicit local execution trust-boundary docs |
| TD-012 | `infra/scripts/offline_validation.py` had grown into an oversized validation script instead of a modular validation package | M5-M7 | Pre-M8 Phase D | Split validation flows into `infra/validation/` modules and reduced `offline_validation.py` to a thin entry wrapper |
| TD-013 | runtime-brief and memory-retrieval assembly lacked a hard context-budget preflight and explicit pruning guard path | M5-M7 | Pre-M8 Phase D | Added diagnostics-first `context_budget`, gateway preflight guarding, trace context, and ADR-006 for the next-step pruning strategy |
| TD-014 | key runtime dependencies were pinned with narrow upper bounds, making routine compatibility and security updates harder than necessary | M5-M7 | Pre-M8 Phase E | Widened core runtime upper bounds selectively and documented the repository's dependency/versioning policy before `M8` |
| TD-015 | governance reports parsed Markdown debt prose directly instead of consuming a structured canonical source | M3-M7 | Pre-M8 Phase D | Added canonical JSON governance sources with Markdown compatibility fallback and explicit source-contract reporting |
| TD-017 | clean source-package/export flow was not productized, so review or handoff snapshots could include local state, DBs, artifacts, and repo noise | M5-M7 | Pre-M8 Phase E | Added source-package manifest/export tooling, minimal automation gates, and freeze-review provenance for handoff claims |
| TD-018 | canonical repo docs mixed local absolute links and current/historical guidance without a portable source map | M1-M7 | Pre-M8 Phase E | Finished portable-link cleanup for living docs and formalized current-vs-historical doc governance in the active workflow guide |

---

# 3. Open Debt

| ID | Description | Introduced In | Planned Repayment Phase | Current Status | Blocking Impact |
| --- | --- | --- | --- | --- | --- |
| TD-001 | claim and worker-lease semantics remain local-only and do not provide true distributed resource ownership | M0 | M9 | partially_repaid | blocks external worker pools, distributed locking, and real multi-node scheduling |
| TD-006 | review policy breadth still stops at `auto_only`, `recommended`, `human_required`, and `mandatory`; `optional` remains reference-only | M0 | M9 | partially_repaid | blocks a fuller runtime policy family but does not block the current shipped baseline |
| TD-007 | `run_events` and trace export are stronger after `M8`, but replay-grade linkage and first-class metrics are still incomplete | M0 | M9 | partially_repaid | blocks richer observability, replay analysis, and structured runtime diagnostics |
| TD-008 | the `M8` durable pilot added runtime-ref mapping, but complex interrupt/resume/checkpoint merge semantics are still incomplete | M0 | M9 | partially_repaid | blocks richer recovery workflows and deeper runtime fault handling |
| TD-009 | execution semantics are still serial-first and do not implement real claim/lease/barrier concurrency | M0 | M9 | partially_repaid | blocks safe parallel execution and higher-throughput scheduling |
| TD-010 | governance visibility is stronger than before, but debt tracking is still document-centric and not yet quantitatively automated | M0 | M9 | partially_repaid | blocks deeper debt trend analysis, alerting, and richer dashboard/reporting automation |

---

# 4. Freeze Review Questions

1. Are all accepted cross-milestone debts from `M0` through the current cycle recorded here?
2. Does any active debt item now block the next milestone entry gate?
3. Have all pre-entry hardening debts been repaid before feature breadth resumes?
4. Were any completed debts retired with explicit review evidence rather than silently dropped?
