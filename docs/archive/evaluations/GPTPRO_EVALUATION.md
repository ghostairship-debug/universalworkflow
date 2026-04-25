## 评估范围

我按“个人本地 operator runtime”来评估，而不是按 SaaS、多用户平台、插件市场来评估。这个定位是仓库 README 明确写出的：项目目标是本地 agentic workflow runtime，强调稳定、可恢复、可审计，当前入口包括 CLI/API/Web console `/ui/workbench`，最新接受基线为 M47。([GitHub][1])

本报告是基于 GitHub 仓库静态审阅、仓库文档、源码结构，以及 OWASP/FastAPI/LangGraph/Python packaging 等公开文档做的深度挑刺；我没有在本地 clone 后运行完整 `pytest`、真实 LLM provider、真实 repo mutation 或浏览器端交互。

---

# 总体判断

这个库已经不是“玩具项目”。它有明确的本地优先定位、阶段性文档制度、CLI/API/UI 多入口、较宽的测试面、repo mutation 安全收口、chat 侧高风险确认卡，以及 scheduler lease/callback 校验等工程化痕迹。仓库 README 也把每日验证收敛到 doc link、offline validation、`pytest -q`，并把 slow tests 放到 milestone closeout，这对个人项目来说是务实的节奏。([GitHub][1])

但当前最大风险也很清楚：**系统已经进入“能驱动真实行动”的阶段，但安全边界、服务边界、能力真实性、运行时遥测还没有完全跟上。** 换句话说，功能表面已经足够大，下一阶段最该做的不是继续加入口或 provider，而是关闸、减面、固化事实来源。

我给一个偏工程实战的评分：

| 维度            |     评分 | 判断                                                    |
| ------------- | -----: | ----------------------------------------------------- |
| 产品定位清晰度       |   8/10 | “本地 operator runtime，不做 SaaS”这个边界很健康                  |
| 架构完整度         |   7/10 | 模块很多，概念齐全，但中央 facade 仍然过大                             |
| 当前可维护性        | 5.5/10 | 文档和测试在帮忙兜底，但 `OrchestratorService`/Web UI 有继续膨胀风险     |
| 安全闭环          |   6/10 | repo mutation 和 chat confirmation 做得不错；API 级别还需要硬闸    |
| 可观测性/能力真实性    |   5/10 | 有 descriptor 和 milestone 记录，但缺真实 runtime telemetry 闭环 |
| dogfood/本地可用性 |   7/10 | 测试、state 隔离、文档制度不错；Python 3.13+ 与缺 CI 会增加摩擦           |

---

# 已经做对的地方

## 1. 项目定位没有过度膨胀

README 明确排除了 SaaS、多用户 onboarding、插件市场等目标，把当前目标限定为个人本地 runtime。这是很重要的，因为它避免了过早平台化，也让安全模型可以围绕“本机 operator”设计，而不是一开始就背上企业级多租户复杂度。([GitHub][1])

## 2. repo mutation 当前已经有比较实在的安全收口

`repo_mutation.py` 里能看到路径规范化、workspace 越界拒绝、危险命令 denylist、测试命令解析、`subprocess.run(..., shell=False)`、timeout、受控环境变量等机制。这一点值得肯定：M38 文档里提到的历史 shell 风险，当前代码层面已经明显修过。([GitHub][2])

## 3. chat 侧高风险确认卡已经有雏形

仓库 README 说 chat 可以触发 workflow，但 `resume`、`approve`、`reject`、`cancel`、`launch_execute`、repo mutation、git commit/push/PR 等必须确认；源码里也能看到 `requires_confirmation`、pending confirmation、confirm/decline marker、high-risk action confirmation card 这类实现。这个方向是对的。([GitHub][1])

## 4. scheduler lease/callback 校验不是摆设

服务里已经有 active committed lease、handoff、callback scheduler context、stale control plane / lease mismatch 等校验逻辑。这说明项目不只是“调度器名词堆砌”，而是真的在处理 long-running workflow 的控制面一致性问题。([GitHub][3])

## 5. 文档制度和测试面已经形成阶段性资产

仓库有 `docs/current_development_workflow.md`、milestone history、tech debt registry、M-level 计划/总结等文档；测试目录覆盖 API、CLI、governance、execution loop、runtime boundary、scheduler authority、web UI、worker adapters 等多类场景。这对后续重构非常有价值，因为你不是在裸奔。([GitHub][4])

