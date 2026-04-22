# M32-0D Cluster-Aware Runtime And Packets

Status: completed

## Goal

Extend the existing graph and packet families so cluster-aware execution becomes part of the current runtime truth instead of a parallel special path.

## Acceptance

- graph nodes support `agent_profile_id`
- graph nodes support `cluster_template_id`
- graph nodes support `role_label`
- goal packets expose cluster selection and cluster graph preview
- operator packets expose cluster progress, packets, and handoffs
- replay packets expose cluster execution lineage
- execution routing can run `DevCluster` without introducing a new `*_delivery` service special path
- existing `feature_delivery`, `project_delivery`, and `guarded_project_delivery` compatibility remains intact

## Result

- graph nodes now project `agent_profile_id`, `cluster_template_id`, and `role_label`
- goal/operator/replay packet families now carry cluster-aware fields
- parent/child lineage remains the single execution truth chain
- `DevCluster` runs through the shared runtime/packet path without introducing a second orchestration family
- compatibility for `feature_delivery`, `project_delivery`, and `guarded_project_delivery` remained intact
