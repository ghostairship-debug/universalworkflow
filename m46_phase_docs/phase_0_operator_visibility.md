# M46 Phase 0：Operator 可见性

日期：2026-04-25

## 目标

M46 不做大规模 UI 改版，而是把 M44/M45 的关键决策投影到 operator 可见面：doctor、run detail、status detail 和 workbench 可复用的 payload。

## 已完成

- `ResolvedExecutionProfile` 新增 `adaptive_llm_routing_enabled`、`adaptive_route_tier`、`adaptive_route_reason`。
- task packet env 新增 `WORKFLOW_ADAPTIVE_*` 路由投影，status detail 可回放。
- `workflowctl doctor` 新增 `adaptive_llm_routing` 与 `dynamic_cluster_routing`。
- 动态集群 composite graph 会显示全部 selected cluster，而不是只显示第一个。

## 验证

- `tests/test_m44_adaptive_routing.py`
- `tests/test_m45_dynamic_cluster_routing.py`
