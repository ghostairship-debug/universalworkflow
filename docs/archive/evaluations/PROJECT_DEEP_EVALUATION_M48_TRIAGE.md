# Universal Agentic Workflow OS 当前阶段深度评估报告

日期：2026-04-25  
评估基线：已接受 `M47`，尚未打开新的 M48 bounded phase  
产品前提：个人自用 / 本地 operator runtime  
本轮重点：当前阶段问题排查、阻塞项、架构与实现挑刺、下一轮修改/优化建议

## 0. 结论先行

当前项目不是“主线不可用”的状态。相反，M47 后的主线已经具备相当完整的个人本地 workflow runtime 形态：CLI、API、Web workbench、chat control、repo mutation、PR-ready summary、scheduler authority、remote worker、capability projection、多集群与自适应路由都已经接入，并且主要验证链路可以跑通。

真正的问题是：系统能力已经铺得很宽，但下一阶段的主要风险从“功能缺口”转向了“可长期维护、可可靠验证、可安全恢复”。如果继续横向加能力，`OrchestratorService` / interaction / lifecycle / projection 这些大面会继续变重，测试反馈会继续变慢，能力健康会继续看起来比实际更可靠。

建议 M48 不再优先加新 provider / 新 cluster / 新 UI 页，而是聚焦：

1. 验证可靠性与测试分层。
2. repo mutation 原子性和回滚边界。
3. capability health 从 descriptor/assumed-ready 走向真实 telemetry。
4. `OrchestratorService` 和 `service_interaction.py` 的真实拆分。
5. Web/workbench 高风险动作的本地安全边界补强。

## 1. 本轮验证结果

已执行：

| 验证项 | 结果 | 备注 |
| --- | --- | --- |
| `python --version` | `Python 3.13.5` | 与 `pyproject.toml` 的 `>=3.13` 匹配 |
| `python -m infra.scripts.check_doc_links` | passed | 检查 6 个 living docs，issue_count=0 |
| `workflowctl --db-path state/workflow.db doctor` | status=`ok` | secrets 已 redacted，optional commands 可见 |
| `python -m infra.scripts.offline_validation --skip-offline-probe` | report `overall_passed=true` | 外层命令一度撞到 3 分钟超时，但 `state/offline_validation_report.json` 写出并显示所有 flow passed |
| `pytest -q --tb=short --basetemp=state/.pytest-tmp-eval` | `242 passed, 134 skipped in 367.53s` | 默认慢测跳过；全量快速测试实际约 6 分钟 |

发现的验证问题：

- README 当前写法 `workflowctl doctor --db-path state/workflow.db` 实测失败，Typer 要求全局参数放在子命令前：`workflowctl --db-path state/workflow.db doctor`。
- `pyproject.toml` 固定 `--basetemp=state/.pytest-tmp`。一次被超时打断的 `pytest -q` 在 Windows 上留下 SQLite 文件句柄，后续测试清理 basetemp 时出现 `PermissionError: [WinError 32]`。
- 当前“快速”默认测试虽然能通过，但约 6 分钟，不再是轻量回归。CLI/API/Web 慢测默认跳过，因此 `pytest -q` 对入口破坏的覆盖有限，主要依赖 offline validation 补位。
- `infra.validation.common.run_command()` 没有 per-command timeout，offline validation 出问题时不容易快速定位卡在哪个子步骤。

## 2. 当前项目成立的部分

### 架构方向仍然成立

- local-first + SQLite 适合个人本地 runtime。状态、审计、恢复和离线验证都能落在一个可复制的本地工作区里。
- CLI / API / Web workbench 三入口并存是合理的。这个项目不是单一 UI 产品，而是一个本地控制平面。
- review policy、human gate、scheduler authority、worker lease、runtime attempt、snapshot、operator packet 等边界是真实有价值的，尤其适合“自动化可以动代码，但必须可解释和可恢复”的使用场景。
- `M38` 的安全 test runner 修复已经实质完成：`run_test_commands()` 使用 `shell=False`、argv、timeout、输出截断、secret redaction 和危险命令拦截。
- M43-M47 的 artifact 闭环证明项目不只是抽象编排，已经能把真实输入转成可检查的本地输出。

### 工程纪律比一般个人项目强

- 有 living docs、技术债登记、milestone 摘要、offline validation、doc link check、doctor、自测入口。
- 有回归测试 376 个 collected，其中默认 profile 242 passed / 134 skipped。
- 高风险 chat action 已经有 confirmation card 的概念。
- external worker / scheduler authority 默认仍 local-only 或 opt-in，没有默认进入公网/分布式复杂度。

## 3. P0/P1 阻塞项

