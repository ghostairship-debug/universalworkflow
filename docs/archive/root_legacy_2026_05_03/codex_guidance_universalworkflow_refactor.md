# Codex 指导文档：UniversalWorkflow 商业游戏 Pipeline 真相链与架构重构

> 目标读者：Codex / repo mutation agent  
> 仓库：`ghostairship-debug/universalworkflow`  
> 当前重点：不要继续堆商业游戏内容实现；先修复“失败不能成功”的控制面、DB 权威链、证据合同、需求无损传递、玩法语义 gate 与 QA/Supervisor 红队防线。

---

## 0. 当前事实，不得改写

当前商业游戏生产线结论是 **NO-GO**。

必须保持以下事实：

```text
machine_evidence_go=false
human_player_review_go=false
commercial_playable_go=false
```

最新严格 pipeline `pipeline_ecf26665254e` 虽然产生了 Cocos build、browser playtest、screenshots、audio/runtime proof、feature coverage 和事件证据，但真实人工评审判定失败。失败不是 URL 或 build 路径错误，而是产品级失败：当前 build 本体不是合格商业游戏，而是 runtime hook / canvas / event coverage 被机器 gate 误收。

禁止在任何 README、closeout、pipeline evidence、gate output 或测试 fixture 中把以下内容写成商业可玩完成：

```text
feature flags
browser events
canvas hash
screenshots only
build artifact exists
Cocos toolchain/bridge evidence
runtime hook
DOM-created canvas
scaffold / smoke / build-only evidence
```

---

## 1. 核心目标

本轮 Codex 修改目标不是“继续实现游戏内容”，而是修复系统性假阳性。

优先级顺序：

1. **Execution Truth Hardening**  
   让 DB task card lifecycle、fresh CLI attempt、receipt、child run、ledger 和 downstream short-circuit 成为硬门槛。

2. **Evidence Reuse 降级**  
   历史 evidence 只能作为 reference/preflight/resume hint，不得完成 implementation gate。

3. **Operator Fallback 边界收窄**  
   operator fallback 只能修 workflow/control-plane/diagnostic/docs，不能满足产品实现卡。

4. **Lossless Requirement Compiler**  
   PDF / source brief 的核心需求必须以 requirement matrix 形式无损传递到 agent output 和 task card。

5. **Gameplay Semantic Gate**  
   新增玩法语义证据合同，阻止 event-only、feature-flag-only、runtime-hook-only 通过产品 gate。

6. **Cocos Product Body Baseline**  
   建立非固定模板、但真实 Cocos component-based 的游戏架构底座。

7. **Adversarial QA / Supervisor**  
   QA 和 Supervisor 默认寻找反证，即使机器 gate pass，也能因产品本体无效强制 NO-GO。

8. **架构边界重构**  
   将 OrchestratorService 继续保持为 façade，逐步拆分 DB lifecycle、evidence truth、final gate、gameplay semantic gate 等服务。

---

## 2. 非目标与禁止事项

本轮不要做：

```text
不要新增商业游戏内容卡
不要恢复旧 commercial_cocos_game fixed template
不要把 old template 改名后重新启用
不要让 operator fallback 写产品实现文件后标 completed
不要扩大 provider timeout 来掩盖任务粒度过大
不要新增 event/feature flag 作为 GO 条件
不要把 Cocos bridge/toolchain evidence 当作 product body evidence
不要把 human review 推迟成可选项
不要生成未来 phase task cards
不要自动声明 M110 或 commercial playable GO；必须保持当前 NO-GO / human-review guard
```

旧 `commercial_cocos_game` 路线必须继续 hard fail，只允许指向 `commercial_game_production`。

---

## 3. 需要优先修改的文件

### 3.1 `packages/core_domain/task_card_store.py`

当前问题：`task_card_quality_report` 主要检查卡片内容质量，未把 DB lifecycle `status=draft` 作为不可执行条件。

需要修改：

```text
quality_status: passed/blocked
lifecycle_status: draft/active/running/completed/blocked/failed/archived
execution_eligible: true/false
```

规则：

