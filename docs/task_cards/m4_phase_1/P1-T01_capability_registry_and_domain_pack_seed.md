# P1-T01 - Capability Registry And Domain Pack Seed

## Goal

Turn hardcoded adapter routing into an explicit `CapabilityRegistry`, add a minimal `DomainPackDefinition`, and make compile output visibly depend on the selected domain pack.

## Scope

- add `CapabilityRoute` and `DomainPackDefinition`
- add `infra/seeds/domain_packs.json`
- add `DomainPackRegistry`
- update `WorkerRouter` to delegate to `CapabilityRegistry`
- inject domain-pack and adapter proof into compile output

## Guardrails

- do not add new persistence tables
- do not add multi-pack conflict resolution
- do not introduce dynamic plugin loading

## Verification

- contract parsing tests
- execution-loop tests for capability routes and domain-pack artifact proof

## Exit Signal

- registry-backed adapter resolution exists
- one enabled domain pack is loadable and compile-visible
