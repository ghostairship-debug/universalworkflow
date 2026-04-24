# M41 Phase 8：Codex CLI 强 Dogfood 后端

## 背景

Phase 6 的受控 dogfood 暴露出一个真实阻塞点：强模型 agent lane 仍硬依赖 `OPENAI_API_KEY`。这不符合当前个人自用环境，因为本机已经有 Codex CLI 登录态，且 MiniMax/DeepSeek 更适合承担轻量控制层。

## 决策

- M41 dogfood 默认执行后端改为 `WORKFLOW_DOGFOOD_EXECUTION_BACKEND=codex_cli`。
- `architecture_delivery_cluster` 中原本使用 `agent` 的核心规划、评审和文档角色，在强 dogfood + `codex_cli` 后端下解析为 `codex` artifact-only 执行。
- `WORKFLOW_DOGFOOD_EXECUTION_BACKEND=agent_lane` 仍保留 LangChain lane，但它不再是默认 dogfood 主路径。
- LangChain 主 LLM 改为 OpenAI-compatible provider factory：`auto` 顺序为 MiniMax、DeepSeek、OpenAI。
- 真正 repo mutation 仍只交给 patch-capable worker，且继续受 task card/write scope/test command 约束。

## 合同

- 新增环境变量：`WORKFLOW_DOGFOOD_EXECUTION_BACKEND=codex_cli|agent_lane`，默认 `codex_cli`。
- 新增环境变量：`WORKFLOW_DOGFOOD_CODEX_MODEL`，用于给 Codex CLI 后端单独指定模型；为空时使用 `WORKFLOW_DOGFOOD_MODEL`，当前默认是 `gpt-5.5`。
- 新增环境变量：`WORKFLOW_LANGCHAIN_AGENT_PROVIDER=auto|minimax|deepseek|openai`，默认 `auto`。
- 新增环境变量：`WORKFLOW_LANGCHAIN_AGENT_MODEL`、`WORKFLOW_LANGCHAIN_AGENT_BASE_URL`。
- 新增投影字段：`dogfood_execution_backend`、`langchain_agent_provider`、`langchain_agent_model`、`langchain_agent_degraded_reason`。
- 新增模型选择来源：`dogfood_strong_codex_cli`。

## 当前结果

- `workflowctl doctor` 可以区分 dogfood 后端、Codex CLI readiness 和 LangChain provider readiness。
- 无 `OPENAI_API_KEY` 时，默认 dogfood 后端不再失败在 LangChain 初始化。
- Codex artifact-only prompt 已包含 goal、role、responsibilities 和 handoff context，用于生成真实 planner/reviewer/doc artifact。
- 2026-04-25 本机验证：升级 npm `@openai/codex` 从 `0.121.0` 到 `0.125.0` 后，`codex exec --model gpt-5.5` 已可用；当前 dogfood CLI 路径恢复为 `gpt-5.5 xhigh`。
- 2026-04-25 修复：`CodexAdapter` 的 `codex exec` 选项必须位于 prompt 之前，真实运行改为 `codex exec ... -` 并通过 UTF-8 stdin 投喂 prompt，避免 Windows 管道污染、参数失效和 GBK 解码失败。
- 真实 smoke：`state/m41_dogfood_smoke/planner_design.md` 已由 Codex CLI artifact-only 路径生成，证明无 `OPENAI_API_KEY` 时可以完成 planner artifact dogfood。
- 升级后 smoke：`state/m41_dogfood_smoke/planner_design_gpt55.md` 已由 `CodexAdapter.launch()` 使用 `gpt-5.5 xhigh` 生成，证明 workflow adapter 路径也能调用 5.5。
