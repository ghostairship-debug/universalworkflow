# M41-13A：Codex CLI Dogfood E2E

状态：已完成

## 目标

用 workflow 自己跑一次受控 M41 内部开发演练，确认 Phase 8 的 Codex CLI 后端修复能让强模型 dogfood 不再依赖 `OPENAI_API_KEY`。

## 写入范围

- `m41_phase_docs/phase_13_codex_cli_dogfood_e2e.md`
- `docs/task_cards/m41_phase_13_task_cards.md`
- `docs/task_cards/m41_phase_13/M41-13A_codex_cli_dogfood_e2e.md`
- 如发现阻塞 bug，再补充最小代码修复和对应测试。

## 执行步骤

1. 打开 `WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED=1`、`WORKFLOW_DOGFOOD_EXECUTION_BACKEND=codex_cli`。
2. 确认 Codex CLI 版本和 `gpt-5.5 xhigh` 可用。
3. 创建或预览 `architecture_delivery_cluster` session / run。
4. 检查 cluster member execution profile 是否解析到 Codex CLI。
5. 执行至少一个真实 artifact-only Codex CLI dogfood role。
6. 记录产物、模型选择、失败点、人工接管点和后续缺口。
7. 跑定点测试、doc links、offline validation。

## 验收

- Phase 13 记录中包含真实 run/session/artifact ID 或路径。
- 强 dogfood 默认不再失败在 LangChain/OpenAI 初始化。
- Codex CLI artifact-only 路径返回 `gpt-5.5`。
- 没有 git commit、push、PR。

## 实际结果

- 真实 E2E：`intent_session_557cecbe8fc4` / `run_c0cad7dc9f58`。
- 父 run：`completed`，`parent_return_code=0`。
- 真实 Codex artifact-only 成功角色：`planner_design`、`phase_designer`。
- fallback 成功角色：`multimodal_evidence`、`claude_architect_gate`、`implementer`、`quality_gate`、`doc_curator`。
- 代码修复覆盖：cluster preference 保留、adapter exception 转 evidence、cluster member 防递归、失败 child 不静默 approve、human-required 失败 child fallback 前关闭、Codex timeout 可配置。
- 定点验证：`tests/test_m41_capabilities.py` 与相关 execution loop 用例通过。
