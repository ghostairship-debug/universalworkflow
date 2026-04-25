# M48-M51 修复 / 优化计划（三方评估整合版）

- 日期：2026-04-25
- 当前基线：已接受 `M47`
- 输入评估（按提交顺序）：
  - [PROJECT_DEEP_EVALUATION_M37.md](PROJECT_DEEP_EVALUATION_M37.md)（M37 内部评估，已吸收）
  - [GPTPRO_EVALUATION.md](GPTPRO_EVALUATION.md)（GPT Pro，2026-04-25 更新）
  - [PROJECT_DEEP_EVALUATION_M48_TRIAGE.md](PROJECT_DEEP_EVALUATION_M48_TRIAGE.md)（Codex，2026-04-25）
  - [PROJECT_DEEP_EVALUATION_M47_OPUS.md](PROJECT_DEEP_EVALUATION_M47_OPUS.md)（Opus，2026-04-25）
- 产品前提：个人自用 / 本地 operator runtime；不打开公开 SaaS 或多租户

## 0. 这份计划是什么

这份计划不是又一份新评估。它把 **Opus / Codex / GPT Pro** 三份独立评估中**真正交叉验证过**的问题挑出来，按风险和依赖排成 **4 个 M、共 18 个 phase**，并明确：

1. 每个 phase **修什么文件**、**用什么验收标准**
2. **workflow 自身**（CLI / API / `OrchestratorService` / `repo_mutation`）在 phase 中承担什么
3. **Codex CLI dogfood** 在 phase 中承担什么
4. 人工（你 / 我，Opus）在 phase 中承担什么

> **核心原则**：从 M48 开始，**项目自己修自己**。每个 phase 都是一张本地 task card，由 `workflowctl run from-task-card` 执行；实现侧默认走 Codex CLI（强 dogfood backend），评审侧走 review_cluster 或 launch_guard。这一方面偿还结构债，另一方面把 dogfood 从"声称能用"变成"自己已经在用"。

## 1. 三方评估交叉一致的问题（去重后）

| 编号 | 问题 | Opus | Codex | GPT Pro | 严重度 |
| --- | --- | :---: | :---: | :---: | :---: |
| F1 | 测试可复现性差（SQLite WAL 锁 / 固定 basetemp / 中断后污染） | ✓ | ✓ | — | P0 |
| F2 | OrchestratorService 仍 3500+ 行单 facade，TD-STRUCT-001 在 M40-M47 反向膨胀 | ✓ | ✓ | ✓ | P0 |
| F3 | API 高风险动作只有 chat/UI 层确认，**API 层无强制硬闸** | — | ✓ | ✓ | P0 |
| F4 | repo mutation patch_apply 多文件失败时**不原子**，可能留下部分修改 | — | ✓ | — | P0 |
| F5 | workspace root 隐式取 `Path.cwd()`，启动位置错则边界整体偏移 | — | — | ✓ | P0 |
| F6 | core_domain 出现 1206 行游戏 HTML 模板（`local_game_artifacts.py`） | ✓ | ✓ | — | P1 |
| F7 | Web UI 单文件 1398 行，`innerHTML` 拼接 SSE payload 字段 | — | ✓ | ✓ | P1 |
| F8 | capability health 仍 descriptor-based，不是 runtime telemetry（TD-STRUCT-005） | — | ✓ | ✓ | P1 |
| F9 | scheduler-authority flag off 时仍构造 5 个 repo + import 1646 行模块 | ✓ | — | ✓ | P1 |
| F10 | README/docs ↔ 代码事实漂移（命令位置、模型默认、test 数字、active truth set 含历史文档） | ✓ | ✓ | ✓ | P1 |
| F11 | API `create_app()` import-time 副作用（migrate + service init） | — | — | ✓ | P1 |
| F12 | offline_validation 单步无 timeout、不报告 elapsed | — | ✓ | — | P1 |
| F13 | chat_runtime.py 738 行单文件，MiniMax 误继承 DeepSeek | ✓ | — | — | P2 |
| F14 | CLI main.py 1535 行 60+ 命令未按 sub-app 拆 | ✓ | — | — | P2 |
| F15 | service_interaction.py 2315 行 mixin 包含 chat/session/profile/watchdog 四类职责 | ✓ | ✓ | — | P2 |
| F16 | 缺 CI / lockfile / Python 版本可复现性 | — | — | ✓ | P2 |
| F17 | LangGraph durable execution 与 workflow.db 双状态源未对齐 | — | — | ✓ | P2 |
| F18 | doctor 命令是只读，未挂在 pre-commit / CI 入口；缺 `--strict` | ✓ | — | — | P2 |

