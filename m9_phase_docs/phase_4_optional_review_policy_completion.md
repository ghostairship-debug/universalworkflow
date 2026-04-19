# M9 Phase 4 - Optional Review Policy Completion

**Phase status:** Complete  
**Phase position:** This phase closes the remaining review-policy debt by turning `optional` from reference-only into a real run-level runtime policy.

## Scope

- implement `optional` as an executable review policy with a clean advisory-only terminal shape
- update seed presets, review-policy governance surfaces, release-readiness logic, CLI/API tests, and operator state language
- preserve backward-compatible semantics for the existing four policies

## Out Of Scope

- further review-policy families beyond `optional`
- distributed ownership or concurrency work
- broader milestone replanning beyond the review-policy gap

## Phase Gate

This phase passes only if:

- `optional` is executable end to end
- operator-facing effective states remain clear and backward compatible for existing policies
- governance and readiness reports no longer describe `optional` as reference-only

## Next Reassessment

Next approved phase: `M9 Phase 5 - Freeze Review And Scope Closure`
