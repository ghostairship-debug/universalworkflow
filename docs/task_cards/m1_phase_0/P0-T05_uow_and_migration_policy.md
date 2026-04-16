# P0-T05 — UoW And Migration Policy

## Basic Info

- Task ID: `P0-T05`
- Phase: `M1 Phase 0`
- Status: `verified`
- Depends On: `P0-T01`

## Goal

冻结 M1 的 Unit of Work 粒度、repository 连接注入策略以及 M1 期间的破坏性迁移政策。

## Non-goals

- 不在本卡中实现完整事务代码
- 不承诺兼容 M0 全部历史临时 DB 样本

## Read Set

- `packages/core_domain/db.py`
- `packages/core_domain/repositories.py`
- `packages/core_domain/services.py`
- `infra/scripts/manage.py`
- `infra/scripts/offline_validation.py`
- `tests/test_repositories.py`

## Write Set

- `m1_phase_docs/phase_0_rebaseline_and_scope_freeze.md`
- 本文件
- 后续 Phase 1 / 3 的 db、repositories、manage、offline_validation、tests

## Interface / Data Changes

- `db.unit_of_work()` 风格 context manager
- repository 写方法允许注入外部 connection
- service method 成为事务边界
- M1 开发期间允许 `db reset` 式破坏性清理

## Invariants

- 事务边界不跨 service 方法
- 一个 UoW 内的多步写入必须原子提交或整体回滚
- migration 需要 fresh reset 场景稳定通过

## Implementation Steps

1. 在 `db.py` 中增加 UoW 入口。
2. 在 repositories 中支持 connection 注入，避免 service 内多步写入多次独立建连。
3. 在 `compile_run()`、`resume_run()`、`approve_run_review()`、`reject_run_review()`、`cancel_run()` 中使用 UoW。
4. 更新 `manage.py`、offline validation 和 README，使其明确 M1 默认允许破坏性 reset。

## Test Plan

- repository 写入在注入 connection 时可正常工作
- service 多步写入失败时回滚
- `db reset -> migrate -> seed -> smoke` 通过

## Risks / Rollback

- 风险：先引入事务，再忘记调整 repositories，导致一半走 UoW 一半走独立建连
- 回退：若 UoW 引入不完整，不继续扩 API，先补齐 repository 注入能力

## Completion Evidence

- phase 文档中已冻结 service-method 级 UoW
- Phase 1 / 3 可以直接据此修改 db 和 repositories
