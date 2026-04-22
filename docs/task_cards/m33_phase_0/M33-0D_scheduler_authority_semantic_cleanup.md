# M33-0D Scheduler-Authority Semantic Cleanup

Status: pending

## Goal

Clean up remaining legacy scheduler-authority wording and internal semantics where they still imply a stronger distributed-consensus guarantee than the repository actually provides.

## Acceptance

- identify the remaining internal table/event/diagnostic names that still overstate the guarantee
- rename or wrap those semantics where safe without breaking current external compatibility
- preserve the accepted public honesty baseline for `/healthz`, `/authority/cluster`, CLI, API, and operator surfaces
- update tests and governance/readiness evidence where wording or semantics change

## Notes

- this is semantic honesty cleanup, not a claim that the runtime has become a different class of distributed system
