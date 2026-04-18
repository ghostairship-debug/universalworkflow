# M6 Phase 4 - Persistent Memory Item Baseline

**Phase status:** Completed  
**Phase position:** This phase starts after `M6 Phase 3` proves the seed-backed namespace catalog and read-only run memory candidates. It is the first bounded persistence step for the `Memory` line.

**Entry condition:** Memory namespaces and run memory candidates already exist, but there is still no persisted `memory_items` baseline, no queryable stored memory history, and no retrieval-oriented bridge beyond transient projections.

---

## 1. Reassessment

Current implementation status:

- namespaces exist
- run memory candidates exist
- no persistent memory-item table exists yet
- memory remains projection-only

Decision:

- keep the next step narrow
- persist only a bounded `memory_items` baseline
- do not jump to semantic retrieval or ranking

---

## 2. In Scope

- introduce the first persistent `memory_items` baseline
- materialize selected run memory candidates into stored items
- expose list/query surfaces by namespace and run

---

## 3. Out Of Scope

- embeddings or vector retrieval
- cross-run ranking
- automatic memory injection back into compile/resume
- simulation memory

---

## 4. Target Baseline

- one durable `memory_items` table exists
- one bounded materialization path exists from run memory candidates to stored items
- operator surfaces can list memory items by namespace and run

---

## 5. Phase Task Breakdown Principle

This phase is expected to split into:

1. Memory-item contracts and persistence baseline
2. Candidate-to-item materialization path
3. CLI/API/query/docs/validation closeout

---

## 6. Outcome

- Added the first persisted `MemoryItem` contract and SQLite `memory_items` table.
- Added repository support for:
  - create
  - get
  - get by source candidate
  - list by run
  - list by namespace
- Made run memory candidate IDs stable across repeated reads so operator-triggered materialization is addressable.
- Added a bounded service path that materializes a selected run memory candidate into a durable `memory_item`.
- Added `memory_item_materialized` timeline evidence so the new persistence step is auditable.
- Exposed the new baseline through:
  - `run materialize-memory`
  - `run memory-items`
  - `memory item list`
  - `POST /runs/{id}/memory-items`
  - `GET /runs/{id}/memory-items`
  - `GET /memory/items`
- Extended offline validation so both CLI and API acceptance now prove:
  - persistent materialization
  - run-scoped listing
  - namespace-scoped listing

Verification:

- `pytest tests/test_contracts.py tests/test_repositories.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - `183 passed`
- `pytest -q`
  - `192 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

Result:

- Phase gate passed.
- The repository now has the first bounded durable memory baseline without yet taking on retrieval ranking, semantic search, or automatic memory injection.

---

## 7. Next Reassessment

- The next `Memory` slice should decide whether to:
  - keep the line operator-driven and add retrieval preview / selection surfaces
  - or start a tightly bounded memory-to-compile bridge
- To stay aligned with the roadmap and avoid jumping too early into automatic injection, the next phase should favor a **retrieval preview and selection baseline** before any compile/resume memory injection.
