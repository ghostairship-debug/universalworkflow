# M42-1A：集群目录补全

## 写入范围

- `packages/core_domain/interaction_catalog.py`
- `packages/core_domain/cluster_router.py`
- `tests/test_m42_clusters.py`

## 目标

新增 `search_cluster`、`design_cluster`、`multimodal_cluster`、`review_cluster`、`management_cluster`，并确保它们能被 CLI/API/profile projection 读取。

## 结果

- 已新增五类 cluster template。
- 已新增对应 agent profile 和 role_label。
- 已补齐 member order、preset mapping、review rubric。
- 已扩展 router 的中文/英文关键词。

## 验收

- `tests/test_m42_clusters.py::test_m42_cluster_catalog_contains_priority_clusters`
- `tests/test_m42_clusters.py::test_m42_router_suggests_specialized_clusters`
