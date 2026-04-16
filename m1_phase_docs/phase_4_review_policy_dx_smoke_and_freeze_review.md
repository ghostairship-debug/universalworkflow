# M1 Phase 4 — Review Policy, DX, Smoke And Freeze Review

**阶段定位：** 收口 M1 的最后一段，把 `human_required` 从冻结语义变成真实闭环，并完成 M1 的文档、smoke、offline validation 与 freeze review。  
**进入条件：** Phase 3 gate 已通过。

---

# 1. 本阶段重评

当前实际状态：

- `auto_only` 已可从 compile -> resume -> review -> completed 跑通
- compile / resume / handoff / status-detail 都已成立
- `human_required` 还未真正进入流程
- 现有 smoke / offline validation 仍然是 M0 / M1 前半段口径

因此，Phase 4 只做最终收口：

- `human_required` 真正走通
- approve / reject API / CLI
- M1 smoke
- offline validation 升级
- README / freeze review 更新

---

# 2. In Scope

- `resume_run()` 分叉 `auto_only` / `human_required`
- `review_requested` 事件落地
- `approve_run_review()` / `reject_run_review()`
- API：
  - `POST /runs/{run_id}/approve`
  - `POST /runs/{run_id}/reject`
- CLI：
  - `workflowctl run approve <run_id>`
  - `workflowctl run reject <run_id>`
- `infra/scripts/manage.py smoke` 升级为 M1 smoke
- `infra/scripts/offline_validation.py` 升级为 M1 验收
- `README.md`
- `docs/reviews/m1-freeze-review.md`

---

# 3. Out Of Scope

- review timeout / SLA
- reviewer assignment
- Web review UI
- 第二执行器
- M2 并发控制

---

# 4. 关键实现约束

- `human_required` 路径不走 auto review
- `resume` 后若 preset 为 `human_required`，run 必须进入 `awaiting_review`
- approve / reject 必须各自产生 human `ReviewVerdict`
- `awaiting_review` 默认无限挂起
- M1 smoke 与 offline validation 必须继续支持断网、无 LLM key

---

# 5. Task 拆解原则

本阶段拆为 4 张复杂卡：

1. human review service 分叉
2. approve / reject API / CLI
3. smoke / offline validation / README
4. freeze review 与全量验证

---

# 6. Phase Gate

- `feature_delivery` auto path 通过
- `research_spike` human path 通过
- smoke 与 offline validation 通过
- README 已更新到 M1
- `docs/reviews/m1-freeze-review.md` 给出明确 `go / no-go`

---

# 7. 风险与回退

- 风险：把 human review 做成过重流程
- 控制：只保留 `awaiting_review -> approve/reject -> terminal`
