# M41-0A：强模型 Dogfood 合同冻结

## 写入范围

- `packages/core_domain/config.py`
- `packages/core_domain/execution_profiles.py`
- `packages/contracts/models.py`
- `packages/core_domain/compile.py`

## 验收

- 新增 dogfood 配置项。
- `ResolvedExecutionProfile` additive 增加模型选择来源字段。
- `WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED=1` 时核心 agent 解析到 `gpt-5.5 / xhigh`。
