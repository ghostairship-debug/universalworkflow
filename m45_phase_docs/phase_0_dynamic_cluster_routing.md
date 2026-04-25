# M45 Phase 0：动态角色/集群编排

日期：2026-04-25

## 目标

M45 把单集群推荐升级为可选动态多集群组合。开启 `WORKFLOW_DYNAMIC_CLUSTER_ROUTING_ENABLED=1` 后，复杂目标可以同时进入多模态、搜索、设计、开发和 review lane。

## 默认组合顺序

1. `multimodal_cluster`
2. `search_cluster`
3. `design_cluster`
4. `architecture_delivery_cluster`
5. `dev_cluster`
6. `review_cluster`
7. `management_cluster`

泛 `research_cluster` 只在没有更专门集群命中时补位，避免过度编排。

## M45 修复点

真实 smoke 发现 `launch_goal` 会选中多个集群，但 status detail 的 `cluster_graph` 只显示第一个集群。已修复为 composite preview graph：`cluster_template_ids` 和 `cluster_graphs` 都包含全部动态命中集群。

## 验证

- `tests/test_m45_dynamic_cluster_routing.py`
- Smoke：`state/m46_dynamic_adaptive_smoke/summary.json`
