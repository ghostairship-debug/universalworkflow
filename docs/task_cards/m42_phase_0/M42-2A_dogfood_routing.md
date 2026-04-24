# M42-2A：强 Dogfood 路由扩展

## 写入范围

- `packages/core_domain/execution_profiles.py`
- `packages/worker_adapters/codex_adapter.py`
- `packages/worker_adapters/subprocess_support.py`
- `tests/test_m42_clusters.py`
- `tests/test_m41_capabilities.py`

## 目标

在 `WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED=1` 且 `WORKFLOW_DOGFOOD_EXECUTION_BACKEND=codex_cli` 时，M42 专用集群里的核心 `agent` 角色解析为 Codex CLI。

## 结果

- `search_cluster`、`design_cluster`、`multimodal_cluster`、`review_cluster`、`management_cluster` 的核心 agent roles 均进入 `dogfood_strong_codex_cli`。
- `mmx_multimodal`、`vertex_multimodal`、`claude_architect` 仍保持外部 artifact-only adapter，不被强制改为 Codex。
- Codex CLI 真实执行新增进程树 timeout 清理，避免 Windows 上 node/native 子进程残留。

## 验收

- `tests/test_m42_clusters.py::test_m42_strong_codex_backend_routes_core_cluster_roles_to_codex`
- `tests/test_m42_clusters.py::test_m42_external_multimodal_member_keeps_mmx_adapter`
- `tests/test_m41_capabilities.py::test_subprocess_tree_timeout_returns_124_for_hung_cli`
