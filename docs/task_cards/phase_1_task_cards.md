# Phase 1 Task Cards

## Reassessment

- Phase 0 freezes the naming, roles, and ADR constraints needed for implementation.
- The latest Opus observations are adopted here:
  implement core-chain objects first, then support objects.
- Out-of-band change handling is fixed in ADR-002 as:
  append a warning to `Evidence.known_gaps`, do not block review.

## Card P1-01: Implement core-chain contracts

- Source refs:
  `m0_phase_docs/phase_1_contracts_and_preset_baseline.md`
  `docs/contracts/wave1-objects.md`
- Goal:
  Add Pydantic models for `Run`, `Phase`, `RuntimeTask`, `Evidence`, and `ReviewVerdict`.
- Done when:
  Models serialize, deserialize, and retain `schema_version`.

## Card P1-02: Implement support contracts

- Goal:
  Add `TaskCard`, `TaskPacket`, `PresetDefinition`, and `HandoffLite` plus shared enums and budget policy.
- Done when:
  Preset value domains are fixed and `HandoffLite` is schema-only for M0.

## Card P1-03: Add preset registry and seed data

- Goal:
  Create the preset registry doc and JSON seeds for `feature_delivery` and `research_spike`.
- Done when:
  Seed files parse into `PresetDefinition` and examples match the doc.

## Card P1-04: Implement `PresetResolver` manual-only path

- Goal:
  Reject missing presets, reject unknown presets, and never infer one from goal text.
- Done when:
  Resolver returns a `PresetDefinition` or raises an explicit domain error.

## Card P1-05: Lock contracts tests

- Goal:
  Add round-trip tests, seed parsing tests, and default `reviewer_type=auto` validation.
- Done when:
  Contracts and preset tests pass under `pytest`.