```text
status=draft        => execution_eligible=false
status=archived     => execution_eligible=false
status=blocked      => execution_eligible=false
status=failed       => execution_eligible=false
status=active       => execution_eligible=true, if quality passed
status=approved     => execution_eligible=true, if quality passed
status=running      => execution_eligible=false for new execution, unless resume path explicitly validates attempt
status=completed    => execution_eligible=false for new execution, but can be consumed as completed only if DB says completed
```

`task_card_quality_report` 的 `go_no_go` 不得只依赖 quality。建议输出：

```json
{
  "schema_version": "m108_task_card_quality_v2",
  "task_card_count": 0,
  "quality_blocked_count": 0,
  "lifecycle_blocked_count": 0,
  "execution_eligible_count": 0,
  "go_no_go": "GO|NO-GO",
  "task_cards": [
    {
      "task_card_id": "...",
      "quality_status": "passed",
      "lifecycle_status": "draft",
      "execution_eligible": false,
      "issues": [
        {"code": "task_card_not_active", "field": "status", "value": "draft"}
      ]
    }
  ]
}
```

### 3.2 `packages/contributions/pipelines/commercial_game_task_worker.py`

当前问题：same-project worker 可筛选 `execution_mode=same_project_patch`，但必须进一步强制 DB lifecycle。

需要修改：

```text
same_project_business_task_cards(...) 只返回 execution_eligible=true 的卡
execute_same_project_task_cards(...) 必须拒绝 draft/archived/blocked/failed 卡
_run_task_card_with_retry_policy(...) 完成时必须具备 fresh receipt_id、child_run_id、attempt_id 或明确等价字段
```

禁止：

```text
attempts=0 => completed
worker_adapter=existing_same_project_evidence => completed
satisfaction_mode=existing_same_project_evidence => completed
prior completed ledger => fresh implementation completed
```

历史 evidence 只能改成：

```text
satisfaction_mode=reused_reference_only
status=reference_only
implementation_gate_satisfied=false
```

### 3.3 `packages/contributions/pipelines/commercial_game_production.py`

当前问题：worker stage 主要依赖 task-card quality report 和 downstream evidence contracts。

需要修改：

```text
execute_commercial_game_task_card_worker 在 task_card_quality_report 之后，增加 execution eligibility gate
若 task_card_lifecycle_no_go，则 worker stage blocked，failure_class=task_card_lifecycle_no_go
上游 same_project_worker_patch_go=false 时，build/playtest/product-depth/human-review 必须 short-circuit
machine_evidence_go 不得绕过 gameplay_semantic_go / product_body_go
```

### 3.4 `packages/contributions/pipelines/commercial_game_evidence_contracts.py`

新增两个合同：

```text
GAMEPLAY_SEMANTIC_EVIDENCE_SCHEMA = "commercial_game_gameplay_semantic_evidence_v1"
PRODUCT_BODY_EVIDENCE_SCHEMA = "commercial_game_product_body_evidence_v1"
```

新增 blocker：

```text
runtime_hook_not_product_body
canvas_only_product_body
feature_flag_only_evidence
event_only_gameplay_evidence
semantic_board_state_missing
semantic_piece_model_missing
semantic_placement_trace_missing
semantic_line_clear_trace_missing
semantic_candidate_refresh_trace_missing
semantic_game_over_trace_missing
semantic_anti_stall_trace_missing
cocos_component_binding_missing
```

最终 gate 必须满足：

```text
asset_graph_go
cocos_bridge_go
same_project_fresh_cli_patch_go
build_go
browser_smoke_go
gameplay_semantic_go
product_body_go
human_player_review_go
```

其中 `browser_smoke_go` 只能证明运行 smoke，不能证明 gameplay semantic 或 product body。

### 3.5 `tests/`

优先新增或修改测试：

