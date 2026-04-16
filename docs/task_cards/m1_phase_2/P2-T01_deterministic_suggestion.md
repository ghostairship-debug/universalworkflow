# P2-T01 — Deterministic Suggestion

## Basic Info

- Task ID: `P2-T01`
- Phase: `M1 Phase 2`
- Status: `verified`
- Depends On: `Phase 1 gate`

## Goal

实现离线、确定性、可解释的 `PresetResolver.suggest(goal_text)`。

## Read Set

- `packages/core_domain/resolver.py`
- `infra/seeds/presets.json`
- `tests/test_contracts.py`

## Write Set

- `packages/core_domain/resolver.py`
- `tests/test_contracts.py`

## Tests

- feature goal 排序
- research goal 排序
- fallback 排序稳定
- reason 存在

## Output

- heuristic suggestion engine
