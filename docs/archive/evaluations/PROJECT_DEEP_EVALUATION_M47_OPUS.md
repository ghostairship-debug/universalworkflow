# Universal Agentic Workflow OS 深度评估报告（Opus）

- 日期：2026-04-25
- 基线：已接受 `M47`
- 评估前提：个人自用 / 本地 operator runtime
- 评估方式：本地工作树静态分析 + 关键路径动态验证（pytest 子集、doc link 校验、doctor 行为）
- 评估者：Claude Opus 4.7
- 与既有评估的关系：本文不重复 [PROJECT_DEEP_EVALUATION_M37.md](PROJECT_DEEP_EVALUATION_M37.md) 和 [GPTPRO_EVALUATION.md](GPTPRO_EVALUATION.md) 已经讲过的结构性结论，重点放在 **M37→M47 之间真正发生的变化**、**当前阶段新出现或仍未还清的问题** 以及 **下一步可立即执行的修复**

## 0. 一句话总评

> 项目方向仍然成立、个人自用闭环已实质打通；但 **M40-M47 把 8 个里程碑数字主要花在窄向量切片（聊天工作台 + 1010 方块小游戏）上，OrchestratorService 反而比 M38 更大，core_domain 引入了 1206 行"游戏 HTML 模板"，测试可复现性出现新的 Windows 文件锁回归**。下一步该做的不是 M48 的新主题，而是把已经欠下的结构债先收一次。

## 1. 评分（与 M37 评估对比）

| 维度 | M37 评估 | 本次（M47）评分 | 变化原因 |
| --- | ---: | ---: | --- |
| 项目设想合理性 | 8.5 | 8.5 | 个人自用方向不变 |
| 架构基础 | 8.0 | 7.0 | OrchestratorService 反向膨胀，core_domain 出现非领域代码 |
| 实现纪律 | 8.0 | 7.5 | M40+ 的 M 编号膨胀（一些 M 实际只是文档收口）削弱了 milestone 含义 |
| 个人自用成熟度 | 7.0 | 7.5 | 确实跑通了 PDF→artifact 真实闭环、聊天驾驶舱、Codex CLI dogfood |
| 测试可复现性 | — | 5.5 | **本次实测发现 Windows SQLite WAL 锁导致的 29 ERROR 回归** |
| 长期可维护性 | 5.5 | 4.5 | services.py 从 3520 行涨回 3552 行；core_domain 多了 1206 行游戏代码 |
| 外部公开产品化 | — | — | 当前不是目标，不评分 |

**核心趋势**：M37→M47 净结果是 **能力面变宽了，结构面变弱了**。

## 2. M37→M47 真正发生了什么（事实校核）

读完所有活跃文档 + 抽样代码后，把"做了什么"和"声称做了什么"对齐：

### 2.1 真实落地的能力

- **M40：聊天驾驶舱 LLM 化**——`packages/runtime_langgraph/chat_runtime.py` 738 行，覆盖 OpenAI / DeepSeek / MiniMax / Degraded / Fallback 五个 provider；`<think>...</think>` 推理过滤是真实在做的 production-grade 处理（非常关键，MiniMax 模型确实会泄露推理）
- **M41-M42：强 dogfood + 6 个 cluster 角色**——[`packages/worker_adapters/codex_adapter.py`](packages/worker_adapters/codex_adapter.py) 真的接 `codex exec --json --output-last-message`，options-before-prompt + stdin prompt + 进程树 timeout 都已落地
- **M43：PDF→HTML vertical slice**——`examples/block_puzzle_shop/index.html` + `design_trace.md` 是真实可玩游戏；浏览器 smoke 截图存在（`state/m43_block_puzzle_e2e/block_puzzle_shop_smoke.png`）
- **M44/M45：自适应路由 + 动态多集群**——默认关闭，opt-in，符合"先稳定再激进"的克制原则
- **M46：composite cluster graph**——修复了 status detail 只显示首个 cluster 的真实 bug
- **doctor 命令**：`workflowctl doctor` 真的在跑 optional command probe（opencode/codex/claude/mmx/gcloud）+ 环境变量脱敏 + MCP profile 自检

