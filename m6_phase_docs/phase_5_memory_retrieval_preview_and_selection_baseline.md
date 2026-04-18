# M6 Phase 5 - Memory Retrieval Preview And Selection Baseline

**Phase status:** Completed  
**Phase position:** This phase starts after `M6 Phase 4` creates durable `memory_items`. It keeps the `Memory` line operator-driven and adds the first retrieval-preview surface without yet injecting memory back into compile or resume.

**Entry condition:** Stored `memory_items` now exist and can be listed, but there is still no explicit retrieval preview, no manual selection surface, and no bounded way to see which items would compose a retrieval brief for future runtime use.

---

## 1. Reassessment

Current implementation status:

- seed-backed namespaces exist
- run memory candidates exist
- durable `memory_items` now exist
- materialization is operator-triggered and auditable
- there is still no retrieval-preview bridge

Decision:

- keep the next step read-mostly
- preview retrieval from stored memory items
- allow bounded manual selection by item id and namespace
- do not inject the preview into compile/resume yet

---

## 2. In Scope

- introduce a structured retrieval-preview baseline over stored `memory_items`
- support bounded selection through explicit `memory_item_id` filters and namespace filters
- expose retrieval preview through CLI/API/docs/validation

---

## 3. Out Of Scope

- automatic memory injection into `TaskPacket`
- semantic ranking, embeddings, or vector search
- memory item update/delete lifecycle
- simulation memory

---

## 4. Target Baseline

- one retrieval preview can be generated from stored `memory_items`
- operators can manually constrain the preview by item id and namespace
- CLI/API can inspect the preview before any future compile-time memory bridge exists

---

## 5. Phase Task Breakdown Principle

This phase is expected to split into:

1. Retrieval-preview contract and selection logic
2. CLI/API retrieval-preview surfaces
3. Docs/validation/closeout

---

## 6. Outcome

- Added a structured `MemoryRetrievalPreview` contract.
- Added service support to build a retrieval preview from stored `memory_items` using:
  - `preset_id`
  - `run_id`
  - `namespace_id`
  - explicit `memory_item_id` selection
- Kept the new retrieval layer read-only:
  - no compile mutation
  - no runtime mutation
  - no automatic memory injection
- Exposed the new baseline through:
  - `memory retrieve-preview`
  - `GET /memory/retrieval-preview`
- Extended offline validation so both CLI and API acceptance now prove:
  - persistent materialization
  - retrieval preview
  - explicit item-id selection

Verification:

- `pytest tests/test_contracts.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - `171 passed`
- `pytest -q`
  - `193 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

Result:

- Phase gate passed.
- The repository now has the first explicit retrieval-preview bridge over stored memory items, while still keeping compile/resume semantics unchanged by default.

---

## 7. Next Reassessment

- The next `Memory` slice should decide whether to:
  - stop at preview/selection and keep memory purely operator-facing
  - or add one explicit compile-time memory bridge
- To stay aligned with the original roadmap note about `retrieval brief` injection while keeping risk low, the next phase should favor an **explicit compile-time memory brief injection baseline** that is opt-in and not automatically enabled.