```text
test_draft_task_card_cannot_execute_even_if_quality_passed
test_markdown_snapshot_cannot_promote_db_draft_to_completed
test_existing_same_project_evidence_is_reference_only
test_attempts_zero_cannot_complete_implementation_card
test_operator_fallback_cannot_satisfy_product_implementation
test_product_write_set_modified_by_operator_fallback_blocks_commercial_gate
test_feature_flags_only_do_not_pass_product_body
test_event_list_only_do_not_pass_gameplay_semantic_gate
test_dom_canvas_runtime_hook_blocks_product_body
test_screenshots_without_semantic_trace_no_go
test_qa_rejects_pipeline_ecf266_like_evidence
test_supervisor_overrides_gate_pass_when_product_body_invalid
```

测试优先放在：

```text
tests/test_pipeline_and_automation_cli.py
tests/test_commercial_game_evidence_contracts.py
tests/test_task_card_store.py
tests/test_commercial_game_task_worker.py
```

---

## 4. DB task card 权威规则

DB 是 task card 权威源。Markdown 只是 snapshot。

硬规则：

```text
DB draft card 不能执行
DB draft card 不能被 ledger 标 completed
Markdown snapshot 不能提升 DB 状态
pipeline-local ledger 不能单方面改变 DB lifecycle
quality passed 不等于 completed
completed 必须来自 fresh CLI child run 或 DB 中已完成且可验证的 lifecycle
```

推荐实现一个 helper：

```python
def task_card_execution_eligibility(card: TaskCard) -> dict[str, Any]:
    ...
```

返回：

```json
{
  "execution_eligible": false,
  "lifecycle_status": "draft",
  "blockers": ["task_card_not_active"]
}
```

---

## 5. fresh CLI execution 规则

商业实现卡只能由真实 CLI path 完成：

```text
workflowctl run from-task-card --execute
```

完成 entry 必须至少具备：

```text
receipt_id
child_run_id
attempt_id 或 child_attempt_id
attempt_index >= 1
worker_adapter != shell/noop/dry_run/existing_same_project_evidence
accepted patch 或明确 mutation_result
changed_files
final_test_status passed
DB lifecycle completed
```

三次失败规则：

```text
runtime_max_attempts=3
每次 fresh receipt
每次记录 stdout/stderr preview、failure_class、watchdog、continuation command
三次失败后 status=blocked，failure_class=blocked_after_three_attempts
下游 build/playtest/product-depth/human-review 全部 skipped_due_to_upstream_failure
```

---

## 6. Evidence reuse 规则

允许 reuse：

```text
preflight reference
resume hint
regression baseline
prior evidence comparison
operator audit context
```

禁止 reuse：

```text
implementation completed
same_project_worker_patch_go=true
commercial_playable_go=true  # forbidden unless explicit NO-GO / human-review guard has been cleared
machine_evidence_go=true
human review substitute
```

建议把原先 `existing_same_project_evidence` 改名为：

```text
reused_reference_only
```

并强制输出：

```json
{
  "status": "reference_only",
  "implementation_gate_satisfied": false,
  "attempts": [],
  "attempt_count": 0,
  "blockers": ["fresh_cli_execution_missing"]
}
```

---

## 7. Operator fallback 边界

operator fallback 可用于：

```text
workflow bug repair
control-plane diagnostic
evidence correction
doc/postmortem
test fixture hardening
provider timeout/root-cause analysis
```

operator fallback 不可用于：

```text
商业产品实现卡
Cocos game body implementation
BlockPuzzleGame.ts / main.scene 等 product write_set 的实现完成证明
same_project_worker_patch_go
commercial_playable_go
```

如果 fallback 修改了 product write_set：

```text
product_implementation_by_operator_fallback=true
product_body_go=false
commercial_playable_go=false
blocker=operator_fallback_product_implementation_not_allowed
```

---

## 8. Lossless Requirement Compiler

新增 requirement matrix。不要再让 agent output 把源需求压缩成 advisory summary。

每条需求格式：

```json
{
  "req_id": "REQ-CORE-001",
  "source_path": "...",
  "page": 1,
  "original_quote": "...",
  "normalized_requirement": "10x10 棋盘，底部 3 个候选方块，拖拽放置，行列填满消除",
  "category": "core_gameplay",
  "priority": "must",
  "acceptance_method": "gameplay_semantic_gate",
  "downstream_owner": "gameplay_worker"
}
```

必须覆盖核心玩法：