---

# 关键问题与挑刺

## P0：API 级高风险动作没有形成与 chat confirmation 同等强度的硬边界

这是我认为当前最需要优先处理的问题。

文档已经定义了高风险动作必须确认，chat 侧也有 confirmation card；但 API router 暴露了 `/runs/launch`、`/runs/{run_id}/resume`、`approve`、`reject`、`compile` 等 mutating endpoint，并且 request model 里有 `execute: bool = False`、adapter/model overrides、`write_set`、`read_set`、`test_commands`、`mutation_mode` 等能力。静态看 router 层没有看到统一的认证/确认 dependency。([GitHub][5])

这在本地 127.0.0.1 模型下不是传统公网漏洞，但仍然有实际风险：浏览器可以被恶意页面诱导向本地服务发起 state-changing request。OWASP 对 CSRF 的核心描述正是“诱导已认证用户浏览器执行不想要的状态改变操作”，并建议对 state-changing request 使用 token、custom header 等防御。([OWASP Cheat Sheet Series][6])

**建议：把“确认”从 UI/chat 概念升级成 API 层强制的 `OperatorActionReceipt`。**

建议新增一张表或等价结构：

```text
operator_action_receipts
- receipt_id
- action_type              # launch_execute / resume_run / approve_review / reject_review / cancel_run / repo_mutation / git_push ...
- run_id
- session_id
- scope_hash               # 对 execute/write_set/test_commands/mutation_mode/task_card_ref 等做 hash
- created_at
- expires_at
- consumed_at
- created_by_surface       # chat / web_ui / cli
- rationale
```

所有高风险 POST 必须带：

```http
X-Workflow-Operator-Token: ...
X-Workflow-Action-Receipt: ...
```

后端校验：

1. receipt 存在；
2. action_type 匹配；
3. run_id/session_id 匹配；
4. request body 的关键字段 hash 匹配；
5. 未过期；
6. 未被消费；
7. 消费后不可重放。

FastAPI 本身支持通过 dependency 注入 bearer token/security scheme，这种模式可以直接放在 router dependency 中实现，不需要把安全逻辑散落到业务代码里。([FastAPI][7])

**验收测试：**

```text
POST /runs/launch execute=true without receipt -> 401/403
POST /runs/{id}/resume without receipt -> 401/403
wrong action_type receipt -> 403
expired receipt -> 403
reused receipt -> 403
receipt scope_hash 与 write_set/test_commands 不一致 -> 403
GET /runs/{id}/status 不需要 receipt
Web UI confirmation card 生成 receipt 后，POST 成功
```

---

## P0/P1：`OrchestratorService` 仍然是最大结构性风险

tech debt registry 已经把 `TD-STRUCT-001` 记录为未还清：`OrchestratorService` 是 large facade，存在 cross-plane wiring/helper 问题，会阻碍 honest service boundary 和安全抽取。源码也印证了这一点：`packages/core_domain/services.py` 大约 3500+ 行，`OrchestratorService` 的 `__init__` 同时装配 repositories、runtime/chat/control/adapters/capability/domain/simulation/trace/worker_scheduler/support services。([GitHub][3])

这类 facade 的问题不是“文件长”本身，而是它会造成三个后果：

第一，安全策略容易绕过。比如 chat 层、API 层、CLI 层都调用同一个大服务时，哪些动作需要 receipt、哪些只是 read-only，很容易靠约定而不是类型/边界保证。

第二，测试会越来越像集成测试。一个小 use case 需要构造半个系统，最后大家倾向于 mock 大对象，导致测试不再能证明真实边界。

第三，后续引入更多 provider、scheduler、worker、UI action 时，所有东西都会继续往这个服务里塞。

**建议拆法：不要一口气重写，而是做“绞杀式拆分”。**

保留 `OrchestratorService` 作为兼容 facade，但新增内部 use-case service：

```text
OrchestratorCompositionRoot
  只负责 wiring，不放业务逻辑

RunLifecycleService
  create_run / launch_goal / resume / cancel / status

InteractionCommandService
  chat intent -> action proposal -> confirmation receipt

OperatorActionGuard
  判断 action risk、生成/消费 receipt、做 API 硬闸

MutationSafetyService
  write_set/read_set/test_commands/mutation_mode 归一化与安全判定

CapabilityRoutingService
  provider/model/adapter readiness、fallback、degraded decision

SchedulerLeaseService
  lease acquire/commit/handoff/callback validation

ProjectionQueryService
  timeline/replay/summary/status 只读查询
```