### 3.1 验证链路不够“抗中断”

证据：

- `pyproject.toml:47` 固定 `--basetemp=state/.pytest-tmp`。
- 一次超时后的 pytest 残留导致后续测试在清理 `state/.pytest-tmp/.../workflow.db` 时遇到 Windows 文件占用。
- 使用独立 basetemp 后同一批默认测试通过。

影响：

- 日常验证一旦被中断，下一次测试可能不是代码失败，而是临时目录/DB 句柄污染。
- 对本地 agentic workflow 来说，这种“验证环境脏了”会严重影响信任感。

建议：

- 不在 `pyproject.toml` 全局固定单一 basetemp，改为命令层生成唯一目录，例如 `state/.pytest-tmp/${timestamp}` 或默认 pytest temp。
- 增加 `make test-fast`，内置唯一 basetemp、`--tb=short`、`--durations=20`。
- 对会起子进程、写 SQLite、启动 API 的测试加统一 cleanup fixture。
- offline validation 的每个 flow 和每个 subprocess 都加 timeout，并在报告中记录耗时。

### 3.2 `OrchestratorService` 仍是最大结构债

证据：

- `packages/core_domain/services.py` 约 3370 行。
- `service_interaction.py` 约 2223 行。
- `service_lifecycle.py` 约 1653 行。
- `service_projection.py` 约 1549 行。
- `RunLifecycleService` 等类存在，但目前多为“把调用转回 facade”的代理，不是完整业务所有权迁移。

影响：

- 新能力最容易继续塞回 `OrchestratorService` 或 mixin。
- 代码已经分文件，但职责仍绕 facade 互调，后续开发者很难判断“这个逻辑应该去哪”。
- 当前结构会放大回归测试成本：小改动也可能触碰 lifecycle、projection、interaction、scheduler 多个平面。

建议优先拆出这些真实 owner：

- `RepoMutationCoordinator`：负责 patch generation/apply/test/fix loop/rollback。
- `CapabilityTelemetryService`：负责 capability health、receipt aggregation、recent call summary。
- `ChatCommandController`：负责 chat action inference、confirmation、action execution。
- `ClusterPlanningService`：负责 dynamic cluster selection、preview graph、cluster runtime bundle。
- `RepairCoordinator`：负责 inspection problem 选择和 apply_run_repair。
- `SchedulerLeaseCoordinator`：负责 scheduler lease/handoff/callback validation。

### 3.3 repo mutation patch apply 不是完全原子

证据：

- `service_repo_mutation.py` 会先 `capture_workspace_snapshot()`，再 `apply_unified_diff()`。
- 如果 `apply_unified_diff()` 在多文件 patch 中已经写入前面的文件，然后后续文件 apply 失败，最后一次尝试会直接 raise `PatchApplyError`，没有在 raise 前恢复 baseline。
- 有 retry 时下一轮开头会 restore；没有 retry 或最后一轮失败时存在留下部分修改的风险。

影响：

- 这会破坏 repo mutation 最重要的承诺：失败时不污染工作区。
- 对个人本地自动化尤其危险，因为失败后人可能误以为没有改动。

建议：

- `execute_repo_mutation()` 对 patch apply 失败路径加 `try/finally` 或显式 restore。
- 更稳妥的做法是 staging apply：先在临时副本或内存模型中验证全部 hunk，再一次性写入目标文件。
- 测试新增：多文件 patch 第一文件成功、第二文件失败时，断言第一文件恢复到 baseline。

### 3.4 Web/workbench 高风险动作缺少浏览器层安全约束

证据：

- `apps/orchestrator_api/main.py` 没有 auth middleware，当前依赖 loopback 本地使用前提。
- `apps/orchestrator_api/routers/ui.py` 中 resume/approve/reject/cancel/confirm 都是 POST，但没有 CSRF token 或 operator token。
- `apps/orchestrator_api/web_ui.py` 的 live SSE 渲染在若干位置用 `innerHTML` 拼接 `message.role`、`message.action_type`、`confirmation.action_type`、`confirmation.run_id` 等字段。

影响：

- 只要严格绑定 `127.0.0.1`，风险可接受；一旦误绑 `0.0.0.0`、反代、或打开远程 worker/workbench，这会立刻变成高风险。
- SSE payload 字段如果来自模型、任务卡或外部输入，`innerHTML` 会形成 XSS 风险面。

建议：

- 明确把“无认证 Web 仅限 loopback”写进 README 和 workbench 页面。
- UI POST 加本地 operator token 或 CSRF nonce，即使只是个人自用也能防误触/跨站请求。
- live DOM 构造改为 `createElement + textContent`，不要用 `innerHTML` 拼接 payload 字段。
- 高风险 action confirmation 增加 action summary / run id / mutation scope 的二次展示。

