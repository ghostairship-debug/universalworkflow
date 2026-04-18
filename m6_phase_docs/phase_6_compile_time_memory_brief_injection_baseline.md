# M6 Phase 6 - Compile-Time Memory Brief Injection Baseline

**Phase status:** Completed  
**Phase position:** This phase starts after `M6 Phase 5` proves that stored memory items can produce a deterministic retrieval preview. It is the first explicit bridge from the `Memory` line back into compile context.

**Entry condition:** Retrieval preview and manual item selection now exist, but compile/recompile still ignore selected memory items and no `TaskPacket` carries a memory brief.

---

## 1. Reassessment

Current implementation status:

- stored `memory_items` exist
- retrieval preview exists
- explicit item selection exists
- compile/recompile still do not accept memory input

Decision:

- add one explicit compile-time memory brief bridge
- keep the bridge opt-in
- do not auto-select memory items
- do not inject memory automatically at resume time

---

## 2. In Scope

- allow compile/recompile to accept explicit `memory_item_id` selection
- inject the resulting retrieval brief into compile context and `TaskPacket`
- expose the injected selection/brief through operator surfaces

---

## 3. Out Of Scope

- automatic memory selection
- automatic memory injection into every compile
- ranking or vector retrieval
- runtime-time mutation of the memory brief

---

## 4. Target Baseline

- compile can optionally carry a bounded memory brief
- the selected memory items are visible in task packet / status-detail / snapshots
- the default compile path remains unchanged when no memory items are supplied

---

## 5. Phase Task Breakdown Principle

This phase is expected to split into:

1. Compile-time memory-brief injection and projection
2. CLI/API compile controls for explicit memory selection
3. Docs/validation/closeout

---

## 6. Outcome

- Added the first explicit compile-time memory bridge.
- `compile` / `recompile` can now accept explicit `memory_item_id` selection.
- The resulting retrieval brief is now carried through:
  - compile response
  - `TaskPacket.env`
  - runtime-state compile context
  - status-detail / inspection
  - compile snapshots
  - generated artifact content
- Kept the bridge opt-in:
  - compile without memory items behaves exactly as before
  - no automatic selection or injection was added

Verification:

- `pytest tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - `155 passed`
- `pytest -q`
  - `196 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

Result:

- Phase gate passed.
- The repository now has a real, explicit `retrieval brief -> TaskPacket` bridge while still avoiding automatic memory injection semantics.

---

## 7. Next Reassessment

- With `Domain Pack` and `Memory` now both past their first platform/baseline bridges, the next major line should evaluate whether to:
  - keep deepening `Memory`
  - or start the planned `Simulation` baseline
- To keep following the second-cycle roadmap instead of over-deepening one line, the next phase should favor a **Simulation baseline reassessment**.