并加一个机械约束：**`services.py` 不再新增非 delegation 方法。** 每个 milestone 设 LOC ratchet，例如：

```text
M48: services.py < 3200 LOC
M49: services.py < 2600 LOC
M50: services.py < 2000 LOC
```

---

## P1：能力健康状态还是“描述符可信”，不是“运行时事实可信”

tech debt registry 里 `TD-STRUCT-005` 写得很直白：capability health 现在是 descriptor-based，没有完整 runtime telemetry，会阻碍可信 capability readiness 和 routing decision。([GitHub][8])

这和 milestone history 中对 MMX/Claude 的表述也能对上：M41 记录里仍然提到 MMX/Claude 是 degraded/fallback，还不是 fully productized。([GitHub][9])

当前阶段最怕的是 UI 或 router 显示“Claude/MMX/Vertex 可用”，但真实调用其实没跑过、只跑过 fallback、或者凭 descriptor 推断。这会让 operator 错误判断系统能力。

**建议新增 runtime capability ledger。**

最小表结构：

```text
capability_invocations
- id
- provider             # openai / anthropic / vertex / mmx / noop ...
- adapter
- model
- role                 # planner / executor / reviewer / multimodal / repair ...
- run_id
- task_id
- started_at
- duration_ms
- status               # success / failed / timeout / skipped / fallback
- error_kind
- error_message_hash
- artifact_refs
- smoke_test_id
```

再定义 readiness 状态：

```text
verified_recently   最近 N 天真实成功
stale               曾经成功，但超过 N 天
degraded            fallback 成功，primary 失败
unverified          只有 descriptor，没有真实调用
disabled            配置缺失或用户关闭
```

UI/workbench、doctor、router 都只读这个 ledger，不直接相信 descriptor。这样“能力”从声明变成事实。

---

## P1：scheduler-authority 命名仍然过强

tech debt registry 里 `TD-STRUCT-003` 指出 scheduler-authority legacy naming overstates consensus，会影响 operator 对系统保证的理解。([GitHub][8])

我赞同这个判断。当前代码里 lease/callback validation 已经挺认真，但“authority”这个词会让人误以为有分布式一致性、leader election、quorum、fencing token 全套语义。实际上，如果当前主要是本地 DB/单机 lease arbitration，就应该在 UI/API/docs 里明确叫：

```text
Local Scheduler Lease Coordinator
```

或者：

```text
Scheduler Lease Arbiter
```

把 guarantees 写清楚：

```text
保证：
- 单 store 下的 lease/fencing 校验
- stale callback 拒绝
- committed lease/handoff 校验

不保证：
- 多节点强一致 consensus
- quorum election
- 网络分区安全
- exactly-once side effect
```

这不是文字洁癖。对 agentic runtime 来说，operator 对系统保证的误解，本身就是安全风险。

---

## P1：workspace root 依赖 `Path.cwd()`，容易在真实使用中指错根目录

`OrchestratorService` 里 `_workspace_root` 返回 `Path.cwd().resolve()`。repo mutation 层本身有路径越界保护，但如果“根”本身由当前启动目录决定，那么启动位置错了，安全边界和写入边界就会整体偏移。([GitHub][3])

这在本地工具里很常见：你以为 operator 正在管理 repo A，实际 uvicorn 从父目录、home 目录或另一个 workspace 启动。路径校验仍然通过，但校验的是错误 workspace。

**建议：workspace root 必须显式配置，不应隐式取 cwd。**

优先级建议：

```text
1. CLI/API 启动参数 --workspace-root
2. 环境变量 WORKFLOW_WORKSPACE_ROOT
3. workflow.toml
4. 最后才允许 cwd，并在 UI 上用红色/黄色标记“implicit cwd root”
```

所有 repo mutation、task card path、write_set/read_set 都基于这个 root canonicalize。高风险 action receipt 的 `scope_hash` 也必须包含 workspace root fingerprint。

---

## P1：API app import-time 初始化/迁移有副作用风险