## 4. P1/P2 可优化项

### 4.1 capability health 仍然偏“声明式”

证据：

- `CapabilityPlane.list_capability_health()` 的 `recent_call_summary` 当前固定为 0/0。
- `_runtime_probe_for_descriptor()` 对 worker pool 和 adapter route 使用 `assumed_ready`，对 runtime gateway 主要看 configured/enabled。
- `workflowctl doctor` 显示 MMX/Vertex ready，主要依据 CLI/环境存在，不能证明真实多模态输入可稳定处理。

影响：

- operator 看到的“ready”容易被理解成“生产可用”，但当前更多是“配置看起来可用”。
- adaptive route / dynamic cluster 如果未来依赖 health 做选择，会被 descriptor optimism 误导。

建议：

- 从 `CapabilityExecutionReceipt` 或 evidence metadata 汇总最近 N 次成功/失败、耗时、return code、failure class。
- health 分级改为 `configured`、`probe_ready`、`recently_successful`、`degraded`、`disabled`，避免单一 ready 过载。
- 对 MMX/Vertex/Claude/Codex/OpenCode 增加轻量 probe command，失败时进入 degraded。

### 4.2 external worker 的 callback origin 配置尚未真正生效

证据：

- `config.py` 暴露 `WORKFLOW_WORKER_POOL_ALLOWED_CALLBACK_ORIGINS`。
- `external_workers.py` 会把 `callback_base_url` 传给 remote worker。
- `remote_worker_api/main.py` 收到 `callback_base_url` 后直接向该 URL POST heartbeat/completion。
- 当前代码没有看到对 `allowed_callback_origins` 的实际校验。

影响：

- 当前 seed 使用 `127.0.0.1`，风险有限。
- 如果远程 worker API 被开放，恶意或错误 dispatch payload 可能让 worker 向非预期地址发请求。

建议：

- 在 control plane 发 dispatch 前校验 callback_base_url 必须在 allowlist。
- remote worker 侧也做二次校验，默认只允许 loopback/private configured origins。
- 把 callback URL、base URL、shared secret 环境状态纳入 doctor issue，而不只是显示 present。

### 4.3 living docs 仍混有历史判断

证据：

- README 和 current workflow 把 M37/M38 报告仍列入 active truth set。
- M38 文档里保留 `pytest -q` 曾为 `299 passed` 的历史陈述；当前 collected/test profile 已变化为 `242 passed, 134 skipped` default。
- `check_doc_links` 只验证链接可达，不验证命令可执行或语义新鲜度。

影响：

- 未来重新进入项目时，容易把历史报告误读成当前执行计划。
- 文档命令错误不会被 doc link check 捕获，例如 doctor 的 `--db-path` 位置。

建议：

- 把 M37/M38 从 active truth 改成 historical references，当前 truth set 增加本报告或后续 M48 plan。
- 新增 `infra.scripts.check_doc_commands`，至少 smoke README 中的核心 CLI 命令。
- 在 milestone_history 中记录“当前 default pytest profile 的真实数量和耗时”。

### 4.4 测试分层需要重新划线

证据：

- `tests/test_api.py`、`tests/test_cli.py`、`tests/test_web_ui.py` 整文件标记 slow，默认 pytest 全跳过。
- `tests/test_execution_loop.py` 未整体标 slow，但文件约 2725 行，承担大量集成行为。
- 默认 pytest 仍需约 6 分钟。

建议：

- 建立三层：
  - `test-unit`：纯模型/解析/小服务，目标 < 60 秒。
  - `test-core`：当前默认主线，目标 < 3 分钟。
  - `test-integration`：CLI/API/Web/offline/cluster，M 收口或大改时运行。
- 把 `test_execution_loop.py` 中需要 subprocess、SQLite 大流、orchestration 多 child 的测试拆到 integration。
- 默认 `pytest -q` 保留最小 API/CLI smoke，不要整文件 slow 导致入口完全缺席。

### 4.5 repo mutation 的读取边界还能更硬

证据：

- `task_card_content_for_mutation()` 接受 `task_card_path`，绝对路径可被读取，只检查存在。
- write_set 有 workspace normalization，但 task_card/read context 的边界比 write_set 弱。

影响：

- 个人自用下通常可接受，但模型 prompt 可能包含不该进入任务上下文的本机文件。

建议：

- task card path 默认必须在 workspace 内，或必须显式列入 `read_set`。
- 对传入模型的 task card 内容做大小限制和 redaction。
- mutation report 里记录 read paths，而不只记录 changed files/test attempts。

### 4.6 Web UI 已经接近模板系统边界

