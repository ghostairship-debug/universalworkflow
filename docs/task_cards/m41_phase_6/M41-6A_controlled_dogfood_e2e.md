# M41-6A：受控 Dogfood E2E

## 写入范围

- `apps/operator_cli/main.py`
- `packages/worker_adapters/langchain_agent_adapter.py`
- `tests/test_doctor.py`
- `m41_phase_docs/phase_6_dogfood_e2e_log.md`
- `docs/task_cards/m41_phase_6_task_cards.md`

## 执行内容

1. 打开 `WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED=1`。
2. 创建 `architecture_delivery_cluster` session。
3. 生成 cluster-scoped generated profiles。
4. 编译 architecture plan run。
5. 识别 agent lane 缺少 `OPENAI_API_KEY` 的真实失败点。
6. 改用 deterministic `feature_delivery` evidence run 完成 evidence/review/summary。
7. 把人工接管点写入 Phase 6 日志。

## 验收

- `state/m41_dogfood_e2e_result.json` 存在。
- evidence run 完成。
- doctor 能报告 `dogfood_strong_model=missing_auth`。
- Claude 未被调用。
- 没有执行 git commit/push/PR。
 
## Phase 8 后续修正

Phase 6 的失败点是当时真实存在的历史记录。Phase 8 已将默认强 dogfood 后端改为 Codex CLI；只有显式选择 `WORKFLOW_DOGFOOD_EXECUTION_BACKEND=agent_lane` 时才继续依赖 LangChain provider key。