`apps/orchestrator_api/main.py` 里 `create_app()` 会 resolve DB path、执行 `migrate(resolved_db_path)`、创建 `OrchestratorService`，文件底部还有 `app = create_app()`。这会导致导入模块时就可能发生 DB 迁移和服务初始化。([GitHub][10])

这对本地项目不是灾难，但会影响：

```text
- 测试隔离
- 多 app instance
- 静态分析/文档导入
- future worker/subprocess 模式
- “只想 import schema，不想碰 state”的场景
```

**建议：迁移和 service 初始化移入 lifespan/startup 或 CLI 显式步骤。**

理想结构：

```python
def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI()
    app.state.settings = settings or load_settings()
    register_routes(app)
    return app

@asynccontextmanager
async def lifespan(app: FastAPI):
    migrate(app.state.settings.db_path)
    app.state.service = build_service(app.state.settings)
    yield
    app.state.service.close()
```

同时让测试可以注入 temp DB、fake service、fake workspace root。

---

## P1：Web UI 是单文件手写 HTML/CSS/JS，已经接近维护拐点

`apps/orchestrator_api/routers/web_ui.py` 大约 1300+ 行，里面有大量 HTML/CSS/JS 字符串。好消息是当前能看到 `_escape`、`_json_block` 这类 escaping 处理，不是完全裸拼。坏消息是这个文件继续增长后，XSS、防重放、按钮权限、confirmation receipt、状态渲染都会变得难测。([GitHub][11])

**建议下一阶段不要急着换前端框架，先做模板拆分：**

```text
apps/orchestrator_api/templates/workbench/
  base.html
  run_detail.html
  confirmation_card.html
  capability_panel.html
  timeline.html

apps/orchestrator_api/static/workbench/
  workbench.js
  workbench.css
```

同时加三类测试：

```text
- HTML snapshot test：关键按钮和 data-action 是否存在
- XSS regression：run title / task title / error message 注入 <script> 时必须被 escape
- action permission test：没有 receipt 的高风险按钮只展示 confirm，不直接 POST
```

再加一个基础 CSP：

```http
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'
```

---

## P1：文档事实源仍然有“历史文档被 active 引用”的混淆

README 和 current workflow 都把 M38 plan、M37 report 放在 active truth source 列表里；但 M38 文档自己又写明它是 completed historical record，阶段章节保留历史计划，不再代表当前未完成任务。([GitHub][1])

这不是 P0，但会让人和 agent 都误读状态。尤其这个仓库已经把“DB 是主记录、Markdown 只是总结/少数 active docs”写进 current workflow，那么 active truth source 应该更窄。([GitHub][4])

**建议改成两层：**

```text
Active truth sources:
- README.md
- docs/current_development_workflow.md
- docs/milestone_history.md
- docs/tech_debt_registry.md
- docs/tech_debt_registry.json

Historical inputs:
- M38_REPAIR_AND_DEVELOPMENT_PLAN.md
- PROJECT_DEEP_EVALUATION_M37.md
```

再加一个文档一致性测试：

```text
- README latest baseline == current_workflow latest baseline == milestone_history latest baseline
- active truth source 不允许包含 status=completed historical record 的文档
- tech_debt_registry.md 与 tech_debt_registry.json 的 unpaid IDs 一致
```

---

## P1/P2：Python `>=3.13` 是可接受但有摩擦的选择

`pyproject.toml` 要求 `requires-python = ">=3.13"`，依赖包括 FastAPI/OpenAI/Pydantic/Rich/Typer/Uvicorn，optional deps 里还有 LangChain/LangGraph/MCP。([GitHub][12])

这不是错误。项目是个人本地 runtime，作者完全可以选择最新 Python。但它会让跨机器 dogfood、CI、临时容器、未来协作者复现变难。Python packaging 文档也明确 `pyproject.toml` 是现代项目元数据和构建系统配置入口，`requires-python` 会映射到包元数据里的 Python 版本要求。([Python 打包指南][13])

**建议二选一：**

方案 A，继续 3.13+，但补齐 reproducibility：

```text
.python-version
uv.lock 或等价 lockfile
README 明确推荐安装方式
CI matrix 至少跑 3.13
```

方案 B，降到 3.12+，提高可用性：

```text
requires-python = ">=3.12"
CI 跑 3.12 / 3.13
只在确实用到 3.13 特性时保留 3.13+
```

