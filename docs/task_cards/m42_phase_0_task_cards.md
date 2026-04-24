# M42 Phase 0 任务卡索引

| ID | 状态 | 摘要 |
| --- | --- | --- |
| M42-0A | done | 冻结 M42 agent / cluster 补全范围、优先级和验收标准 |
| M42-1A | done | 实现搜索、设计、多模态、review、管理集群 catalog |
| M42-2A | done | 扩展强 dogfood Codex CLI 路由到 M42 专用集群 |
| M42-3A | done | 补 router / projection / E2E 定点测试 |
| M42-4A | done | 跑真实 workflow dogfood smoke 并记录 fallback 结果 |
| M42-5A | done | 更新中文文档、最终验证、commit、push |

## 当前边界

- 不引入公开 SaaS、多用户权限或安装器。
- 不自动创建 GitHub PR。
- 真实外部能力失败时优先 fallback，并记录 degraded 原因。
- 完整慢测试只在 M42 收口时运行一次。

## 当前证据

- `tests/test_m42_clusters.py` 覆盖 M42 cluster catalog、router 和强 dogfood 解析。
- `state/m42_management_cluster_tree_timeout_smoke/summary.json` 记录真实 `management_cluster` tree-timeout smoke。
- 收口 run：`run_665006c2016d`。
- 最终验证：`check_doc_links`、`offline_validation --skip-offline-probe`、`pytest -q`、`pytest -q --run-slow` 全部通过。