> **观察**：F1-F5 都被两份以上评估共同识别为 P0。这构成 M48 + M49 的核心。F6-F12 是 P1，主要在 M50 处理。F13-F18 是 P2，留 M51 + 后续。

## 2. 4 个 M 的总体结构

```
M48  Trust Foundation     (4 phase)  —  让"绿"恢复可信
M49  Boundary Hardening   (5 phase)  —  让高风险动作有硬边界
M50  Service Decomposition(5 phase)  —  让 OrchestratorService 真正瘦下来
M51  Reality Verification (4 phase)  —  让能力健康从声称变成事实
```

**为什么是 4 个 M 而不是 1 个大 M**：每个 M 主题独立、验收独立，避免重蹈 M40-M47 编号膨胀但内容稀薄的覆辙。每个 M 收口前必须重新跑全套 `--run-slow`，不允许越级。

**为什么不再多**：超过 4 个 M 你会丧失耐心；这 4 个 M 的总工作量按你的实际节奏估约 4-6 周。

**M52+ 不在本计划内**：M51 收口后再决定要不要做（可选项写在 §7）。

## 3. Codex / Workflow 协作协议（先读这一节）

### 3.1 三方角色

每个 phase 涉及三个角色：

| 角色 | 谁 | 主要动作 |
| --- | --- | --- |
| **Planner** | 你 + Opus（或 chat workbench） | 把 phase 拆成 task card；写明 write_set / read_set / test_commands / mutation_mode；定义验收 |
| **Implementer** | Codex CLI（`adapter_name="codex"`） | 在 mutation contract 约束下生成 unified diff patch；改代码、改测试 |
| **Reviewer** | review_cluster 或人工 launch_guard | 跑 quality gate，决定 approve / reject / request_changes |

### 3.2 每个 phase 的标准执行序列

```bash
# 1. Planner 准备 task card（Markdown 文件）
#    放在 examples/local_task_cards/m48/p1_unique_basetemp.md
#    内容：goal、write_set、read_set、test_commands、acceptance

# 2. workflow 把 task card 转成 run（patch_apply 模式）
workflowctl --db-path state/workflow.db run from-task-card \
  examples/local_task_cards/m48/p1_unique_basetemp.md \
  --write-set pyproject.toml --write-set tests/conftest.py \
  --test-command "python -m pytest tests/test_repositories.py -q" \
  --mutation-mode patch_apply \
  --execute

# 3. Codex 强 dogfood 自动接管 implementer 角色
$env:WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED="1"
$env:WORKFLOW_DOGFOOD_EXECUTION_BACKEND="codex_cli"
$env:WORKFLOW_DOGFOOD_MODEL="gpt-5.5"
# Codex 输出 patch → repo_mutation 应用 → 跑 test_command → 通过则 evidence 落库

# 4. 失败时自动回滚
#    repo_mutation 在每轮失败前 restore_workspace_snapshot
#    （F4 修复后这一步对多文件 patch 也会硬保证）

# 5. Reviewer（review_cluster 或人工）
workflowctl --db-path state/workflow.db run pr-ready-summary <run_id>
#    → 输出包含 diff、test attempts、评估意见
#    → 高风险 phase 必须人工 approve

# 6. 收口
#    把 M{N} Phase {P} 状态写回 docs/milestone_history.md
#    把当前 phase 任务卡归档（git 历史保留，不复活）
```

### 3.3 风险分级与确认门

按 GPT Pro 提议的 `OperatorActionReceipt` 概念（M49 Phase 1 实现），每个 phase 在执行前**必须**根据风险等级决定确认方式：