### 2.2 名实不符 / 漂移

| 声称 | 事实 |
| --- | --- |
| README："最新接受基线 M47"，`pytest -q` 通过 | 实测 `376 tests collected`，本次评估扣除三个 slow 文件后 `119 passed + 129 skipped`；连续多次重跑会因为 `state/.pytest-tmp/` 文件锁而出现 29 ERROR（详见 §4） |
| `tech-debt-registry.md` 写 "TD-STRUCT-001 partially_repaid" | M38 P3 收缩后 `services.py` 应为 3520 行；本次实测 **3552 行** ——比 M38 完成态更大。新增的 `chat_llm_runtime` / `chat_control_graph` 都直接挂在 `OrchestratorService.__init__`（参见 services.py:244-245） |
| README 说 dogfood 强模型默认 `gpt-5.5` | `codex_adapter.py:22` 实际默认 `DEFAULT_CODEX_MODEL = "gpt-5.4"`；只有当 `WORKFLOW_DOGFOOD_MODEL=gpt-5.5` 显式设置时才用 gpt-5.5。模型名应该统一在配置一处 |
| 文档治理"活跃真相源 6 个" | `python -m infra.scripts.check_doc_links` 实际只跑 6 个；但根目录还躺着 `GPTPRO_EVALUATION.md` 不在活跃列表，没归档也没在 README 引用——典型的"半归档"状态 |

### 2.3 M40-M47 编号膨胀的代价

milestone_history 显示 M40-M47 的真实"含金量"分布很不均：

- **M40-M43**：含金量大（聊天驾驶舱、强模型 dogfood、cluster 角色补齐、真实 PDF→HTML 闭环）
- **M44-M46**：每个都是单一 feature flag + 一个修复（自适应、动态、composite graph 修复）
- **M47**：纯文档收口

如果按你自己在 user memory 里"M 数已经塌成单 phase closeout"的判断，这是 **结构债的另一种形式**：M 编号是廉价的，导致每次对话都在"再开一个 M"，而真正欠的（OrchestratorService、core_domain 污染、测试可复现性）持续被新主题挤到下一个 M。

## 3. P0 阻塞项（必须在 M48 前面对）

### 3.1 OrchestratorService 反向膨胀（TD-STRUCT-001 实际恶化）

**事实**：

- 本次扫描：[`packages/core_domain/services.py`](packages/core_domain/services.py) **3552 行**
- `OrchestratorService` 类直接定义方法数：**158**（用 `grep -c "^    def "`）
- 加上 4 个 Mixin（Lifecycle 16 + MemorySimulation + Interaction 63 + Projection 14+）和 6 个委派服务（SchedulerAuthoritySupport/OrchestrationExecution/RunLifecycle/ReviewPolicy/AuditReplay/OwnershipLease），公共 facade 暴露的方法数 **超过 230**
- `__init__` 一次性创建：27 个 Repository、9 种 Adapter、6 个子服务、3 个 builder（runtime_gateway/chat_llm_runtime/chat_control_graph）—— 见 services.py:247-359

**为什么这是 P0**：

- M38 自己定的 KPI："`services.py` 从 3833 行减少到 3520 行"——M38 完成时是 3520，**M40-M47 又涨回 3552**。说明 M38 的瘦身**没有形成有效约束**，下一轮新功能仍然回流到这个文件
- 158 个直接定义方法 ≈ 一个超大型类，单类的 cyclomatic complexity 已经无法靠 review 守住
- 任何新能力（M48 想做什么）的最低成本路径仍然是"再加一个方法到 OrchestratorService"

**影响**：

- 中断后重新进入代码的成本继续上涨
- 新人（包括未来的你）很难判断"哪些方法是 facade 应该暴露的，哪些是因为没人拆所以堆这里"
- 测试容易覆盖行为，但难以约束职责边界