---

## P2：LangGraph optional dependency 需要和 durable execution 语义对齐

项目 optional dependency 里有 `langgraph`，源码里也有 `runtime_langgraph` 包。LangGraph 官方文档强调 persistence/checkpointer、thread id、durable execution、fault tolerance、human-in-the-loop、time travel 等能力；durable execution 还要求 side effect/non-determinism 处理得足够谨慎。([GitHub][12])

如果项目未来要把 LangGraph 当成真实运行时，而不是 demo adapter，需要明确：

```text
- 每个 workflow/run 是否都有稳定 thread_id
- checkpoint 与本项目 workflow.db 的关系
- side effect 是否先记录 intent，再执行，再记录 result
- resume/replay 是从 workflow.db 驱动，还是从 LangGraph checkpoint 驱动
- 两套状态源冲突时谁是权威
```

否则会出现“双状态源”问题：workflow.db 认为 run 在 A 状态，LangGraph checkpoint 认为在 B 状态。

---

## P2：没有看到 releases/CI 形成外部可验证基线

GitHub 页面显示当前没有 published releases；根目录文件树也没有明显展示 `.github/workflows`。考虑到 README 已经写了 M47 baseline 和每日验证命令，下一步很自然是让仓库自己在 push/PR 上证明这些验证。([GitHub][1])

建议最小 CI：

```yaml
python -m pip install -e ".[dev]"
pytest -q
python scripts/validate_doc_links.py
python scripts/offline_validation.py
```

如果 slow tests 很慢，可以只在手动 workflow 或 milestone tag 上跑。

---

# 建议的修改优先级

## 第一优先级：关 API 高风险动作硬闸

目标：任何能执行、恢复、审批、拒绝、取消、写 repo、跑测试命令、触发 mutation 的 API，都不能只靠“UI 上有确认按钮”来保护。

交付物：

```text
- OperatorActionReceipt model/table
- require_operator_action FastAPI dependency
- X-Workflow-Operator-Token
- X-Workflow-Action-Receipt
- single-use/TTL/scope_hash 校验
- Web UI/chat confirmation card 生成 receipt
- CLI 显式确认后生成 receipt
- 高风险 POST 未带 receipt 全部 401/403
```

这件事应该排在继续加 provider、继续扩 UI、继续拆小功能之前。

---

## 第二优先级：固定 workspace root

目标：repo mutation 的安全边界不再取决于当前进程从哪里启动。

交付物：

```text
- settings.workspace_root
- CLI/API 启动参数
- WORKFLOW_WORKSPACE_ROOT
- UI 顶部显示当前 workspace root
- implicit cwd root 显示 warning
- write_set/read_set/task_card_path 全部 canonicalize
- receipt scope_hash 包含 workspace root fingerprint
```

---

## 第三优先级：把 `OrchestratorService` 变成 facade，而不是系统本体

目标：未来所有新增行为不得继续塞进 `services.py`。

第一刀建议从安全和只读查询切：

```text
OperatorActionGuard
ProjectionQueryService
MutationSafetyService
```

这三块拆出来后，API router 会更清楚：哪些 endpoint 是 read-only，哪些 endpoint 必须带 receipt，哪些 endpoint 会触碰 repo。

---

## 第四优先级：能力健康改成 runtime ledger

目标：UI/doctor/router 不再说“某 provider 应该可用”，而是说“它最近真实成功/失败/降级/未验证”。

交付物：

```text
- capability_invocations table
- provider smoke run command
- readiness state machine
- Workbench capability panel
- degraded/fallback 明确展示
- router 基于 readiness 决策
```

---

## 第五优先级：Web UI 模板化 + CSP + XSS 回归测试

目标：先不追求漂亮，先追求可维护、可测试、不容易把安全按钮写错。

交付物：

```text
- templates/static 拆分
- confirmation_card 组件
- no-receipt no-high-risk-post 测试
- HTML escaping snapshot
- CSP header
```

---

# 建议新增的测试清单

## 安全边界测试

```text
test_launch_execute_requires_receipt
test_resume_requires_receipt
test_approve_review_requires_receipt
test_reject_review_requires_receipt
test_cancel_run_requires_receipt
test_repo_mutation_requires_receipt
test_receipt_single_use
test_receipt_scope_hash_mismatch_rejected
test_receipt_workspace_root_mismatch_rejected
test_malicious_origin_rejected_or_requires_custom_header
```