| 风险等级 | 适用 phase | 确认要求 | review_policy |
| --- | --- | --- | --- |
| **低** | 文档变更、单测试新增、非领域代码迁移 | 自动批准 | `auto_only` |
| **中** | 单文件 refactor、子模块拆分、新增 service 方法 | chat 确认卡 | `recommended` |
| **高** | API 行为变更、安全协议、`OrchestratorService` 接口变更、跨文件 refactor | 人工 approve + receipt | `human_required` |
| **极高** | DB schema 迁移、scheduler-authority 隔离、删除/移走 core_domain 模块 | 人工 approve + receipt + 回滚演练 | `mandatory` |

### 3.4 evidence 落地约定

每个 phase 在 `state/m{N}_phase{P}_*` 下保留 evidence。命名约定：

```
state/m48_phase1_unique_basetemp/
  task_card.md           # 实际执行的 task card 副本
  patch.diff             # codex 输出的 unified diff
  test_attempts.json     # repo_mutation.run_test_commands 的 attempts
  pr_ready_summary.md    # 最终 review summary
  closeout.json          # acceptance 检查结果
```

收口时只把摘要并入 `docs/milestone_history.md`，evidence 留在 `state/`。

## 4. M48 — Trust Foundation（信任基线）

> **主题**：让 `pytest -q` 和 `workflowctl doctor` 重新成为可以无脑信任的入口。
>
> **不解决**的事：不动 `OrchestratorService`、不动 API 安全、不动 capability health。这些都依赖测试和文档先稳。

### Phase 0：基线对齐与历史归档（低风险）

**目标**：让"现在的事实"和"文档说的事实"一致。

**修改对象**：
- `README.md` — `workflowctl doctor` 命令位置错误（应为 `workflowctl --db-path ... doctor`，Codex 实测发现）
- `README.md` — 默认 `gpt-5.5` 与代码默认 `gpt-5.4` 漂移（Opus 发现）
- `README.md` — `pytest -q` 实测数（Codex 实测 `242 passed, 134 skipped`，应写入）
- `docs/current_development_workflow.md` — `active truth sources` 收窄
- 新增 `docs/historical_evaluations/` 目录，把 `M38_REPAIR_AND_DEVELOPMENT_PLAN.md`、`PROJECT_DEEP_EVALUATION_M37.md`、`GPTPRO_EVALUATION.md`、`PROJECT_DEEP_EVALUATION_M48_TRIAGE.md`、`PROJECT_DEEP_EVALUATION_M47_OPUS.md`、本计划归档进去

**workflow 侧**：
- task card：`m48/p0_baseline_alignment.md`
- write_set：`README.md`、`docs/current_development_workflow.md`、`docs/milestone_history.md`
- review_policy：`auto_only`
- test_command：`python -m infra.scripts.check_doc_links`

**codex 侧**：implementer（强 dogfood gpt-5.5）

**人工侧**：你 review 一次实测数字是否正确

**验收**：
- README 里所有命令在 PowerShell 下可直接复制运行
- `active truth sources` 列表 ≤ 6 个，全部为非历史
- `check_doc_links` 0 issue
- 根目录只剩 README + 本计划 + 最新评估（其余归档）

---

### Phase 1：唯一 basetemp + 测试可复现性（高风险）

**目标**：F1 修复 — 让连续中断的 pytest 不再污染下一次运行。

**修改对象**：
- `pyproject.toml` — 移除 `--basetemp=state/.pytest-tmp` 全局固定（Codex 在 §3.1 指出，Opus 实测确认）
- `tests/conftest.py` 25 行 — 加 session-scope autouse fixture：
  - 启动前清理 `state/.pytest-tmp/`（带 retry）
  - 启动前列出残留 `python.exe` / `codex.exe` 子进程（不杀，只警告）
  - 每个用 `tmp_path_factory` 创的 SQLite 在 teardown 强制 WAL checkpoint + close
- `Makefile` 新增 `test-fast` 目标：`pytest -q --basetemp=$(shell mktemp -d) --tb=short --durations=20`
- `infra/validation/common.py` — `run_command()` 加 per-command timeout 和 elapsed_ms（F12）

**workflow 侧**：
- task card：`m48/p1_test_reliability.md`
- write_set：`pyproject.toml`、`tests/conftest.py`、`Makefile`、`infra/validation/common.py`
- review_policy：`human_required`（动测试基础设施）
- test_command：连续跑 5 次 `pytest -q tests/test_repositories.py tests/test_doctor.py`，全部 0 ERROR

