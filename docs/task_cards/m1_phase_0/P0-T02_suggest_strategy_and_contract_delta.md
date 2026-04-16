# P0-T02 — Suggest Strategy And Contract Delta

## Basic Info

- Task ID: `P0-T02`
- Phase: `M1 Phase 0`
- Status: `verified`
- Depends On: `P0-T01`

## Goal

冻结 `PresetResolver.suggest(goal_text)` 的实现策略、输出结构和排序规则。

## Non-goals

- 不引入 LLM 或语义检索
- 不在本卡中实现完整 suggestion 代码

## Read Set

- `packages/core_domain/resolver.py`
- `infra/seeds/presets.json`
- `tests/test_contracts.py`
- `M1_Evaluation_and_Suggestions.md`
- `M0_Evaluation_Claude_Opus.md`

## Write Set

- `m1_phase_docs/phase_0_rebaseline_and_scope_freeze.md`
- 本文件
- 后续 Phase 2 的 resolver / CLI / tests

## Interface / Data Changes

- 新增 `PresetResolver.suggest(goal_text)`
- 建议新增非持久化 contract：
  - `PresetSuggestion`
    - `preset_id`
    - `score`
    - `reason`
- CLI 新增 `workflowctl run suggest-presets --goal ...`

## Invariants

- suggestion 只做推荐，不做自动选择
- 同样输入必须得到同样输出
- 弱匹配时仍需返回稳定结果和明确 reason

## Implementation Steps

1. 选择“静态规则 + 关键词启发式匹配”作为 M1 唯一策略。
2. 为 `feature_delivery`、`research_spike` 定义第一版关键词权重。
3. 规定排序规则：先按分数降序，再按 `preset_id` 升序。
4. 规定输出必须带 `reason`。
5. 在 Phase 2 中落实为 resolver、CLI、tests。

## Test Plan

- 空 goal 时返回稳定 fallback 排序
- 明显 feature goal 时 `feature_delivery` 排第一
- 明显 research goal 时 `research_spike` 排第一
- 多次调用结果顺序一致

## Risks / Rollback

- 风险：把 suggestion 做成“智能推荐”期待
- 回退：明确在文档和 ADR 中标注“deterministic heuristic only”

## Completion Evidence

- phase 文档中已有策略冻结
- Phase 2 将按本卡直接实现 suggestion 和对应测试