## workspace 测试

```text
test_workspace_root_from_config_not_cwd
test_absolute_write_set_outside_workspace_rejected
test_task_card_path_outside_workspace_rejected
test_implicit_cwd_workspace_warns
```

## capability 测试

```text
test_successful_provider_call_records_invocation
test_failed_provider_call_records_error_kind
test_fallback_marks_degraded_not_verified
test_stale_capability_not_routed_as_ready
```

## 架构防回退测试

```text
test_services_py_loc_ratchet
test_no_new_high_risk_route_without_operator_guard
test_active_truth_sources_do_not_include_historical_completed_docs
```

## UI 测试

```text
test_workbench_escapes_run_title
test_workbench_escapes_error_message
test_high_risk_button_opens_confirmation_not_direct_post
test_confirmation_receipt_consumed_after_post
```

---

# 结论

这个项目当前最值得肯定的是：**方向很清楚，已经有足够多的真实工程痕迹，不是概念玩具。** repo mutation 安全修复、chat confirmation、scheduler lease 校验、测试面、文档制度都说明它已经进入可持续 dogfood 的阶段。

但下一阶段的主线应该从“扩功能”切换到“关边界、还债、让事实可验证”：

```text
1. API 高风险动作必须强制 receipt/token
2. workspace root 必须显式化
3. OrchestratorService 必须停止膨胀
4. capability readiness 必须来自真实 telemetry
5. Web UI 必须从单文件字符串渲染走向可测试组件
6. active truth source 必须收窄，历史文档归档化
```

我会把最优先的修改建议压缩成一句话：

**先把 operator action confirmation 做成后端不可绕过的安全协议，再拆 `OrchestratorService`，然后用 runtime telemetry 替代 capability descriptor 的“自我声明”。**

[1]: https://github.com/ghostairship-debug/universalworkflow "GitHub - ghostairship-debug/universalworkflow · GitHub"
[2]: https://github.com/ghostairship-debug/universalworkflow/blob/main/packages/core_domain/repo_mutation.py "universalworkflow/packages/core_domain/repo_mutation.py at main · ghostairship-debug/universalworkflow · GitHub"
[3]: https://github.com/ghostairship-debug/universalworkflow/blob/main/packages/core_domain/services.py "universalworkflow/packages/core_domain/services.py at main · ghostairship-debug/universalworkflow · GitHub"
[4]: https://github.com/ghostairship-debug/universalworkflow/blob/main/docs/current_development_workflow.md "universalworkflow/docs/current_development_workflow.md at main · ghostairship-debug/universalworkflow · GitHub"
[5]: https://github.com/ghostairship-debug/universalworkflow/blob/main/apps/orchestrator_api/request_models.py "universalworkflow/apps/orchestrator_api/request_models.py at main · ghostairship-debug/universalworkflow · GitHub"
[6]: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html "Cross-Site Request Forgery Prevention - OWASP Cheat Sheet Series"
[7]: https://fastapi.tiangolo.com/tutorial/security/first-steps/ "Security - First Steps - FastAPI"
[8]: https://github.com/ghostairship-debug/universalworkflow/blob/main/docs/tech-debt-registry.md "universalworkflow/docs/tech-debt-registry.md at main · ghostairship-debug/universalworkflow · GitHub"
[9]: https://github.com/ghostairship-debug/universalworkflow/blob/main/docs/milestone_history.md "universalworkflow/docs/milestone_history.md at main · ghostairship-debug/universalworkflow · GitHub"
[10]: https://github.com/ghostairship-debug/universalworkflow/blob/main/apps/orchestrator_api/main.py "universalworkflow/apps/orchestrator_api/main.py at main · ghostairship-debug/universalworkflow · GitHub"
[11]: https://github.com/ghostairship-debug/universalworkflow/blob/main/apps/orchestrator_api/web_ui.py "universalworkflow/apps/orchestrator_api/web_ui.py at main · ghostairship-debug/universalworkflow · GitHub"
[12]: https://github.com/ghostairship-debug/universalworkflow/blob/main/pyproject.toml "universalworkflow/pyproject.toml at main · ghostairship-debug/universalworkflow · GitHub"
[13]: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ "Writing your pyproject.toml - Python Packaging User Guide"