### 3.2 core_domain 出现 1206 行非领域代码

**事实**：[`packages/core_domain/local_game_artifacts.py`](packages/core_domain/local_game_artifacts.py) 1206 行，里面包含：

- `_snake_game_html()`：完整贪吃蛇 HTML+CSS+JS 作为 Python 字符串字面量
- `_block_puzzle_shop_html()`（推断同样规模）：1010 方块消除完整 HTML
- `_pdf_paths_for_goal` / `_read_pdf_text`：PDF 解析

**为什么这是 P0**：

- `core_domain` 是项目的领域核心。它应该承载"agent workflow 运行时"的概念——run、phase、task_card、capability、policy、orchestration——而不是"贪吃蛇 HTML 模板"
- M43 vertical slice 的目标是"证明 PDF→HTML artifact 闭环可走通"，已经达成；但**实现路径错了**：游戏 HTML 应该是 worker adapter / artifact builder 的产物，不是核心包的常驻代码
- 这种"为了让 demo 能跑而把 demo 资产塞进核心包"的反模式，会鼓励未来的你继续往 core_domain 塞下一个项目的 HTML（比如 M48 想做扫雷）
- 现在删它会引发 import 链断裂，所以它会一直留下来——这是经典的"窗破效应"

**对比**：`examples/block_puzzle_shop/index.html` 是真正应该存放 HTML 的地方；`design_trace.md` 是真正的 artifact 摘要。问题在于 Python 这一侧的 generator 写在了 core_domain。

### 3.3 测试可复现性回归（Windows SQLite WAL 锁）

**事实**：本次评估实际操作过程中，`pytest -q` 出现两类失败：

1. **后台 pytest 进程残留**（PID 75556，由 anaconda3/python.exe 持有 SQLite WAL 文件 `state/.pytest-tmp/test_orchestration_rejects_fai0/workflow.db-wal`）。它的写锁挡住了任何后续 `pytest` 启动时的 `tmp_path` cleanup，连续 29 个 ERROR
2. 即使在主进程退出后，`state/.pytest-tmp/` 目录里残留了 **212+ 个上次的 tmp 子目录**，部分仍被 SQLite shared 锁住

**根因诊断**：

- 测试用 `tmp_path_factory` 创建 SQLite db，但 SQLite WAL 模式在 Windows 上 **进程退出 ≠ 锁释放**——必须显式 `connection.close()` + checkpoint
- conftest.py（25 行）只配置 slow marker，**没有 session-scope cleanup fixture**
- M42 已经为 codex.exe 添加了进程树 timeout 清理（TD-CODEX-PROCESS-001 已偿还），但同样的"Windows 子进程不干净"在 pytest 自身的 SQLite 连接上**没有等价保护**

**为什么这是 P0**：

- 这正是 GPTPRO_EVALUATION 当时给出"测试不全绿"判断的根因——它不是代码错，是基础设施错
- 个人自用最该信任的就是"我跑一下 pytest 看绿不绿"。如果它每三次有一次因为环境问题而显红，"绿"作为信任锚会失效
- 你自己 `tech-debt-registry` 中 TD-DOGFOOD-001 提到"声称完整 dogfood 已生产可用"——同样的逻辑，**测试可复现性也是声称的一部分**

## 4. P1 重要问题（M48-M49 应处理）

### 4.1 cluster_router 是关键词字面量匹配

[`packages/core_domain/cluster_router.py`](packages/core_domain/cluster_router.py) 178 行，全部由硬编码中英文 marker 集合驱动：

```python
architecture_markers = {"architecture", "architect", "claude", "dogfood", "m41", "架构", "能力层", "自开发"}
multimodal_markers = {"multimodal", "pdf", "image", ..., "多模态", "图片", "截图", "设计稿"}
# ... 共 8 组 markers
```

**问题**：

