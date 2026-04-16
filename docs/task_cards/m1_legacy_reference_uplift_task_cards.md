# M1 遗产参考增强 Task Cards

## Reassessment

- 本批 uplift 只围绕 3 个低风险、高收益方向。
- 目标是 `M1 hardening`，不是重开 M1 架构。
- 一切遗产吸收必须保持 `run-centric` 主链，不得回流 `project / phase / task-card kernel`。

## Phase A：状态守卫硬化

- `LU-A1`
  Summary:
  冻结 `RunStatus / RuntimeStateRef` 的迁移矩阵与 terminal 规则。
  Type:
  `complex`
  Output:
  迁移矩阵说明、contracts 约束口径、测试边界。
  Doc Link:
  [LU-A1](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_legacy_reference_uplift/LU-A1_state_transition_matrix.md:1)

- `LU-A2`
  Summary:
  将迁移矩阵落实到 service guard、API 错误与表驱动测试。
  Type:
  `complex`
  Depends On:
  `LU-A1`
  Doc Link:
  [LU-A2](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_legacy_reference_uplift/LU-A2_guard_and_transition_tests.md:1)

## Phase B：Review Policy 测试矩阵

- `LU-B1`
  Summary:
  从遗产 review policy 测试提炼 case matrix，并映射到当前 `auto_only / human_required`。
  Type:
  `complex`
  Output:
  review case matrix 与语义边界说明。
  Doc Link:
  [LU-B1](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_legacy_reference_uplift/LU-B1_review_case_matrix.md:1)

- `LU-B2`
  Summary:
  增加 `latest_review_verdict / effective_review_state` 的查询与测试投影。
  Type:
  `complex`
  Depends On:
  `LU-B1`
  Doc Link:
  [LU-B2](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_legacy_reference_uplift/LU-B2_review_projection_and_tests.md:1)

## Phase C：Status Detail / Dry-Run Inspection

- `LU-C1`
  Summary:
  扩展 `status-detail` 的 operator diagnostics 字段与 CLI / API 展示。
  Type:
  `complex`
  Output:
  失败原因、等待原因、下一步建议、最后 review / runtime 摘要。
  Doc Link:
  [LU-C1](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_legacy_reference_uplift/LU-C1_status_detail_diagnostics.md:1)

- `LU-C2`
  Summary:
  新增 4 类坏状态的 dry-run inspection，不修改真实状态。
  Type:
  `complex`
  Depends On:
  `LU-C1`
  Doc Link:
  [LU-C2](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_legacy_reference_uplift/LU-C2_dry_run_inspection.md:1)
