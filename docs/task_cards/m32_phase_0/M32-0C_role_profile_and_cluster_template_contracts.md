# M32-0C Role / Profile / Cluster Template Contracts

Status: completed

## Goal

Establish the two-layer execution model of stable public roles plus profiles, then add first-class execution-cluster templates on top.

## Acceptance

- keep public governance roles stable: `planner`, `coder`, `researcher`, `reviewer`, `operator`
- add `AgentProfileDefinition`
- add `GeneratedAgentProfile`
- add `AgentProfileRegistry`
- express specialists such as `architect`, `verifier`, and `citation_checker` as profiles instead of new public roles
- add `ExecutionClusterTemplate`
- add `ClusterExecutionPlan`
- add `ClusterOutputPacket`
- add `ClusterReviewRubric`
- add cluster routing support
- define first templates: `DevCluster` and `ResearchCluster`

## Result

- kept public governance roles stable
- added profile contracts, generated-profile support, and registry surfaces
- added first-class execution-cluster template contracts and routing helpers
- defined `DevCluster` and `ResearchCluster` as the first platform templates
- preserved the rule that specialist execution semantics live in profiles/templates rather than a large public role enum