- 加新 cluster 必须改这个文件（违反 OCP）
- "m41" 作为 marker 写死——M41 已经过去 6 个里程碑，这个 marker 是历史遗留
- 没有 telemetry：实际命中率不可观测，TD-STRUCT-005（capability health 仍 descriptor-based）的另一面体现
- 中文 marker 的覆盖度由我（人）拍脑袋决定，不是任何评估的产物

**优化路径**：把 marker dict 提到 `infra/seeds/cluster_routing.yaml`，每次匹配记一个 `cluster_route_decision` 事件到 SQLite，30 天后用真实数据反向调权。这同时偿还 TD-STRUCT-005 的一部分。

### 4.2 chat_runtime.py 738 行单文件

`runtime_langgraph/chat_runtime.py` 把 5 个 LLM provider + reasoning markup filter + builder 全压在一个文件：

- `MiniMaxChatLLMRuntime` 继承 `DeepSeekChatLLMRuntime` 只多一个 `suppress_reasoning_markup=True` 参数 —— **不是父子关系**，是兄弟关系，应该共同继承一个 `OpenAICompatibleChatLLMRuntime` 基类
- `_strip_reasoning_markup` / `_iter_visible_text_deltas` 是 MiniMax 特有的 `<think>` 处理，但写在通用 helper 区域
- `build_chat_llm_runtime_from_env` 一个函数读 9 个环境变量，分支多达 4 层

**优化路径**：拆 `runtime_langgraph/chat_runtime/{base.py, openai.py, openai_compatible.py, deepseek.py, minimax.py, fallback.py, reasoning_filter.py, builder.py}`。注意：**保持包路径不动**（`from packages.runtime_langgraph.chat_runtime import ...`），只在 `__init__.py` re-export。

### 4.3 CLI main.py 1535 行 60+ 命令

[`apps/operator_cli/main.py`](apps/operator_cli/main.py) 单文件挂着所有 typer 命令。命令族明显可分（`preset_*` / `domain_pack_*` / `capability_*` / `interaction_*` / `run_*` / `governance_*` / `db_*` / `scheduler_*` / `memory_*`），但目前都共用顶层 typer.Typer。

**优化路径**：每族抽 `apps/operator_cli/commands/{run.py, interaction.py, ...}`，main.py 只做 `app.add_typer(...)`。

### 4.4 service_interaction.py 2315 行 Mixin

`InteractionServiceMixin` 包含 chat / session / generated_profiles / watchdogs 四类职责。`post_chat_message`(974) `confirm_chat_action`(1048) `build_interaction_stream_events`(1155) `generate_session_profiles`(1883) `evaluate_watchdogs`(1978) —— 这些应是**四个独立子服务**，目前共享一个 mixin 只为方便 `self.foo`。

### 4.5 scheduler-authority 没有真隔离

`packages/core_domain/scheduler_authority.py` 1646 行，TD-STRUCT-003 仍 partially_repaid。你已经决定"个人自用，云/分布式 deferred"，但代码层面：

- `OrchestratorService.__init__` **无论 flag 是否打开都会构造** `SchedulerLeaseProposalRepository` / `SchedulerLeaseDecisionRepository` / `SchedulerPeerHeartbeatRepository`（services.py:263-265）
- 只是 `scheduler_authority_cluster` 这个对象在 flag off 时换成 `NullSchedulerAuthorityCluster`
- 真正"isolated/feature-flagged off"应该让 init 时不构造这些 repo，import 时不 import scheduler_authority 模块

**影响**：每次 OrchestratorService 启动都要 import 1646 行的 scheduler_authority + 3 个 repo，即便永远用不到。

### 4.6 README ↔ 代码事实漂移

- `pytest -q` 数字没更新（README 没数字、`docs/current_development_workflow.md` 在历史描述里说 `299 passed`，实际 376 collected）
- `gpt-5.5` 默认值漂移（前文已述）
- `M38_REPAIR_AND_DEVELOPMENT_PLAN.md` 仍是"活跃真相源"之一，但其实 M38 已收口；它现在的角色是**历史评估**，应该和 GPTPRO_EVALUATION 一起归档

