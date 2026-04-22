# M33-0C OrchestratorService Seam Extraction

Status: pending

## Goal

Continue shrinking the cross-plane helper concentration inside `OrchestratorService` without breaking the public surface or weakening the current composition root.

## Acceptance

- extract another bounded helper/delegate slice from `OrchestratorService`
- make the service-boundary story more honest than the accepted `M32` baseline
- preserve the current public lifecycle, governance, and orchestration entry surfaces
- update any seam/audit references needed to reflect the new split

## Notes

- this card depends on the `M33-0B` contraction direction being clear enough to avoid extracting the wrong abstraction first
