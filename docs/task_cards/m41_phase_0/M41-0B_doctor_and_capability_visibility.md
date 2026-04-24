# M41-0B：Doctor 与能力可见性

## 写入范围

- `apps/operator_cli/main.py`
- `packages/core_domain/capability_plane.py`
- `tests/test_doctor.py`

## 验收

- `workflowctl doctor` 显示 `codex/opencode/claude/mmx/gcloud`。
- Claude 显示 `quota_guarded` 或 disabled/missing。
- MMX/Vertex 显示 ready、missing auth 或 missing CLI。
- 所有 secret 只显示 present/redacted，不输出真实值。