## 5. P2 设计/治理问题（不阻塞，但应记入登记表）

1. **examples/local_task_cards/** 只有一个 `01_safe_doc_patch.md`——README 推销 task-card 闭环，但样例库实际只有一个示例。如果这个闭环是核心卖点，至少给 5-10 个跨场景任务卡（patch / artifact / review-only / multimodal / failure-recovery）
2. **doctor 命令是只读，没有 `--strict` 模式**，无法挂在 pre-commit / CI 入口。建议加 `workflowctl doctor --strict`：任何 issue 即非零 exit
3. **没有依赖锁文件提交**（`pyproject.toml` 用 caret 范围，`.lock` 不在 git）。GPTPRO 当时撞到"环境 pytest 9 vs <9"的真实坑，应锁
4. **测试目录 mirror 已经存在**（`tests/contracts/` `tests/core_domain/` `tests/apps/` `tests/worker_adapters/`），但根 tests 下还有 `test_api.py` 2210 行 / `test_cli.py` 2149 行 / `test_execution_loop.py` 3344 行——**镜像化只走了一半**，大文件还在根
5. **GitHub 集成实际状态**——README 说 "git commit/push/PR 必须先确认"，但代码里没看到 `gh` CLI 或 `pygithub` 接入；走的是 `ShellAdapter` 单进程 git。这意味着创建 PR 实际仍是手工——这没问题（个人自用），但文档应该说清楚

## 6. M48 推荐主题（**不要做新能力**）

> 主题：**结构债收口（Structural Debt Closeout）**

明确不做：

- 不做新 cluster 类型
- 不做新 LLM provider 接入
- 不做新 dogfood 路径
- 不开 M44/M45 的 default-on
- 不开 GitHub 自动 PR

应做（按优先级排）：

### Phase 0：基线对齐
- 把本报告的发现转成 `state/workflow.db` 中的 phase + task cards
- 删除/归档 `M38_REPAIR_AND_DEVELOPMENT_PLAN.md` 和 `GPTPRO_EVALUATION.md` 到 git 历史，根目录只保留本报告（`PROJECT_DEEP_EVALUATION_M47_OPUS.md`）+ `PROJECT_DEEP_EVALUATION_M37.md`（前任评估）
- README 实测数字校对：`pytest -q --collect-only` 报告测试数；`grep -c` 报告 services.py 行数；这些数字写到 README 一节"当前实测"

### Phase 1：测试可复现性硬化（先做，因为不做这一步后续 phase 都在沙堆上）
- conftest.py 加 session-scope autouse fixture：
  - 启动前清理 `state/.pytest-tmp/`（带 retry + 残留 PID 报告）
  - 启动前 grep `python.exe` / `codex.exe`，列出可疑残留（不杀，只警告）
  - 每个 SQLite db 强制 WAL checkpoint 后再 close
- 验收：连续跑 `pytest -q` 5 次，0 个 ERROR

### Phase 2：core_domain 去污染
- `local_game_artifacts.py` 移到 `examples/_generators/` 或拆 `packages/contributions/games/`
- 只保留 PDF 抽取在 `core_domain`（这部分确实是领域能力）
- 验收：`packages/core_domain/` 总行数下降 ≥ 800

### Phase 3：OrchestratorService 收缩 v2（M38 已经做过 v1）
- 加冻结测试 `tests/test_orchestrator_facade_surface.py`：
  ```python
  # 当前 158 个直接方法是上限，向下不能涨
  assert len(direct_methods(OrchestratorService)) <= 158
  ```
- 立即把 `chat_llm_runtime` / `chat_control_graph` 从 `OrchestratorService.__init__` 抽到 `ChatService`
- 把 27 个 repository 实例分成 6-8 个 Repository Bundle（RunBundle / TaskBundle / SchedulerBundle / RuntimeBundle / MemoryBundle / ChatBundle / GovernanceBundle）
- 验收：services.py ≤ 3000 行；冻结测试上限改为 130

### Phase 4：scheduler-authority 真隔离
- flag off 时**不**构造 SchedulerLease* repo / 不 import scheduler_authority
- 加 `tests/test_scheduler_authority_isolation.py`：当 flag off 时 services 模块的 import time 和 memory delta 显著低于 flag on
- 验收：local-only 模式启动后 `OrchestratorService.__dict__` 不含 scheduler_authority 相关字段

### Phase 5：路由可观测
- `cluster_router.py` 把 markers 提到 `infra/seeds/cluster_routing.yaml`
- 每次 `suggest_template_ids` 写一个 SQLite 事件
- 加 `workflowctl run cluster-routing-stats`：列出最近 30 天的 cluster 分布
- 验收：M44/M45 的 default-on 决定能基于真实数据，而不是直觉

## 7. 不建议做的事

1. **不要做 OrchestratorService 大重构**（一次性切成 micro-services）。冻结测试 + 渐进抽取比一次大手术稳得多；你之前 M2M 一轮已经验证过这点
2. **不要再开 M48 之前再起一个新评估文件**。本评估 + M37 评估两份足够，再加只会再次形成"半归档"漂移
3. **不要把 M44/M45 改成 default-on**。先收 30 天 telemetry。"opt-in 是刻意选择"是你自己 docs 里写的克制，应该被尊重
4. **不要把这次 PR-ready summary 路径接到自动 push**。`pr_ready_summary` 当前是 artifact，加 push 自动化前必须先把"测试可复现性"这一格补回到稳态

## 8. 评估方法附录

本次评估实际跑过的命令：

```bash
# 静态规模
find packages apps tests -name "*.py" | xargs wc -l | sort -rn | head -40
grep -c '^    def ' packages/core_domain/services.py            # 158
grep -c '^    def ' packages/core_domain/service_interaction.py # 63
grep -c '^    def ' packages/core_domain/service_lifecycle.py   # 16

# 动态验证
python -m pytest --collect-only -q                              # 376 tests collected
python -m infra.scripts.check_doc_links                         # 0 issues, 6 docs
python -m pytest -q --tb=no \
  --ignore=tests/test_execution_loop.py \
  --ignore=tests/test_release_closeout.py \
  --ignore=tests/test_web_ui.py                                 # 119 passed, 129 skipped, 1:33

# 异常诊断
python -m pytest tests/test_doctor.py -q --tb=short
# → 29 ERROR：PermissionError [WinError 32]: SQLite WAL 锁
# → 根因：上次中断的 pytest（PID 75556）持有 state/.pytest-tmp 下的 db-wal
# → 验证：清理 + Stop-Process 后重跑通过
```

代码读取覆盖：

- `packages/core_domain/{services, repositories, service_interaction, service_lifecycle, service_projection, repo_mutation, cluster_router, local_game_artifacts}.py`
- `packages/runtime_langgraph/chat_runtime.py`
- `packages/worker_adapters/{codex_adapter, langchain_agent_adapter}.py`
- `apps/{operator_cli/main, orchestrator_api/main}.py`
- 全部活跃文档（README、current_development_workflow、milestone_history、tech-debt-registry、tech_debt_registry.json、M38 计划、M37 评估、GPTPRO 评估）
- `examples/block_puzzle_shop/{index.html, design_trace.md, README.md}`
- `state/` 真实 smoke artifact 列表

未覆盖（不影响结论）：

- web_ui.py 1398 行的 UI 模板细节
- runtime_langgraph/gateway.py
- contracts/models.py 1377 行的 Pydantic 模型
- tests/ 内部断言细节（只看了 collection 数和运行结果）
- infra/migrations/ SQL 演化

## 9. 一句话给你

> 你不缺新的 milestone 主题，你缺一次"把已经会用、已经依赖、已经欠的"全部收一次的 phase。M48 应该叫 **`Structural Debt Closeout`**，不该叫 M48。
