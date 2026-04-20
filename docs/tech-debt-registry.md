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
| TD-006 | review policy breadth stopped at `auto_only`, `recommended`, `human_required`, and `mandatory`; `optional` was reference-only | M0 | M9 | Added executable `optional` advisory-review runtime behavior, seed coverage, and governance/readiness parity |
| TD-007 | `run_events` and trace export lacked replay-grade linkage and first-class run metrics | M0 | M9 | Added replay-packet projection, end-to-end run metrics, and richer audit/status observability surfaces |
| TD-008 | the durable pilot still lacked explicit interrupt/resume/checkpoint lineage and reconciliation semantics | M0 | M9 | Added structured durable lineage history, durable transition inspection, and terminal/review checkpoint reconciliation |
| TD-010 | governance visibility remained document-centric and lacked quantitative automation and alerts | M0 | M9 | Added quantitative governance metrics, automated alert reports, and updated release-readiness integration |
| TD-001 | claim and worker-lease semantics remained local-only and did not provide explicit repository-owned ownership topology | M0 | M10 | Added explicit claim/worker ownership topology, attempt-aware claim and lease linkage, coherent ownership projections, and local batch-domain semantics without turning the runtime into a multi-node scheduler |
| TD-009 | execution semantics were still serial-first and did not implement claim/lease/barrier-aware local batch concurrency | M0 | M10 | Added local batch-barrier events, parallel batch resume semantics, projection surfaces, and CLI/API batch-resume entry points for the supported local control plane |
| TD-020 | the full operator web UI and human control surface were still missing beyond CLI/API and the read-mostly TUI | M5-M13 | M14 | Added a built-in FastAPI web operator surface with dashboard, run explorer, pending-review console, governance/config pages, and controller-owned human action routes |
| TD-019 | hosted remote worker pools and multi-node scheduling were still not productized beyond the shipped local-first / loopback external-worker baseline | M10 | M15 | Added single-control-plane remote HTTP worker pools, callback-driven lease renewal/completion recording, remote worker bootstrap packaging, and remote worker recovery coverage while keeping repository truth in the control plane |
| TD-021 | a centralized scheduler-authority first slice existed for multi-control-plane identity, lease proposal, and arbitration provenance, but true distributed scheduler consensus and cross-control-plane failover were still incomplete | M15 | M20 | Added majority-quorum scheduler authority peers, committed cross-control-plane lease ownership, fencing-token enforced remote callbacks, takeover handoff lineage, cluster operator surfaces, and offline cutover validation while keeping repository truth inside the control planes |

---

# 3. Open Debt

| ID | Description | Introduced In | Planned Repayment Phase | Current Status | Blocking Impact |
| --- | --- | --- | --- | --- | --- |

---

# 4. Freeze Review Questions

1. Are all accepted cross-milestone debts from `M0` through the current cycle recorded here?
2. Does any active debt item now block the next milestone entry gate?
3. Have all pre-entry hardening debts been repaid before feature breadth resumes?
4. Were any completed debts retired with explicit review evidence rather than silently dropped?
