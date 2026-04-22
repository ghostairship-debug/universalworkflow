# M34-0C Scheduler-Authority Interior Cleanup

Status: active

## Goal

Continue the scheduler-authority semantic honesty line behind the already-correct public wording by reducing legacy interior naming where it still overstates the actual guarantee.

## Acceptance

- identify the remaining storage/event/diagnostic names that still retain legacy consensus-era wording
- rename, wrap, or alias those semantics where safe without breaking external compatibility
- preserve the accepted public honesty baseline for `/healthz`, cluster/operator surfaces, CLI, and API
- update tests and governance/readiness evidence where naming or wording changes

## Notes

- this card is semantic honesty cleanup, not a claim that the runtime has become a stronger distributed system
- prefer additive compatibility and bounded interior cleanup over risky migrations unless a migration becomes necessary and safe