**codex 侧**：implementer + quality_gate（review_cluster 跑回归）

**人工侧**：你必须 approve；测试基础设施改错会让后续所有 phase 看起来红

**验收**：
- 连续 5 次 `pytest -q` 0 ERROR
- 中断一次后，第二次启动**不会**因为残留 SQLite WAL 文件失败
- `state/.pytest-tmp/` 在每次启动前被清掉
- offline_validation 报告中每个 flow 有 `elapsed_ms` 字段

---

### Phase 2：测试三层化（中风险）

**目标**：默认 `pytest -q` 6 分钟太慢（Codex 实测 367 秒），形成"测试入口缺席"。

**修改对象**：
- `tests/conftest.py` — 加新 marker：`unit`、`core`、`integration`
- `tests/test_execution_loop.py` 3344 行 — 把 subprocess / 多 child orchestration 类移到 `tests/integration/test_execution_loop_integration.py` 并标 `slow + integration`
- `Makefile` — `test-unit`（< 60 秒）、`test-core`（< 3 分钟）、`test-integration`（M 收口跑）
- `pyproject.toml` — 给 pytest addopts 加 `-m "not integration"` 默认

**workflow 侧**：
- task card：`m48/p2_test_layering.md`
- write_set：`tests/conftest.py`、`tests/test_execution_loop.py`、`tests/integration/`、`Makefile`、`pyproject.toml`
- review_policy：`human_required`
- test_command：`make test-unit`（< 60s）+ `make test-core`（< 180s）

**codex 侧**：implementer

**人工侧**：你 approve 三层划线（哪些算 unit / core / integration）

**验收**：
- `make test-unit` < 60 秒
- `make test-core` < 180 秒
- `make test-integration` 包含 M 收口 slow 套件
- `pytest -q` 默认行为仍然合理（向后兼容）

---

### Phase 3：M48 收口

**目标**：把 M48 写进 `docs/milestone_history.md`，准备 M49 入口。

**修改对象**：
- `docs/milestone_history.md` — 加 M48 行
- `docs/tech-debt-registry.md` + `docs/governance/tech_debt_registry.json` — F1/F12 标 `repaid`
- `README.md` — 更新当前基线为 M48

**workflow 侧**：task card `m48/p3_closeout.md`，`auto_only`，跑 `pytest -q --run-slow`

**codex 侧**：doc_curator（强 dogfood）

**验收**：完整 `pytest -q --run-slow` 通过；offline validation 通过；doc link 通过

## 5. M49 — Boundary Hardening（边界硬化）

> **主题**：把"高风险动作"的安全保证从约定（chat 卡）变成协议（API receipt）。
>
> **不解决**的事：不重构 OrchestratorService 内部职责（M50）；不改 capability health（M51）。

### Phase 0：workspace root 显式化（极高风险）

**目标**：F5 修复 — repo mutation 边界不再依赖进程启动目录。

**修改对象**：
- `packages/core_domain/config.py` — 加 `workspace_root` 字段，优先级：`--workspace-root` > `WORKFLOW_WORKSPACE_ROOT` > `pyproject.toml` 的 `[tool.workflow]` > `cwd`（最后才用，且打 warning）
- `packages/core_domain/services.py:483` — `_workspace_root()` 改读 `effective_config["workspace_root"]`
- `packages/core_domain/repo_mutation.py` — 所有 `_workspace_root` 入口对齐
- `apps/operator_cli/main.py` — `--workspace-root` 全局 option
- `apps/orchestrator_api/main.py` — `WORKSPACE_ROOT` 启动校验
- `apps/orchestrator_api/web_ui.py` — workbench 顶部红字显示 implicit cwd warning

**workflow 侧**：
- task card：`m49/p0_workspace_root.md`
- write_set：上述 6 个文件
- review_policy：`mandatory`
- test_command：新增 `tests/test_workspace_root.py`（4 个用例：config / env / cwd / mismatch）

**codex 侧**：implementer + quality_gate

**人工侧**：必须人工 approve；这是会改变所有 mutation 行为的根接口

