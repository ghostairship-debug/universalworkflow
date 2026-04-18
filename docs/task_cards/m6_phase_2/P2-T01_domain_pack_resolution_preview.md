# P2-T01 - Domain Pack Resolution Preview

## Objective

Expose the resolved pack and chosen adapter for a preset/task-kind pair before compile is invoked.

## Scope

- add a read-only preview surface in the service layer
- reuse `DomainPackResolution` rather than inventing a new shape

## Verification

- service tests
- CLI/API preview tests
