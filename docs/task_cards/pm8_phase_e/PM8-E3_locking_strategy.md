# PM8-E3 - Locking Strategy

## Objective

Record the repository's dependency locking/versioning strategy so maintenance and security updates have an explicit policy before `M8`.

## Required Outcomes

- strategy doc exists
- rationale references current dependency bounds and upgrade posture
- living docs point to the policy when relevant

## Result

- added `docs/dependency_locking_policy.md`
- widened the repository's core runtime bounds selectively instead of leaving them artificially tight
- updated living docs so future milestone entry work can treat dependency changes as policy-driven and test-gated rather than ad hoc