```text
10x10 board
3 candidate pieces
drag placement
legal/illegal placement
row/column clear
refresh after all 3 candidates used
game over
anti-stall safeguard
classic mode
level/adventure mode
revive
shop/skin
props
gallery/collection
UI hierarchy
audio/feedback
level table/config
```

规则：

```text
agent role output 不得删除 source req
agent role output 不得合并 req_id
agent role output 不得改名 source requirement
derived requirement 必须单独标注 derived_requirements
没有 req_id coverage 的 task card 不得执行
source_count/input_count/chunk_count 不一致必须 fail fast
```

---

## 9. Gameplay Semantic Gate

新增真实玩法语义 gate，而不是继续增加 feature flag。

必须验证：

```text
board_state: 10x10
piece_shapes: non-empty shape set
candidate_tray: exactly 3 candidates
placement: legal placement changes board
illegal_placement: rejected without board mutation
line_clear: row/column filled then cleared
candidate_refresh: only after all 3 candidates consumed
score_progression: score changes after valid actions
combo_or_streak: if declared, trace exists
game_over: no legal moves triggers game over
anti_stall: safeguard can produce/verify playable candidate
level_goal_progression: level goal changes with board actions
props: prop changes board state if declared
revive: revive changes failed state if declared
```

示例合同：

```json
{
  "schema_version": "commercial_game_gameplay_semantic_evidence_v1",
  "status": "completed",
  "gameplay_semantic_go": true,
  "product_body_go": true,
  "blockers": [],
  "source": {
    "board_size": "10x10",
    "move_trace_path": "...",
    "line_clear_trace_path": "...",
    "game_over_trace_path": "..."
  }
}
```

负例必须失败：

```text
只有 featureCoverage=true
只有 events 列表
只有 canvas hash
只有截图
只有 DOM hook state
只有 Cocos bridge/toolchain evidence
```

---

## 10. Cocos Product Body Baseline

不要恢复旧 fixed template。需要的是“非模板但真实”的 Cocos component baseline。

建议新增模块：

```text
packages/contributions/games/cocos/product_body/
  board_model.py 或生成 TypeScript baseline 的 Python builder
  piece_model.py
  rule_engine.py
  candidate_tray.py
  semantic_harness.py
  product_body_contract.py
```

Cocos 项目侧建议生成：

```text
assets/scripts/BoardModel.ts
assets/scripts/PieceModel.ts
assets/scripts/RuleEngine.ts
assets/scripts/CandidateTray.ts
assets/scripts/BoardView.ts
assets/scripts/InputController.ts
assets/scripts/LevelGoalController.ts
assets/scripts/ShopSkinController.ts
assets/scripts/AudioFeedbackController.ts
assets/scripts/SemanticTestBridge.ts
```

Product body gate 必须确认：

```text
关键 Scene 节点存在
关键节点有真实 Cocos component 绑定
玩法状态来自 Cocos component/model，不是 DOM hook
semantic trace 可从真实 runtime/model 导出
DOM/canvas hook 仅可 diagnostic，不可 product body
```

---

## 11. QA 与 Supervisor 红队规则

QA 默认不是确认者，而是反证者。

QA 输出建议：

```json
{
  "schema_version": "commercial_game_red_team_qa_v1",
  "status": "blocked",
  "red_team_findings": [
    {
      "finding": "runtime_hook_not_product_body",
      "severity": "critical",
      "blocks": ["product_body_go", "commercial_playable_go"],
      "evidence": "..."
    }
  ],
  "attempted_disproofs": [],
  "accepted_proofs": []
}
```

Supervisor 必须能在以下情况强制 NO-GO：

```text
DB task card 仍是 draft
implementation card 不是 fresh CLI 完成
attempts=0
worker_adapter=existing_same_project_evidence
operator fallback 修改 product write_set
runtime hook / canvas-only game body
browser playtest 只有 event/feature flag
source requirement coverage 不完整
gameplay semantic proof 缺失
human review 缺失或失败
```

---

## 12. 架构拆分建议

不要继续让 `OrchestratorService` 承担更多领域职责。它可以保留为应用 façade。

