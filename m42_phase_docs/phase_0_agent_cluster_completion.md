# M42 Phase 0：Agent / Cluster 补全与收口记录

日期：2026-04-25

## 目标

M42 的目标是把 M41 已跑通的 `architecture_delivery_cluster` 经验推广为更完整的个人自用 agent / cluster 能力层。当前优先级不是公开产品化，而是让本地 workflow 面对不同任务形态时有更清晰的角色分工、路由依据、fallback 证据和 E2E 验收。

## 范围

- 新增或补齐搜索、设计、多模态、review、管理五类常驻集群。
- 保留 `dev_cluster`、`research_cluster`、`architecture_delivery_cluster` 的既有语义。
- 强 dogfood + `codex_cli` 后端下，新集群的核心 `agent` 角色默认解析到 Codex CLI `gpt-5.5 / xhigh`。
- MMX/Vertex/Claude 仍按 M41 规则视为外部 artifact-only 能力，失败必须可 fallback，不允许静默成功。

## 已实现集群

| Cluster | 角色链路 | 当前用途 |
| --- | --- | --- |
| `search_cluster` | `search_scout -> source_synthesizer -> citation_checker -> launch_guard` | 搜索、来源追踪、研究摘要和引用核验 |
| `design_cluster` | `product_designer -> visual_interaction_designer -> design_critic -> launch_guard` | 产品方向、交互/视觉方案和设计审查 |
| `multimodal_cluster` | `multimodal_evidence -> multimodal_synthesizer -> citation_checker -> launch_guard` | PDF、图片、截图、设计稿 evidence 入口 |
| `review_cluster` | `quality_gate + test_sentinel + governance_sentinel -> doc_curator -> launch_guard` | 质量、测试、治理和中文文档收口 |
| `management_cluster` | `roadmap_manager -> phase_designer -> governance_sentinel -> doc_curator -> launch_guard` | roadmap、phase/task 和 closeout 管理 |

## 实现结果

- `packages/core_domain/interaction_catalog.py`：新增 agent profiles、cluster templates、member sequence、preset mapping。
- `packages/core_domain/cluster_router.py`：新增中文/英文 marker 路由，保留 architecture/dogfood 最高优先级。
- `packages/core_domain/execution_profiles.py`：把 `dogfood_strong_codex_cli` 覆盖范围扩展到 M42 专用集群。
- `packages/worker_adapters/codex_adapter.py` 与 `packages/worker_adapters/subprocess_support.py`：为真实 Codex CLI 加入进程树 timeout 清理，避免 Windows node/native 子进程残留。
- `tests/test_m42_clusters.py`：覆盖 catalog、router、强 dogfood 路由、MMX 外部角色保留和 management preview。

## E2E 记录

- 长 timeout smoke：`state/m42_management_cluster_smoke/summary.json`
- 进程树 timeout 修复后 smoke：`state/m42_management_cluster_tree_timeout_smoke/summary.json`
- 收口 run：`run_665006c2016d`
- 结论：`management_cluster` 根 run completed；Codex 子 run 在约 8 秒硬超时后被标记 failed，再由 shell fallback 完成；复查无残留 `codex.exe`。

## 验证

已通过：

```powershell
python -m pytest -q tests/test_m42_clusters.py tests/test_m41_capabilities.py::test_codex_adapter_timeout_can_be_overridden_for_local_dogfood tests/test_m41_capabilities.py::test_codex_adapter_timeout_can_be_overridden_per_packet tests/test_m41_capabilities.py::test_dogfood_codex_backend_routes_architecture_agent_roles_to_codex --no-cov
python -m pytest -q tests/test_m42_clusters.py tests/test_m41_capabilities.py::test_subprocess_tree_timeout_returns_124_for_hung_cli tests/test_m41_capabilities.py::test_codex_adapter_timeout_can_be_overridden_per_packet tests/test_m41_capabilities.py::test_codex_command_places_exec_options_before_prompt --no-cov
python -m pytest -q tests/test_m42_clusters.py tests/test_m41_capabilities.py tests/test_execution_loop.py::test_project_delivery_runs_multi_role_orchestration tests/test_execution_loop.py::test_guarded_project_delivery_uses_shared_graph_substrate tests/test_execution_loop.py::test_resume_run_converts_worker_adapter_exception_to_failed_evidence --no-cov
python -m pytest -q tests/test_contracts.py::test_m32_interaction_and_cluster_contracts_round_trip --no-cov
```

M42 最终收口已通过：

```powershell
python -m infra.scripts.check_doc_links
# passed, checked_doc_count=6

python -m infra.scripts.offline_validation --skip-offline-probe
# overall_passed=true

python -m pytest -q
# 227 passed, 134 skipped

python -m pytest -q --run-slow
# 361 passed
```

## 后续建议

M43 优先用真实 PDF/截图跑 `multimodal_cluster`，再用低频 Claude gate 验证 architecture handoff；同时继续收缩 `OrchestratorService` 和 Codex artifact-only role prompt。