**验收**：
- task card 中 4 个测试用例全过
- 启动时显示当前 workspace root（implicit 时红色 warning）
- `write_set`/`read_set`/`task_card_path` 全部基于显式 root canonicalize

---

### Phase 1：API OperatorActionReceipt 协议（极高风险）

**目标**：F3 修复 — 实施 GPT Pro 提议的 `OperatorActionReceipt` 协议。

**修改对象**：
- 新增 `packages/contracts/operator_action_receipt.py` — Pydantic 模型 + 状态机
- 新增 SQLite 表 `operator_action_receipts`（migration）
- `packages/core_domain/repositories.py` — 加 `OperatorActionReceiptRepository`
- 新增 `apps/orchestrator_api/security.py` — `require_operator_action` FastAPI dependency
- `apps/orchestrator_api/routers/runs.py` — 高风险 endpoint 全部加 dependency：
  - `POST /runs/launch` (execute=true)
  - `POST /runs/{id}/resume`
  - `POST /runs/{id}/approve`
  - `POST /runs/{id}/reject`
  - `POST /runs/{id}/cancel`
  - 所有触发 repo mutation 的 endpoint
- `apps/orchestrator_api/routers/ui.py` — confirmation card 改为先生成 receipt，再 POST
- 新增 `tests/test_operator_action_receipt.py` — 实现 GPT Pro 提议的 10 个安全测试

**workflow 侧**：
- task card：`m49/p1_operator_action_receipt.md`
- write_set：约 8 个文件
- review_policy：`mandatory`
- test_command：`make test-core` + `pytest tests/test_operator_action_receipt.py -q`

**codex 侧**：implementer（强 dogfood，分两轮：第一轮 contract + repo + dependency，第二轮 routers + UI）

**人工侧**：必须人工 approve；这是 API 行为变更

**验收**（GPT Pro §安全边界测试）：
- 没有 receipt 的高风险 POST 全部 401/403
- 错误 action_type 的 receipt 被拒
- 过期 receipt 被拒
- 重放 receipt 被拒
- scope_hash 与 write_set/test_commands 不一致被拒
- GET /runs/{id}/status **不**需要 receipt

---

### Phase 2：repo mutation 原子性（高风险）

**目标**：F4 修复 — 多文件 patch 任意一文件失败时，**全部**回滚到 baseline。

**修改对象**：
- `packages/core_domain/repo_mutation.py:316` `apply_unified_diff` — 改为 staging apply：
  - 第一阶段：所有文件 patch 在内存中验证（每个 hunk dry-run）
  - 第二阶段：全部成功后才一次性写入
  - 任意失败：raise PatchApplyError，**不写入任何文件**
- `packages/core_domain/service_repo_mutation.py:99` `execute_repo_mutation` — 加 `try/finally` 保证最后一轮失败时 `restore_workspace_snapshot`
- 新增 `tests/test_repo_mutation_atomicity.py` — 第一文件成功、第二文件失败时断言第一文件恢复 baseline

**workflow 侧**：
- task card：`m49/p2_mutation_atomicity.md`
- review_policy：`human_required`

**codex 侧**：implementer + quality_gate（review_cluster 跑全套 mutation 回归）

**验收**：
- 新增 atomicity 测试通过
- 现有 mutation 测试全部通过
- 多文件 patch 失败场景下 `git status` 显示无遗留改动

---

### Phase 3：Web UI XSS 修复 + CSP（高风险）

**目标**：F7 修复 — `innerHTML` 拼接 SSE payload 字段改为 `createElement + textContent`。

**修改对象**：
- `apps/orchestrator_api/web_ui.py` 1398 行 — workbench JS 部分所有 SSE payload 字段构造改安全 helper（Codex 在 §3.4 列了具体字段：`message.role`、`message.action_type`、`confirmation.action_type`、`confirmation.run_id`）
- `apps/orchestrator_api/main.py` — 加 CSP middleware：`default-src 'self'; script-src 'self'; style-src 'self'`
- 新增 `tests/test_web_ui_xss.py` — 注入 `<script>` 到 run title / error message / task title，断言被 escape

**workflow 侧**：
- task card：`m49/p3_xss_csp.md`
- review_policy：`human_required`

**codex 侧**：implementer