建议逐步拆分：

```text
TaskCardLifecycleService
EvidenceTruthService
ReceiptLeaseService
ProviderExecutionService
RepoMutationService
PipelineExecutionService
CommercialFinalGateService
HumanReviewService
GameplaySemanticGateService
```

Repository 也建议按 aggregate 拆分：

```text
repositories/run_repository.py
repositories/task_card_repository.py
repositories/evidence_repository.py
repositories/receipt_repository.py
repositories/lease_repository.py
repositories/provider_repository.py
```

短期不要大爆炸式迁移。先在现有文件中加 helper 和 tests，把行为修正确认后，再做模块拆分。

---

## 13. 推荐实施顺序

### Step 1：DB lifecycle gate

修改：

```text
packages/core_domain/task_card_store.py
packages/contributions/pipelines/commercial_game_task_worker.py
packages/contributions/pipelines/commercial_game_production.py
```

验收：

```text
draft card 即使 quality passed 也不能执行
quality report 输出 lifecycle_blocked_count
worker stage 因 draft card blocked
```

### Step 2：evidence reuse 降级

修改：

```text
packages/contributions/pipelines/commercial_game_task_worker.py
packages/contributions/pipelines/commercial_game_evidence_contracts.py
```

验收：

```text
existing_same_project_evidence => reference_only
attempts=0 => cannot complete
same_project_worker_patch_go=false
```

### Step 3：operator fallback product write_set blocker

修改：

```text
packages/contributions/pipelines/commercial_game_evidence_contracts.py
packages/contributions/pipelines/commercial_game_task_worker.py
```

验收：

```text
operator fallback 修改产品文件 => product_body_go=false
```

### Step 4：semantic/product body contracts

修改：

```text
packages/contributions/pipelines/commercial_game_evidence_contracts.py
```

验收：

```text
feature flags only fails
events only fails
runtime hook fails
semantic trace passes only when board/piece/placement/clear/gameover proof exists
```

### Step 5：requirement matrix

新增/修改：

```text
packages/core_domain/unified_project_brief.py
packages/core_domain/role_agent_executor.py
packages/contributions/pipelines/commercial_game_production.py
```

可先做最小合同与测试，不必一次完整 PDF 解析。

### Step 6：QA/Supervisor 红队

修改：

```text
packages/contributions/pipelines/commercial_game_production.py
packages/contributions/pipelines/commercial_game_evidence_contracts.py
```

验收：

```text
即使 gate pass，只要 product body invalid，Supervisor 输出 NO-GO
```

---

## 14. 建议测试命令

优先跑：

```powershell
python -m pytest -q tests/test_pipeline_and_automation_cli.py
python -m pytest -q tests/test_task_card_store.py
python -m pytest -q tests/test_commercial_game_evidence_contracts.py
python -m pytest -q tests/test_commercial_game_task_worker.py
```

全量收口：

```powershell
python -m pytest -q
python -m infra.scripts.check_doc_links
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" governance active-truth-check --strict --output-path state/governance/active_truth_check.json
```

不要用通过 build/browser smoke 替代上述 negative tests。

---

## 15. 修改后的成功标准

本轮成功不是 commercial GO，而是：

```text
系统诚实失败
DB draft 无法执行
历史 evidence 无法满足 implementation
operator fallback 无法满足产品实现
上游 worker fail 后下游短路
event-only/feature-flag-only/runtime-hook-only 无法通过 gate
human review 缺失或失败时不能 commercial GO
README/CURRENT_DEVELOPMENT_WORKFLOW/final gate truth 一致
```

只有这些完成后，才允许进入下一轮真实 Cocos product body baseline 和商业游戏内容实现。

---

## 16. Codex 执行提醒

执行时请遵守：

```text
先补 negative test，再改实现
每个 patch 尽量小
不要扩大 unrelated refactor
不要修改历史结论为 GO
不要删除 postmortem 中的 NO-GO 事实
不要制造新的 future phase/task cards
不要绕过 DB/repo mutation/write_set 边界
```

优先让旧问题必然失败，再考虑新增正例。
