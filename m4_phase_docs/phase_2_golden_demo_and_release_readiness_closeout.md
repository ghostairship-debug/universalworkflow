# M4 Phase 2 - Golden Demo And Release Readiness Closeout

**Phase status:** Completed  
**Phase position:** This phase starts after `M4 Phase 1` proves `CapabilityRegistry + minimal Domain Pack + M4 smoke`. It turns the current runtime from an internally validated baseline into a release-shaped, operator-facing closeout package.

**Entry condition:** `M4 Smoke` is now green and the remaining `M4` gap is not runtime breadth. It is packaging, release-readiness visibility, and a canonical demo path.

---

## 1. Reassessment

Current implementation status:

- The runtime already has enough operator surfaces to explain a run.
- The repository already has governance reports for tech debt and review policy.
- `offline_validation` already proves the system end-to-end, but that proof is not yet turned into a clean release-readiness surface or a reusable demo bundle.

Legacy references worth absorbing now:

- no new structural legacy import is needed for this phase
- the useful reference is the existing discipline from earlier hardening work:
  - review-ready bundles
  - structured governance projections
  - test-first closeout

What is worth reusing:

- package current capabilities instead of expanding the kernel again
- keep the operator surface CLI-first
- make release readiness machine-checkable

What must not be reused:

- a Web console
- a heavy dashboard subsystem
- another broad runtime expansion disguised as “closeout”

---

## 2. In Scope

- add a structured `release-readiness` governance report
- add a canonical `golden demo` runner on a fresh local DB
- expose release-readiness through CLI and API
- update validation, README, and phase closeout docs

---

## 3. Out Of Scope

- implementing `optional`
- Web UI or TUI
- packaging or installer work
- cloud deployment
- full release engineering automation

---

## 4. Target Baseline

- `release-readiness`
  - consumes current governance + validation signals
  - reports whether the shipped local-first runtime is ready for the current milestone baseline
  - makes remaining gaps explicit instead of hiding them
- `golden demo`
  - runs a canonical set of flows on a fresh database
  - produces a structured packet covering:
    - auto path
    - human-review path
    - recommended escalation path
    - mandatory sign-off path
    - noop path
    - capability-route and domain-pack summary
- CLI/API/documentation all match the shipped closeout behavior

---

## 5. Phase Task Breakdown Principle

This phase is expected to split into:

1. Release-readiness governance report and projections
2. Golden demo runner and verification
3. Docs, README, and closeout materials

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- `governance release-readiness` works
- `GET /governance/release-readiness` works
- `manage.py demo` produces a structured canonical demo packet
- validation and tests prove the closeout surfaces
- full verification remains green

---

## 7. Outcome

- Added a structured `release-readiness` governance report that combines validation, review-policy baseline, capability routes, domain-pack baseline, and milestone gates.
- Exposed release readiness through CLI and API.
- Added `manage.py demo` as a canonical local golden-demo packet runner covering auto, human-review, recommended, mandatory, and noop paths.
- Updated README, offline validation, and closeout materials so the phase is operator-visible and review-ready.
- Verified with:
  - `pytest tests/test_governance.py tests/test_api.py tests/test_cli.py tests/test_release_closeout.py -q` (`78 passed`)
  - `pytest -q` (`162 passed`)
  - `python -m infra.scripts.manage --db-path state/demo_phase2.db demo` (`status=completed`)
  - `python -m infra.scripts.offline_validation --skip-offline-probe` (`overall_passed=true`)

---

## 8. Next Reassessment

- The runtime now has a release-shaped closeout surface for the current milestone baseline.
- The next decision is no longer “how to package M4”. It is whether `optional` should still be pulled into this project scope, or whether the current milestone should be treated as complete and the remaining gap moved into the next cycle.