**验收**：
- XSS 注入测试全过
- CSP header 在响应中存在
- workbench 仍能正常显示 SSE chat / status

---

### Phase 4：M49 收口

**修改对象**：`docs/milestone_history.md`、tech-debt-registry（F3/F4/F5/F7 标 `repaid`）

**验收**：完整 slow 套件 + offline validation 通过

## 6. M50 — Service Decomposition（服务拆分）

> **主题**：让 `OrchestratorService` 真正瘦下来；让 `core_domain` 不再装游戏 HTML。
>
> **关键纪律**：渐进抽取 + 冻结测试。**不**做一次性大重构。

### Phase 0：facade surface 冻结测试（中风险）

**目标**：先加 ratchet，再开始拆。

**修改对象**：
- 新增 `tests/test_facade_surface.py`：
  ```python
  def test_orchestrator_facade_method_count_is_below_ratchet():
      direct = direct_methods(OrchestratorService)
      assert len(direct) <= 158, "do not add new methods to OrchestratorService"
  ```
- 新增类似测试限制 `services.py` LOC（参考 GPT Pro 提议的 ratchet）：
  ```
  M48: services.py < 3600
  M49: services.py < 3500
  M50 收口: services.py < 3000
  M51 收口: services.py < 2400
  ```

**workflow 侧**：task card `m50/p0_ratchet.md`，`auto_only`

**codex 侧**：implementer

**验收**：测试通过；后续 phase 加新方法到 facade 会让此测试红

---

### Phase 1：core_domain 去污染（中风险）

**目标**：F6 修复 — 把 `local_game_artifacts.py` 1206 行游戏 HTML 移走。

**修改对象**：
- 新建 `packages/artifact_generators/games/{block_puzzle.py,snake.py}`
- 新建 `packages/artifact_generators/pdf_extraction.py`（保留 PDF 抽取，这是真领域能力）
- `packages/core_domain/__init__.py` — 移除 game artifacts 导出
- 调用方 import 路径迁移
- 删除 `packages/core_domain/local_game_artifacts.py`

**workflow 侧**：
- task card：`m50/p1_core_domain_cleanup.md`
- review_policy：`human_required`
- test_command：`pytest tests/test_m43_game_artifacts.py -q`

**codex 侧**：implementer

**验收**：
- `packages/core_domain/` 总行数 ≤ 当前 - 1000
- `tests/test_m43_game_artifacts.py` 全过
- `examples/block_puzzle_shop/index.html` 仍可生成

---

### Phase 2：第一刀拆分 — 按 GPT Pro 的"绞杀式"切（高风险）

**目标**：F2 第一轮 — 切出**只读 + 安全**两块，因为这两块边界最清晰。

新增 service：
- `packages/core_domain/service_projection_query.py`（`ProjectionQueryService`）— 承接 `service_projection.py` 中的纯查询
- `packages/core_domain/service_operator_action_guard.py`（`OperatorActionGuard`）— M49 Phase 1 的 receipt 协议核心逻辑放这里

**修改对象**：
- `packages/core_domain/services.py` — 抽出方法委派到新 service
- 调用方（routers / CLI）改为直接调用新 service 而不是 facade

**workflow 侧**：
- task card：`m50/p2_strangler_first_cut.md`
- review_policy：`human_required`

**codex 侧**：implementer + quality_gate

**验收**：
- `services.py` < 3300 行
- `OperatorActionGuard` 100% 覆盖 M49 receipt 验证
- facade surface 测试仍通过（方法数下降）

---

### Phase 3：第二刀 — RepoMutationCoordinator + ChatCommandController（高风险）

**目标**：F2 第二轮 — Codex 在 §3.2 提议的 6 个真实 owner 中再切两个最大的。

新增 service：
- `packages/core_domain/repo_mutation_coordinator.py` — patch generation/apply/test/fix loop/rollback
- `packages/core_domain/chat_command_controller.py` — chat intent → action proposal → receipt（合并 M49 P1 部分逻辑）

**修改对象**：`packages/core_domain/services.py`、`service_interaction.py`、`service_repo_mutation.py`

**workflow 侧**：
- task card：`m50/p3_strangler_second_cut.md`
- review_policy：`human_required`

**codex 侧**：implementer + quality_gate（分两个子 run，分别拆 mutation 和 chat）

