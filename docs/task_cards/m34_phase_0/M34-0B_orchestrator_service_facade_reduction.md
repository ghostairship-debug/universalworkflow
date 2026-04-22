# M34-0B OrchestratorService Facade Reduction

Status: completed

## Goal

Continue shrinking the cross-plane helper concentration inside `OrchestratorService` so the public facade stays stable while the internal seam map becomes more honest.

## Acceptance

- extract another bounded helper/delegate slice from `OrchestratorService`
- preserve the current public lifecycle, interaction, governance, and orchestration entry surfaces
- avoid public-surface breakage or speculative broad rewrites
- update tests and closeout evidence for the new seam split

## Notes

- keep the facade stable; this card is about internal concentration reduction, not public API redesign
- if a seam extraction exposes a real runtime regression, repair it before widening the refactor

## Result

- added [packages/core_domain/service_scheduler_authority_support.py](../../../packages/core_domain/service_scheduler_authority_support.py) as a bounded support/delegate service for scheduler-authority state shaping and arbitration payload assembly
- moved scheduler-authority payload extraction, cluster-summary projection, dispatch context shaping, and arbitration update assembly behind that delegate
- kept current CLI, API, operator-surface, and governance behavior stable by leaving the existing `OrchestratorService` methods as facade wrappers
- validated the seam extraction with targeted scheduler/governance/API/CLI regression coverage
