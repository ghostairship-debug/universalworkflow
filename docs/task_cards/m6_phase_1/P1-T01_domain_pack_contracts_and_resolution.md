# P1-T01 - Domain Pack Contracts And Resolution

## Objective

Replace the current proof-style flat domain-pack shape with reusable contracts for match rules, capability exposure, compile projection, runtime projection, and resolved pack snapshots.

## Scope

- add contract models for the platformized pack sections
- update `DomainPackDefinition` and the seed schema
- teach `DomainPackRegistry` to emit a stable `DomainPackResolution`

## Non-Goals

- multiple pack families
- plugin loading
- runtime mutation or persistence for pack state

## Verification

- contract round-trip tests
- seed parsing tests
- resolution tests that prove the current pack can still match `feature_delivery`-style runs

## Done When

- the current pack is represented through platform-shaped sections
- `DomainPackRegistry` can resolve a stable snapshot for compile/runtime use