**验收**：
- `services.py` < 3000 行（达到 M50 ratchet）
- `service_interaction.py` < 1800 行
- 所有现有 mutation / chat 测试通过

---

### Phase 4：scheduler-authority 真隔离（高风险）

**目标**：F9 修复 — flag off 时**不**构造 `SchedulerLeaseProposalRepository` 等 5 个 repo，**不** import `scheduler_authority` 模块。

**修改对象**：
- `packages/core_domain/services.py:263-265` — 改为 lazy import + 条件构造
- `packages/core_domain/scheduler_authority.py` — 重命名内部 wording（TD-STRUCT-003），把"authority"语义降级为"local lease arbiter"
- 新增 `tests/test_scheduler_authority_isolation.py` — flag off 时 services 模块的 import time / sys.modules 不含 scheduler_authority

**workflow 侧**：
- task card：`m50/p4_scheduler_isolation.md`
- review_policy：`human_required`

**codex 侧**：implementer

**验收**：
- flag off 启动时 `OrchestratorService.__dict__` 不含 scheduler_authority 字段
- TD-STRUCT-003 标 `partially_repaid` → `repaid`

---

### Phase 5：M50 收口

**验收**：完整 slow 套件 + facade surface ratchet 通过

## 7. M51 — Reality Verification（事实验证）

> **主题**：让"系统说自己能做的"和"系统真实能做的"对齐。
>
> **不解决**的事：不再做新的拆分；不再做新的安全协议。

### Phase 0：capability runtime ledger（高风险）

**目标**：F8 修复 — 实施 GPT Pro 提议的 `capability_invocations` 表。

**修改对象**：
- 新增 SQLite 表 `capability_invocations`（migration）
- `packages/core_domain/capability_plane.py` — `list_capability_health()` 加 `recent_call_summary`（不再固定 0/0）
- 新增 `packages/core_domain/capability_telemetry_service.py` — 写入 receipt + 计算 readiness 状态机（GPT Pro 提议的 5 状态）
- 所有 worker adapter execute 路径加 telemetry hook
- 新增 `tests/test_capability_telemetry.py` — 4 个用例（GPT Pro §capability 测试）

**workflow 侧**：
- task card：`m51/p0_capability_ledger.md`
- review_policy：`human_required`

**codex 侧**：implementer

**验收**：
- 跑一次完整 dogfood 后 `workflowctl capability health` 显示真实 recent_call_summary
- doctor / workbench / router 全部读 ledger 不读 descriptor

---

### Phase 1：scheduler-authority 命名重新审视（中风险）

**目标**：F8 + GPT Pro §P1 — 把 "authority" 这种 overstated 命名重命名为 `LocalSchedulerLeaseArbiter`，并明确 guarantee/non-guarantee。

**修改对象**：
- `packages/core_domain/scheduler_authority.py` → `local_scheduler_lease_arbiter.py`
- 公共 API 添加 deprecated 别名（保 6 个月）
- README + docs 描述 guarantee 边界

**workflow 侧**：task card `m51/p1_scheduler_renaming.md`，`recommended`

**codex 侧**：implementer

**验收**：TD-STRUCT-003 真正 `repaid`

---

### Phase 2：CI + lockfile（中风险）

**目标**：F16 修复 — 让仓库自己证明每日验证。

**修改对象**：
- 新增 `.github/workflows/ci.yml`：跑 `make test-core` + `check_doc_links` + `offline_validation`（在 `--skip-offline-probe` 模式）
- 新增 `uv.lock`（或 `requirements-dev.lock`）
- 新增 `.python-version`：`3.13`
- `pyproject.toml` 修正 dev 依赖版本范围（GPTPRO 提到 pytest 9 vs <9）

**workflow 侧**：task card `m51/p2_ci.md`，`human_required`

**codex 侧**：implementer

**验收**：GitHub PR 上 CI 跑绿；本地 `uv sync` 可复现

---

### Phase 3：M51 收口 + M52 决策

**修改对象**：`docs/milestone_history.md`，全部技术债 close

**M52 决策点**：
- 如果 chat_runtime / CLI / service_interaction 的剩余 P2 仍痛 → 开 M52 收尾这些
- 如果不痛 → 关闭里程碑模式，回到 unbounded local dogfood