证据：

- `apps/orchestrator_api/web_ui.py` 约 1352 行，HTML/CSS/JS 都在 Python f-string 中。
- Workbench streaming JS、confirmation card、status feed 都在同一文件。

影响：

- UI 后续一旦继续加能力，字符串模板会越来越难审查安全和布局。
- XSS/escaping 问题会更隐蔽。

建议：

- 短期先把 live JS 的 DOM 创建改为安全 helper。
- 中期把 CSS/JS 移到静态文件，HTML 用 Jinja2 或小型模板函数分区。
- 保持本地工具风格，不需要产品化前端框架。

### 4.7 示例游戏代码不宜长期留在 core runtime

证据：

- `packages/core_domain/local_game_artifacts.py` 约 1180 行。
- M43 游戏 vertical slice 是重要证据，但它属于示例 artifact/template，不属于 core orchestration domain。

建议：

- 将大型示例 artifact 生成器迁到 `examples/` 或 `packages/artifact_generators/`。
- core domain 只保留 artifact registry / dispatcher。
- 这样能避免核心领域模型被一次示例交付拖大。

## 5. 架构层建议

### 下一轮不要继续加宽 capability

当前已经有：

- Codex / OpenCode / shell / noop。
- MiniMax / DeepSeek chat 和 LangChain agent。
- MMX / Vertex / Claude artifact-only 骨架。
- MCP local workspace + MiniMax tools。
- adaptive routing + dynamic multi-cluster。
- remote worker + scheduler authority。

下一轮继续加 provider 的收益会递减。更有价值的是让已有 provider 的 readiness、cost、latency、failure class、fallback path 变得可信。

### 推荐 M48 主题

> M48 Validation Reliability, Mutation Atomicity, and Capability Telemetry

候选阶段：

1. Phase 0：修正文档命令、建立当前 truth set、记录当前验证基线。
2. Phase 1：测试/验证可靠性，唯一 basetemp、per-command timeout、duration report。
3. Phase 2：repo mutation 原子 apply 和 read boundary。
4. Phase 3：capability telemetry 和真实 health summary。
5. Phase 4：WorkBench 高风险动作 token/CSRF 和安全 DOM 渲染。
6. Phase 5：第一轮真实拆分 `service_interaction.py` / `services.py`。

## 6. 建议修改清单

### 立即修

| 优先级 | 项目 | 建议 |
| --- | --- | --- |
| P0 | README doctor 命令错误 | 改成 `workflowctl --db-path state/workflow.db doctor` |
| P0 | pytest 固定 basetemp | 改唯一 basetemp 或从 pyproject 移除固定路径 |
| P0 | repo mutation apply 失败污染工作区 | 最后一轮失败前 restore baseline，新增回归测试 |
| P1 | offline validation 子命令无 timeout | `run_command()` 加 timeout、每个 flow 记录 elapsed_ms |
| P1 | capability health assumed-ready | 引入 recent receipt summary 和 probe status |
| P1 | Web live JS innerHTML | 改 `textContent` / DOM builder |

### 接下来修

| 优先级 | 项目 | 建议 |
| --- | --- | --- |
| P1 | high-risk UI action | 本地 operator token / CSRF nonce |
| P1 | callback origin allowlist | control plane 和 remote worker 双侧校验 |
| P1 | `service_interaction.py` 过大 | 拆 chat controller、cluster planner、watchdog/profile service |
| P2 | `services.py` facade 继续收缩 | 将 repair、scheduler、capability read model 迁出 |
| P2 | doc semantic validation | 增加 README command smoke |
| P2 | 示例游戏代码位置 | 从 core domain 移到 examples/artifact generator |

## 7. 当前阶段可接受的风险

这些暂时不必抢修：

- 不需要公开 SaaS / 多用户认证 / 企业 RBAC。
- 不需要插件市场或第三方 onboarding。
- 不需要默认启用 scheduler authority cluster。
- 不需要默认启用 adaptive routing / dynamic cluster routing。
- 不需要把 MMX/Vertex 声称为主路径，只要文档保持诚实。

## 8. 最终判断

当前项目已经越过“能不能跑”的阶段，进入“能不能长期放心地让它替我做事”的阶段。

最重要的挑刺是：验证慢且对中断敏感、repo mutation 失败原子性还不够硬、capability health 仍偏乐观、核心 facade/mixin 继续过大、Workbench 高风险动作只适合严格 loopback。把这些修掉后，再继续加 provider、cluster、artifact workflow 才会更稳。

一句话建议：

> M48 应该先让系统的验证、回滚、能力健康和操作安全变得可信，而不是继续证明它还能接入更多能力。
