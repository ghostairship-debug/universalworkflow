# M41-8B：LangChain Provider Factory

## 目标

把 LangChain lane 从 OpenAI-only 改为可选控制层，默认优先 MiniMax，DeepSeek V4 Flash 作为 fallback，OpenAI 作为兼容项。

## 实现结果

- 新增 `WORKFLOW_LANGCHAIN_AGENT_PROVIDER`、`WORKFLOW_LANGCHAIN_AGENT_MODEL`、`WORKFLOW_LANGCHAIN_AGENT_BASE_URL`。
- `auto` provider 顺序为 MiniMax、DeepSeek、OpenAI。
- 缺少所有 provider key 时返回明确 `WorkerAdapterUnavailableError`，不影响 OrchestratorService 启动。
- LangChain lane 的 provider/model/fallback 信息进入 adapter metadata 和 doctor。

## 验证

- `python -m pytest -q tests/test_m41_capabilities.py tests/test_doctor.py --no-cov`