## 8. 全局执行规则（4 个 M 通用）

### 8.1 强 dogfood 配置（每个 phase 开始前）

```powershell
$env:WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED="1"
$env:WORKFLOW_DOGFOOD_EXECUTION_BACKEND="codex_cli"
$env:WORKFLOW_DOGFOOD_MODEL="gpt-5.5"
$env:WORKFLOW_DOGFOOD_REASONING_EFFORT="xhigh"
$env:WORKFLOW_CODEX_TIMEOUT_SECONDS="120"
$env:WORKFLOW_WORKSPACE_ROOT="D:\Universal Agentic workflow"  # M49 P0 之后
```

### 8.2 不允许的事

1. **不**在 phase 中插入"顺手再修一下别的"——出现"by the way"立刻拆成新 task card
2. **不**在 phase 失败时把测试改成跳过——必须修代码或撤回 phase
3. **不**在 M 收口前跑 `--run-slow` 跳过红测——红测必须显式记录或修复
4. **不**让 M 编号继续膨胀——M48-M51 是上限；M52 必须有强动机才打开
5. **不**让 codex 直接动 `services.py` 之外的文件——除非 task card 显式声明（防止 implementer 自由发挥扩大 write_set）

### 8.3 异常处理协议

- **codex implementer 失败 3 次** → 自动 fallback 到 shell adapter（项目已有此能力）；如果 shell 也失败 → 转人工
- **测试残留进程** → 中断 + 杀残留 + 清 `state/.pytest-tmp/` + 重跑（M48 P1 后这一步应自动化）
- **patch 出 write_set** → repo_mutation 层应该已经拦截；如未拦截则视为 P0 安全 bug
- **M 编号写错** → 立即停止，先归档现 phase 再开新 M

### 8.4 进度跟踪

每个 phase 完成时：

```bash
workflowctl --db-path state/workflow.db run pr-ready-summary <run_id> > state/m{N}_phase{P}_*/pr_ready_summary.md
workflowctl --db-path state/workflow.db run operator-packet <run_id> > state/m{N}_phase{P}_*/operator_packet.json
```

每个 M 收口时：

```bash
pytest -q --run-slow
python -m infra.scripts.offline_validation --skip-offline-probe
python -m infra.scripts.check_doc_links
```

## 9. 时间预估（参考，非承诺）

| 阶段 | 预估 phase 数 | 预估工作量（你 + codex 协作） |
| --- | :---: | --- |
| M48 Trust Foundation | 4 | 3-5 天 |
| M49 Boundary Hardening | 5 | 1-2 周（OperatorActionReceipt 是大头） |
| M50 Service Decomposition | 6 | 2-3 周（拆分要慢） |
| M51 Reality Verification | 4 | 1 周 |
| **总计** | **19** | **5-7 周** |

> 这是按"个人自用、晚上 + 周末投入"估的。如果工作日全力投入可压到 3-4 周。

## 10. 收尾

### 这份计划相对前几份评估的增量

- **吸收**了三方评估全部 P0/P1（共 12 个）
- **忽略**了三方都提但当前阶段不关键的 P2（如 chat_runtime 拆分、CLI sub-app 化），留给可选 M52
- **新增**：codex / workflow / 人工的明确分工，以及具体到命令行的执行序列
- **新增**：每个 phase 的风险等级、review_policy、verifier 测试

### 第一步该做的事

不是马上开 M48 Phase 0。先做这一件：

1. 你读完这份计划
2. 我（Opus）和你确认每个 M 的边界你都同意
3. **打开 chat workbench**：`uvicorn apps.orchestrator_api.main:app`
4. 把 M48 Phase 0 作为第一张 task card 喂给 workbench
5. 看 codex 实际跑出来的第一个 patch 是否符合预期

如果 M48 Phase 0 这种最低风险任务 codex dogfood 都跑不顺，**整个计划必须重审**。这是你判断"项目能否自己修自己"的第一个真实信号。

### 一句话给你

> **这个项目下一步最值得自豪的事，不是 M48 加了多少新能力，而是 M48-M51 能不能完全用项目自己跑出来。这是 dogfood 从词汇变成事实的唯一路径。**
