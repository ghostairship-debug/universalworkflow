# Phase 4 Task Cards

## Reassessment

- API, repositories, and compile shape are stable enough to support a real execution loop.
- The remaining evaluator guidance for this phase is already fixed:
  out-of-band changes are recorded in `Evidence.known_gaps` and do not block review.
- The control loop can now remain narrow:
  one packet, one shell execution, one evidence record, one verdict.

## Card P4-01: Implement `ShellAdapter`

- Goal:
  Execute the prepared `TaskPacket` and return a stable structured result.
- Done when:
  Success and failure cases both expose `return_code`, `stdout`, `stderr`, timing, and artifact paths.

## Card P4-02: Implement `EvidenceBuilder`

- Goal:
  Convert execution results into machine-readable evidence and compute artifact integrity fields.
- Done when:
  `artifact_refs` always include `path`, `sha256`, `mtime`, and `size_bytes`.

## Card P4-03: Implement `AutoReview v0`

- Goal:
  Produce a deterministic pass/fail verdict from evidence.
- Done when:
  Success and failure commands create review verdicts and write review events.

## Card P4-04: Wire execution into the orchestrator service

- Goal:
  Add an internal `execute_run` flow that updates task state, evidence, review, and terminal run status.
- Done when:
  Timeline contains execution, evidence, review, and terminal run events.

## Card P4-05: Add execution-loop tests

- Goal:
  Verify success, failure, and out-of-band detection paths.
- Done when:
  `pytest` covers the whole `TaskPacket -> ShellAdapter -> Evidence -> ReviewVerdict` chain.
