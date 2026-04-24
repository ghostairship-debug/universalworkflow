# M41-8A：Codex CLI 强 Dogfood 后端

## 目标

让 M41 自开发 dogfood 默认使用本机 Codex CLI，而不是硬依赖 OpenAI API 形式的 LangChain agent lane。

## 实现结果

- 新增 `WORKFLOW_DOGFOOD_EXECUTION_BACKEND`，默认 `codex_cli`。
- 新增 `WORKFLOW_DOGFOOD_CODEX_MODEL`，用于适配本机 Codex CLI 可访问模型。
- `architecture_delivery_cluster` 中非显式选择的 `agent` 核心角色，在强 dogfood + `codex_cli` 后端下解析为 `codex`。
- 新增 `dogfood_strong_codex_cli` 模型选择来源。
- Codex artifact-only prompt 增加 role、responsibilities 和 handoff context。

## 验证

- `python -m pytest -q tests/test_m41_capabilities.py tests/test_doctor.py --no-cov`
