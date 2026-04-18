# M6 Phase 3 - Memory Namespace Baseline And Run Memory Candidates

**Phase status:** Completed  
**Phase position:** This phase starts after `M6 Phase 2` makes the domain-pack platform inspectable and mechanically valid. It begins the second-cycle `Memory` line in the smallest possible way: seed-backed memory namespaces plus read-only run memory candidates.

**Entry condition:** Domain Pack platformization, preview, and validation are already in place, and the repository now needs a real `Memory` bridge without jumping straight into persistence-heavy retrieval or semantic search.

---

## 1. Reassessment

Current implementation status:

- the runtime already has rich run data:
  - summary
  - event inspection
  - audit report
  - evidence
  - snapshots
  - claims / attempts / leases
- but none of that is yet expressed through an explicit memory namespace model

What should happen now:

- add seed-backed `MemoryNamespace` definitions
- add read-only `run memory candidates` derived from current run outputs
- avoid persistence-heavy memory item lifecycle for now

Decision:

- start with namespace catalog + candidate projection only
- treat persistence, retrieval, and semantic search as later phases

---

## 2. In Scope

- add memory namespace contracts and seed catalog
- project run-level memory candidates from existing run/audit/evidence surfaces
- expose namespace and candidate views through CLI/API/docs/validation

---

## 3. Out Of Scope

- persistent memory item CRUD
- semantic retrieval
- embedding/vector infrastructure
- cross-run memory ranking
- simulation hooks

---

## 4. Target Baseline

- seed-backed namespaces exist for the planned memory plane
- a completed or failed run can produce structured memory candidates
- CLI/API can show namespaces and candidates without mutating storage

---

## 5. Phase Task Breakdown Principle

This phase is expected to split into:

1. Memory namespace contracts and seed catalog
2. Run memory candidate projection from existing run surfaces
3. CLI/API/docs/validation closeout

---

## 6. Outcome

- Added seed-backed `MemoryNamespace` catalog with the first baseline namespaces:
  - `repo`
  - `failure`
  - `policy`
  - `release`
- Added read-only `run memory candidates` derived from existing:
  - summary
  - review state
  - audit bundle
  - evidence/run lineage context
- Exposed the new baseline through:
  - `memory namespace list`
  - `run memory-candidates`
  - `GET /memory/namespaces`
  - `GET /runs/{id}/memory-candidates`
- Extended offline validation so CLI/API acceptance now proves the memory namespace catalog and run memory candidates.

Verification:

- `pytest tests/test_contracts.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - `169 passed`
- `pytest -q`
  - `190 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

Result:

- Phase gate passed.
- The repository now has a real, explicit `Memory` baseline without yet taking on persistence-heavy retrieval complexity.

---

## 7. Next Reassessment

- The next `Memory` slice should decide whether to:
  - keep memory read-only but add stronger failure/repair-specific candidates
  - or introduce the first bounded persistent memory-item baseline
- If the priority is to keep following the original roadmap, the next phase should favor a **bounded persistent memory-item baseline** over more read-only formatting work.
