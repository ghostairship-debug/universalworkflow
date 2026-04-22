# M33-0D Scheduler-Authority Semantic Cleanup

Status: completed

## Goal

Clean up remaining legacy scheduler-authority wording and internal semantics where they still imply a stronger distributed-consensus guarantee than the repository actually provides.

## Acceptance

- identify the remaining internal table/event/diagnostic names that still overstate the guarantee
- rename or wrap those semantics where safe without breaking current external compatibility
- preserve the accepted public honesty baseline for `/healthz`, `/authority/cluster`, CLI, API, and operator surfaces
- update tests and governance/readiness evidence where wording or semantics change

## Notes

- this is semantic honesty cleanup, not a claim that the runtime has become a different class of distributed system

## Result

- added additive authority-facing aliases to scheduler-authority payloads:
  - `authority_node_id`
  - `authority_term_no`
  - `decision_index`
- updated operator-facing HTML wording from legacy `Leader / Term / Commit Index / Cluster Topology` labels to more honest `Authority Node / Authority Term / Decision Index / Authority Topology`
- preserved compatibility for existing `leader_node_id`, `term_no`, and `commit_index` consumers without opening a storage migration or breaking API/CLI contracts
