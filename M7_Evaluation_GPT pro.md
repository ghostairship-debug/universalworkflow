下面是我基于你上传的整个仓库做的深度评估。这个结论不是只看 README 得来的，而是结合了实际解包、目录扫描、核心代码阅读、关键链路试跑、测试抽样与工作区状态检查。

我先给一句总判断：

**这不是一个 toy demo 了。它已经是一个“本地优先、具备编排/治理/审计/验证闭环”的 agentic workflow 基线。**
但它现在最需要的不是继续加功能，而是一次系统性的 **pre-M8 hardening**。
原因很明确：**功能广度已经够了，结构硬化没有跟上；而且当前上传的快照不是一个干净的、完全绿色的发布态，而是一个带本地状态和未提交改动的工作区快照。**

---

## 1. 我实际确认了什么

我不是只做静态阅读，我做了下面几类检查：

1. **完整解压并扫描仓库结构**

   * 这是一个比较大的 repo，不是单一脚本。
   * 当前工作区里有 **305 个 tracked 文件**。
   * 其中大约有 **40 个 Python 源文件**、**246 个 tracked Markdown 文档**。

2. **读了关键入口和核心实现**

   * CLI：`apps/operator_cli/main.py`
   * API：`apps/orchestrator_api/main.py`
   * TUI：`apps/operator_tui/dashboard.py`
   * 核心服务：`packages/core_domain/services.py`
   * 数据访问：`packages/core_domain/repositories.py`
   * 运行时边界：`packages/runtime_langgraph/gateway.py`
   * 执行适配器：`packages/worker_adapters/*`
   * 治理：`packages/core_domain/governance.py`
   * memory / simulation / domain pack / compile 等模块也都看了

3. **做了关键动态验证**

   * 我跑通了 `feature_delivery` 主链：`create -> compile -> resume -> completed`
   * 我也跑了 `research_spike`，确认它会进入 `awaiting_review`
   * `status-detail`、`summary`、`audit-report`、`simulation`、`memory-candidates` 这些操作面都是真实存在、且能工作

4. **测试层面做了收集和故障复现**

   * `pytest --collect-only -q` 实际收集到 **208 tests**
   * 我明确复现了 **至少两条失败用例**
   * 所以当前这个上传快照**不能再被视为绿基线**

5. **检查了 repo hygiene / 发布卫生**

   * 当前 zip 里带了 `.git`、`.pytest_cache`、大量 `.pyc`、多个 `.db` 和几千个运行产物
   * 这说明你发来的不是“干净源码包”，而是“本地工作目录快照”

---

## 2. 目前实现到了什么程度

### 2.1 这套系统已经实现的能力，比一般 demo 要完整很多

从产品形态上看，它已经有这些部分：

* **本地优先编排器**

  * CLI
  * FastAPI API
  * TUI 仪表板
  * SQLite 持久化
* **显式运行生命周期**

  * `create_run`
  * `compile_run`
  * `recompile_run`
  * `resume_run`
  * `cancel_run`
  * `approve/reject review`
  * `reconcile/repair`
* **运行时治理对象**

  * runtime state refs
  * claims
  * worker leases
  * runtime attempts
  * run snapshots
  * budget ledger
* **执行层抽象**

  * `shell`
  * `opencode`
  * `noop`
  * 通过 `WorkerRouter` 做 capability route
* **运行时网关边界**

  * `NullRuntimeGateway`
  * `OpenAIRuntimeGateway`
* **治理与报告面**

  * tech debt report
  * review policy report
  * release readiness report
  * domain pack platform report
* **memory / simulation / domain pack**

  * persisted memory baseline
  * retrieval preview
  * compile-time injection
  * deterministic local simulation
  * 一个已平台化的 domain pack

这说明它的“面”已经很宽了，而且不是假面。

---

### 2.2 核心运行链路是成立的

我实际跑过的两个典型路径说明了这不是只靠文档描述的系统。

#### `feature_delivery`

我验证到它可以走完：

* 创建 run
* compile 成 `prepared`
* 生成 `runtime_task_id` / `state_ref` / `handoff`
* route 到 `shell` adapter
* resume 后进入执行
* evidence 生成
* auto review 通过
* 最终 `completed`

而且 `status-detail` 里能看到：

* `review_policy=auto_only`
* `effective_review_state=auto_passed`
* `runtime_gateway.provider=null`
* `domain_pack=software_delivery_pack`
* `capability_resolution=shell_exec -> shell`

这说明以下几层是真正接起来了：

* contracts
* repositories
* orchestration service
* execution adapter
* review
* reporting

#### `research_spike`

我确认它会在执行后进入：

* `awaiting_review`

这说明 review policy 分支也是真实工作，而不是写在 README 里。

---

### 2.3 持久化和状态机设计是这个仓库的强项之一

`packages/contracts` 这一层做得其实不错。

有明确的：

* `RunStatus`
* `RuntimeGraphStep`
* `RuntimeClaimStatus`
* `WorkerLeaseStatus`
* `RuntimeAttemptStatus`
* `RunSnapshotStage`

而且有 Pydantic validator 去约束状态合法性。
这比“纯 dict + 随手写字段”的方式强很多。

数据库迁移也不是随便堆的：

* `001_init.sql`
* `002_m1_runtime_state_and_handoffs.sql`
* `003_m2_runtime_claims.sql`
* `004_m2_run_snapshots.sql`
* `005_m2_budget_ledgers.sql`
* `006_m2_worker_leases.sql`
* `007_m2_runtime_attempts.sql`
* `008_m6_memory_items.sql`
* `009_m7_simulation_records.sql`

并且 SQLite 打开了：

* `PRAGMA foreign_keys = ON`
* `PRAGMA journal_mode = WAL`
* `PRAGMA synchronous = NORMAL`

这代表作者是有意识地把它做成“可运行的本地系统”，而不是临时 PoC。

---

### 2.4 执行适配器层有明显的“平台化”意识

执行层不是硬编码在 service 里，而是抽象成 adapter：

* `ShellAdapter`
* `OpenCodeAdapter`
* `NoopAdapter`

`WorkerRouter` 负责 capability -> adapter 选择。
默认偏好是：

* `noop -> noop`
* `shell_exec -> shell`

这也意味着：

* `opencode` lane 已经存在
* 但默认主链仍然是保守的 `shell`

这是一个相对稳妥的策略：
**把 GPT-capable lane 做出来了，但没有贸然把主链默认切到 agent 模式。**

---

### 2.5 governance / report 面比一般内部工具更成熟

`packages/core_domain/governance.py` 不是摆设。

它能出这些报告：

* tech debt
* review policy
* release readiness
* domain pack platformization

而且这些不是死文本，而是会从：

* docs
* DB
* state/offline validation report
* worker routes
* domain pack registry

动态拼装。

这说明这套系统已经开始进入“工程治理”层，不只是“能跑一条任务”。

---

## 3. 我认为这个仓库当前最值得肯定的地方

### 第一，主链是完整的，不是假的

很多 agentic repo 表面上讲 capability、memory、simulation，实际上只是一层 prompt wrapper。
这套不是。它至少把这些事都做成了真实对象：

* compile / recompile / resume 分离
* state ref 持久化
* claim / lease / attempt / snapshot
* review state
* evidence
* audit / status detail / summary

### 第二，本地优先和确定性默认值控制得不错

`NullRuntimeGateway`、离线 smoke/demo、SQLite、`noop` 路线，这些都让它在没有云依赖时仍然有“可验证的骨架”。

### 第三，operator surface 很丰富

CLI、API、TUI、audit report、status detail、repair/reconcile，这些使得它比较接近“可运营系统”，而不是“只能开发者自己懂”。

### 第四，演进脉络有记录

这个 repo 不是一次写成的，阶段文档、review、task cards 很多。
虽然这也带来了文档噪音问题，但它说明这套东西是按里程碑推进出来的。

---

## 4. 当前最核心的问题

下面这部分是重点。我把风险按严重程度拆开讲。

---

### 4.1 **P0：当前快照不是干净发布态**

这是我认为你首先要正视的一点。

当前工作区是脏的：

* `README.md` 有未提交修改
* `docs/task_cards/m5_phase_3_task_cards.md` 有未提交修改
* `docs/tech-debt-registry.md` 有未提交修改
* `m5_phase_docs/phase_3_cli_first_architecture_correction_and_opencode_adapter.md` 有未提交修改
* `docs/reviews/m7-gemini-opus-pre-m8-synthesis.md` 是 **untracked**

这意味着：

1. 你给我的并不是一个 clean checkout
2. README 指向的某些当前状态，不一定对应一个可复现的 Git commit
3. 任何“当前已经完成”的结论，都要打折扣看待

**这很重要，因为它直接影响你对项目成熟度的判断。**

---

### 4.2 **P0：当前 repo 自述的“绿色状态”已经失真**

`README.md` 的 “Current repository status” 里写着当前绿基线包括：

* `pytest -q` -> `208 passed`
* offline validation `overall_passed=true`

但我实际复现到：

* `pytest --collect-only -q` 确实是 **208 collected**
* 但当前至少有 **2 条失败用例**

具体失败的是：

* `tests/test_api.py::test_api_exposes_governance_tech_debt_report`
* `tests/test_cli.py::test_cli_governance_tech_debt_report`

失败原因很具体：

```python
assert payload["planned_phase_counts"]["M3"] >= 1
```

现在会抛：

```python
KeyError: 'M3'
```

为什么？

因为 `docs/tech-debt-registry.md` 里的 debt phase 已经从旧的 milestone 写法（如 `M3`）改成了：

* `Next Cycle`
* `Pre-M8`

而 `packages/core_domain/governance.py` 的输出是照当前文档原样计数，所以现在返回的是：

```json
{
  "planned_phase_counts": {
    "Next Cycle": 5,
    "Pre-M8": 5
  },
  "m3_focus_items": []
}
```

这说明一个非常关键的问题：

> **当前 repo 的“运行时报告契约”已经被治理文档的文案变化打断了。**

也就是说，现在不是 parser 崩了，而是：

* 文档结构/语义变了
* 集成测试还在假设旧语义
* README 还在说绿

这比普通 test fail 更危险，因为它暴露的是 **source of truth 已经漂移**。

---

### 4.3 **P0：治理文档已经变成“运行时输入”，但没有 schema 化**

这是当前最明确、最值得优先改的架构缺陷之一。

`build_tech_debt_report()` 会直接解析：

* `docs/tech-debt-registry.md`

它依赖：

* `# 2.`、`# 3.` 这样的编号 section
* markdown table 的列顺序
* 某些字段名称和语义

这意味着你的治理文档已经不只是文档，而是：

> **运行时/报告层的真实输入数据源**

一旦如此，它就不该继续只是 Markdown prose，而应该升级成：

* YAML / JSON / SQLite 表 / 明确 schema 的结构化数据

然后 Markdown 应该由结构化数据生成，而不是反过来。

现在的问题不是“文档写得不够漂亮”，而是：

* 文档被系统消费
* 但文档没有被当成 contract 管理

今天是 `M3` -> `Pre-M8` 让测试炸了；
明天可能是 section 号改了、列顺序换了、标题重命名了，报告就悄悄错了。

---

### 4.4 **P0：发布包卫生很差，带了大量本地状态**

你给我的 zip 里包含了很多不该出现在“源码评估包”里的内容：

* `.git` 目录：约 **6.0M**
* `state/`：约 **6.7M**
* `.pytest_cache`
* `56` 个 `.pyc`
* `19` 个 `.db` 文件
* `7` 个 `.json` 文件
* `5222` 个 `state/artifacts/*.md`

这会带来几个问题：

#### 第一，交付噪音极大

别人拿到之后很难分清：

* 哪些是源码
* 哪些是运行产物
* 哪些是临时状态
* 哪些是历史验证残留

#### 第二，容易泄漏内部痕迹

`.git` 目录、运行 DB、artifact、validation report 都可能包含：

* 历史提交痕迹
* 本地测试残留
* 路径信息
* 中间生成内容

#### 第三，影响 reproducibility

别人复现时会被已有 DB/state 干扰，甚至以为某些产物是仓库本身的一部分。

更值得注意的是：
`.gitignore` 其实写得是对的，它已经忽略了：

* `__pycache__/`
* `*.py[cod]`
* `.pytest_cache/`
* `state/*`（保留 `.gitkeep`）

所以问题不在 Git 配置，而在于：

> **打包流程本身没有被产品化。**

也就是说，仓库能开发，但“如何输出一个干净交付物”还没制度化。

---

### 4.5 **P0：安全边界目前只适合本机可信环境**

这个点你可能没特别强调，但我认为很重要。

当前 API 没看到任何认证/授权层。
同时执行层有：

* `ShellAdapter` 直接 `subprocess.run(packet.command, ...)`
* `OpenCodeAdapter` 通过 CLI 调用外部 agent 工具
* 两类 adapter 都会继承 **整个父进程环境变量**

具体地，adapter 里是这样做的：

```python
env = os.environ.copy()
env.update(packet.env)
```

这意味着：

1. 只要某个子进程被启动，它就能看到父进程环境里的秘密信息
2. 如果未来把 API 暴露到非本地可信环境，这就是高风险面
3. 即便今天是 local-first，环境变量泄漏也会在 agent/CLI 工具扩展时变成问题

所以当前真实的安全边界应该明确写成：

> **仅适用于单机、受信任、本地操作者环境。**

如果未来要出本地机之外的部署形态，必须补：

* authn/authz
* env allowlist
* sandbox / command policy
* file system boundary
* request isolation

否则这个 API 不能安全外放。

---

### 4.6 **P0：预算里有 timeout，但执行层根本没有真正 enforce**

这是一个很隐蔽，但非常实质的问题。

preset/budget 里有：

* `timeout_seconds`

adapter 也有：

* `estimate_cost()` 返回 timeout

但真正执行 subprocess 时，并没有传 `timeout=`。
无论是 `ShellAdapter` 还是 `CliAdapterBase`，都是：

```python
subprocess.run(..., check=False, capture_output=True, text=True)
```

没有 timeout。

这意味着：

* 预算层在“声明超时”
* 执行层在“忽略超时”
* 一旦命令卡死，CLI/API 线程会被同步挂住

这不是小问题，这是一个 **运行时约束和实际行为不一致** 的问题。
我会把它排进最优先修复项。

---

### 4.7 **P0：可移植性有真实问题，不只是文档小瑕疵**

有两个很具体的点：

#### 1）compile 生成的命令硬编码了 `"python"`

在 `packages/core_domain/compile.py` 里，生成的是：

```python
return ["python", "-c", body]
```

这会在一些环境里出问题：

* venv / pyenv / 多 Python 环境
* 某些系统只有 `python3`
* 当前解释器和子进程解释器不一致

这里应该改成 `sys.executable`。

#### 2）仓库里有一批 Windows 本地绝对 Markdown 链接

我扫到多处类似：

* `/D:/Universal%20Agentic%20workflow/...`

出现在 README 和不少文档里。
这会导致：

* 任何非你本机路径环境的人都打不开
* GitHub / 普通 markdown viewer 里链接失效
* 文档可移植性下降

这个问题不是致命，但它很影响“交付给别人”的可信度。

---

## 5. 结构性问题：现在最危险的不是缺功能，而是“复杂度集中”

### 5.1 `packages/core_domain/services.py` 已经是明显的 God Object

这文件现在大约 **3623 行**。
而且不是“有很多小 helper”那种长，而是它实际承担了几乎所有核心职责：

* lifecycle orchestration
* compile / recompile / resume
* review handling
* status/detail/summary/audit projection
* memory candidate / retrieval / materialize
* simulation record / trigger
* reconcile / repair
* claim / lease / attempt / snapshot 协调
* domain pack / capability resolution

我看了它的 public API，职责面已经非常宽。
特别是 `resume_run` 单方法就接近 **389 行**。

这会带来几个后果：

1. **改动耦合度非常高**

   * 增一个运行时 feature，经常得动这一个文件

2. **回归半径很大**

   * 任何修改都可能波及主链、报告、repair、simulation

3. **合并冲突会越来越严重**

   * 尤其多人协作或后续 M8 再加功能时

4. **局部推理越来越困难**

   * 你看一个能力，不得不带着一整个系统上下文

我认同你们文档里“pre-M8 hardening gate”的方向判断。
因为如果继续把新能力堆进 `services.py`，会越来越难救。

---

### 5.2 `infra/scripts/offline_validation.py` 正在变成第二个 God Object

这个文件现在约 **1769 行**。

更关键的是，它不是简单地“很多小函数”，而是有两个非常大的流程函数：

* `validate_cli_flow` 约 **976 行**
* `validate_api_flow` 约 **449 行**

它还直接做：

* CLI 调用
* API 调用
* 状态检查
* 网络探测
* 故障注入
* DB 直接修改
* 报告汇总

这会导致一个典型问题：

> 你已经把业务复杂度从 runtime 主链里，复制了一份到 validation 主链里。

这是危险的，因为 validation 本来应该是“验证系统”，不应该自己变成另一个难维护的系统。

---

### 5.3 当前“真实执行能力”和“编排能力”之间仍然有层级差

这一点要实话实说。

这套仓库的**编排能力**已经明显强于它的**实际任务执行能力**。

因为当前 compile 出来的 shell 主链，本质上是生成一个 `python -c` 命令去写 artifact 文件。
也就是说，系统现在最成熟的是：

* 生命周期编排
* 持久化
* 路由
* 证据/审计
* review / governance

而不是“通用 agent execution”。

这不是坏事。
相反，这说明系统骨架是认真做的。
但它也意味着：

> 如果你要对外描述它当前的成熟度，更准确的说法应该是：
> **“一个较成熟的本地编排/治理骨架，带有最小真实执行基线”**
> 而不是“已经是通用 agent runtime”。

这一点如果不说清，会导致后续路线判断错误。

---

### 5.4 `TaskKind` 语义现在有点混合了

目前 `TaskKind` 只有：

* `shell_exec`
* `noop`

而 `opencode` 这类明显带模型/agent 特征的执行路由，仍然挂在 `shell_exec` 下。

这会带来一个长期问题：

* deterministic shell
* model-mediated CLI execution

这两者的：

* 风险模型
* review 需求
* budget 策略
* evidence 解释
* sandbox 要求

其实不一样。

现在它们共享一个 task kind，会让很多后续策略只能通过 adapter name 补丁式分流，而不是在 contract 层就表达清楚。

我建议以后把能力语义分得更清楚，比如至少考虑区分：

* `shell_exec`
* `agent_exec`
* `noop`

这样 policy、review、simulation、budget 才能更干净。

---

### 5.5 auto review 规则现在过于粗糙

`AutoReviewV0` 的逻辑是：

* return code == 0
* stderr 为空
* 才算 pass

这个 baseline 作为最早版本没问题，但如果系统进入更真实的工具执行阶段，会很容易出现误判：

* 有些工具成功时会往 stderr 打 warning
* 有些 CLI 输出风格不标准
* 有些 agent tool 会产生“非失败 stderr”

这会导致：

* false fail
* 不必要的人审升级
* operator 对 review 结果信任下降

所以 review 现在有了闭环，但质量还很初级。

---

## 6. 还有一些不那么显眼，但很重要的点

### 6.1 README 当前指向一个 **untracked 文档**

`README.md` 里当前引用了：

* `docs/reviews/m7-gemini-opus-pre-m8-synthesis.md`

但这个文件在当前工作区是 **未跟踪文件**。
这意味着：

* 你本地 zip 里有它
* 但 Git 历史里未必有它
* 别人 clone 下来可能看不到 README 指向的内容

这个非常像“本地认知已更新，仓库 canonical source of truth 还没同步”的状态。

---

### 6.2 release readiness 还依赖 `state/offline_validation_report.json`

`build_release_readiness_report()` 会去读：

* `state/offline_validation_report.json`

这说明治理/发布报告不仅依赖代码和 DB，还依赖本地状态文件。
这不是不能做，但需要明确：

* 它是不是“最新运行结果”
* 它是否可能陈旧
* 它是否和当前 checkout 对应

否则 release readiness 可能变成“读到一个历史 report，然后告诉你一切正常”。

---

### 6.3 当前没有看到 CI 工作流配置

我没有看到 `.github/workflows` 或类似 CI 配置。
这代表目前“绿基线”更多是人工宣称，而不是持续验证。

在现在这种体量下，缺 CI 是明显短板。
尤其当：

* README 会写当前状态
* 文档会被 parser 消费
* 测试已有 208 个
* 工作区可能有未提交改动

这时没有 CI，很容易把“我本机刚好好过”误当成“项目状态稳定”。

---

### 6.4 没有 lock file，依赖复现性不强

当前有 `pyproject.toml`，但我没看到 lock 文件。
同时依赖上限又写得比较窄。

这意味着两边都不太舒服：

* 一方面没有 lock，别人环境不一定一致
* 另一方面上限又卡得很紧，升级维护麻烦

这会让“复现”和“维护”同时不够优雅。

---

### 6.5 文档历史很完整，但当前信噪比已经开始下降

repo 里有很多 phase docs、review、task cards、legacy docs。
这说明过程记录很认真，但现在也开始产生一个副作用：

> 当前状态、历史状态、计划状态、评审状态，正在混在一起。

如果不做一次 archive / current / canonical source 的整理，团队会越来越难回答这三个简单问题：

* 现在真实 shipped 的是什么？
* 现在真实 debt 有哪些？
* 接下来批准做的到底是什么？

---

## 7. 我给你的修改建议

我按“先救火，再硬化，再扩展”的顺序给。

---

### 7.1 第一优先级：先把当前基线拉回可信状态

#### 建议 1：修复 governance tech debt 契约漂移

这里你有两个路线：

#### 路线 A：承认语义已经升级，改测试

如果 `M3` 这种旧 phase 语义已经废弃，那就：

* 更新 `tests/test_api.py`
* 更新 `tests/test_cli.py`

不要再硬断言 `"M3"`，而改成验证更稳定的东西，例如：

* `open_debt_count`
* `planned_phase_counts` 总和
* 包含 `TD-010` 等关键 debt
* 预期 buckets 包含 `Pre-M8` / `Next Cycle`

#### 路线 B：维持兼容 API，改报告输出

如果你希望 API/CLI 向后兼容，那就别只输出文档原始 phase。
可以加一层标准化输出，比如：

* `planned_phase_counts_raw`
* `planned_phase_counts_normalized`
* `priority_focus_items`

这样旧测试和新文档可以同时共存一段时间。

**我更推荐 B 的思想，但 A 可以更快止血。**
关键不是选哪条，而是要把“治理文档即运行时输入”的事实正式化。

---

#### 建议 2：README 当前状态必须和真实 repo 对齐

至少要改这些：

* `pytest -q -> 208 passed` 这类当前断言，不能继续保留
* 如果当前 worktree 非绿，就不要写成已绿
* README 不要引用 untracked 文档
* 绝对路径 markdown link 改成相对路径

---

#### 建议 3：做一个正式的“源码发布打包”命令

不要再直接拿工作目录压 zip。

建议新增一个明确脚本，比如：

* `python -m infra.scripts.package_source`
* 或 `make dist-src`

它应该只包含：

* tracked source
* 必要 docs
* seed / migrations
* 不包含 `.git`
* 不包含 `state/*`
* 不包含 `.pytest_cache`
* 不包含 `__pycache__`
* 不包含本地 DB / artifacts

这个动作看似外围，实际上对团队协作、评估、交付都非常重要。

---

#### 建议 4：立刻给 adapter 真正加 timeout enforce

这是运行稳定性的硬需求。

要做的不只是“配置 timeout”，而是：

* `subprocess.run(..., timeout=...)`
* 捕获 `TimeoutExpired`
* 产出明确的 `ExecutionResult`
* evidence 里标记 `timed_out`
* review / summary / status-detail 能正确反映
* 预算与执行行为一致

现在这个缺口不补，系统遇到挂住命令时就会很难看。

---

#### 建议 5：不要让子进程继承全部父环境变量

建议把环境改成 allowlist，而不是 `os.environ.copy()` 全量继承。

最低限度至少只保留：

* `PATH`
* 平台运行必要变量
* 显式 `WORKFLOW_*`

这样可以显著降低：

* secret leakage
* agent/CLI 工具读取宿主隐私配置
* 跨环境行为不一致

---

#### 建议 6：compile 子命令改成 `sys.executable`

这个改动很小，但收益很直接。
比硬编码 `"python"` 健壮得多。

---

## 8. 第二优先级：做一轮结构硬化，而不是继续堆功能

### 8.1 拆 `OrchestratorService`

我不建议一口气大重写。最稳妥的方法是：

**保留 `OrchestratorService` 这个 facade，不改 CLI/API 对外接口；内部把职责逐步下沉。**

建议拆成至少这些服务：

* `run_lifecycle_service.py`

  * create / compile / recompile / resume / cancel
* `review_service.py`

  * auto review / human review transition
* `resource_ownership_service.py`

  * claim / worker lease / runtime attempt / snapshot
* `inspection_service.py`

  * status-detail / summary / audit-report / inspect-state
* `repair_service.py`

  * reconcile / apply repair
* `memory_service.py`

  * candidates / retrieval preview / materialize
* `simulation_service.py`

  * trigger / record / query
* `projection_service.py`

  * API/CLI 共用的投影装配逻辑

这样可以做到：

* 对外接口基本不变
* 先降耦合
* 再逐步清理 `services.py`

---

### 8.2 把 `offline_validation.py` 模块化

建议拆成：

* `infra/validation/common.py`
* `infra/validation/cli_flow.py`
* `infra/validation/api_flow.py`
* `infra/validation/fault_injection.py`
* `infra/validation/reporting.py`
* `infra/validation/runner.py`

这样可以把：

* 共用断言
* CLI 调用
* API 调用
* 故障注入
* report 组装

分开处理。

我尤其建议把“DB 直接篡改”的逻辑单独收口到 `fault_injection.py`，不要让 validation 主流程满地都是直接 SQL mutate。

---

### 8.3 治理数据改成结构化源，Markdown 只做展示层

这是我很强烈建议做的事。

建议建立一个结构化治理源，比如：

* `infra/governance/tech_debt_registry.json`
* 或 `docs/governance/tech_debt_registry.yaml`

里面存：

* debt_id
* description
* introduced_in
* planned_repayment_phase
* normalized_bucket
* current_status
* blocking_impact
* priority
* owner
* notes

然后：

* API/CLI 读结构化源
* Markdown 由结构化源生成

这样你就不会再遇到“改文案把接口打断”的事。

---

### 8.4 给 runtime brief / memory retrieval 做硬预算

目前 memory preview 和 runtime brief 会进 compile/runtime path，但还缺真正的 budget guard。

建议在进入 gateway / adapter 之前，统一做：

* payload size preflight
* line count limit
* bytes limit
* model-specific token budget estimate
* prune strategy
* prune audit trail

否则后续 memory/domain pack 一扩大，很容易出现：

* prompt/context 溢出
* 环境变量 payload 过大
* provider 行为不可预测

这里还有一个你可能没想到的点：

> 当前 memory preview 是通过环境变量 `WORKFLOW_MEMORY_RETRIEVAL_PREVIEW` 传下去的。
> 一旦内容变大，不仅有 token 风险，还有 **操作系统环境变量长度上限** 风险。

---

## 9. 第三优先级：让它从“内部可用”走向“长期可维护”

### 9.1 上 CI

至少应该有这些 gate：

* `pytest -q`
* smoke
* 关键 CLI/API flow
* docs link check
* package hygiene check
* maybe offline validation 的精简版

现在这个项目的复杂度已经过了“没有 CI 也能靠人肉盯住”的阶段。

---

### 9.2 加 lock file，顺手放宽过窄的上限策略

现在依赖策略有点两头别扭：

* 没 lock
* upper bound 又紧

建议要么：

* 引入 lock file 做精确复现
* 再配合 CI 定期升级

否则你会一直在“本地可以、别人未必行”和“每次小版本都得手动改上限”之间来回消耗。

---

### 9.3 重新整理 docs 信息架构

建议至少拆成：

* `docs/current/` 当前有效规范
* `docs/reviews/` 历史评审
* `docs/archive/` 历史 phase / legacy 资料

否则文档越多，越难分辨哪份是 canonical。

---

### 9.4 明确当前产品定位

我建议在 README 里把当前定位说得更准一些：

不是“通用 agent 平台已成熟”，而是：

* **本地优先编排/治理骨架已成熟**
* **真实执行基线已建立**
* **多 adapter / memory / simulation / governance 已接通**
* **下一步优先是结构硬化与运行时约束完善**

这个定位更诚实，也更利于团队做正确决策。

---

## 10. 一个我建议的下一步开发方案

我会建议你不要直接进 M8 功能扩张，而是先做一个明确的 **Pre-M8 Hardening Sprint**。

### 阶段 1：恢复可信基线

目标：让“当前状态”重新可信

要完成：

* 修复 governance report / tests 漂移
* README 状态与实际对齐
* 绝对路径文档链接改掉
* 提交或回滚当前脏改动，形成 clean worktree
* 做干净源码打包脚本
* 给 adapter 加真正 timeout
* 改环境变量继承策略

**出口条件：**

* `git status` clean
* 测试绿
* package 输出干净
* README 不再说谎

---

### 阶段 2：结构硬化

目标：降低变更耦合，避免 M8 继续堆在 `services.py`

要完成：

* `OrchestratorService` facade 化
* 拆分 lifecycle / review / projection / memory / simulation / repair
* `offline_validation` 模块化
* runtime brief / memory budget guard
* 统一 projection / serializer，减少 CLI/API 重复装配

**出口条件：**

* `services.py` 明显瘦身
* validation 不再是单巨脚本
* 关键模块边界清晰

---

### 阶段 3：治理与发布面正规化

目标：把“工程治理”做成稳定基础设施

要完成：

* tech debt registry 结构化
* release readiness 对外部 state 文件依赖显式化
* CI + lock file
* docs current/archive 分层
* canonical status 从自动化结果生成，而不是手工写 README

**出口条件：**

* 报告不再依赖脆弱 Markdown 解析
* 当前状态可由自动化产出证明
* 团队可以明确知道“什么是现在的真相”

---

## 11. 你可能还没特别注意，但我认为很关键的点

这里我列几个“不是最表面，但很值钱”的判断。

### 11.1 现在最值钱的不是再加能力，而是守住“局部可推理性”

如果再把 M8 功能继续往 `services.py` 和 `offline_validation.py` 上堆，后面每一个迭代的成本都会指数上升。

### 11.2 这个仓库最大的优点是“骨架真实”，不要为了追求 feature breadth 破坏本地优先和可验证性

很多团队会在这一步急着接更多 provider、更多智能体、更多策略，最后把原本很好的 deterministic baseline 搞没了。
这套 repo 的本地优先骨架是长处，不是限制。

### 11.3 你们现在已经进入“文档也是系统输入”的阶段了

这是一条分水岭。
一旦跨过这条线，文档必须像 schema 一样管理，而不能再只当人类叙述。

### 11.4 当前最大的潜在事故点，不是逻辑错误，而是“运行时失控”

具体包括：

* 超时未 enforce
* 子进程继承全环境
* API 无 auth
* shell/opencode 可执行外部命令
* 发布包混入本地状态

这些一旦叠加，就会从“工程问题”变成“事故问题”。

---

## 12. 最终结论

我的总体结论是：

### 这是一个**已经跨过 demo 阶段**的 agentic workflow 仓库

它的成熟点在于：

* 生命周期完整
* 持久化认真
* operator surface 丰富
* governance/reporting 已接入
* memory/simulation/domain pack 已有真实基线
* 本地优先、可验证、可审计

### 但它现在处于一种很典型的“广度足够、结构吃紧”的状态

最明显的信号就是：

* `services.py` 过大
* `offline_validation.py` 过大
* 文档与运行时契约漂移
* README 当前状态已与实际不完全一致
* 上传快照是 dirty worktree
* 发布卫生不足
* timeout/security boundary 还没真正收紧

### 所以下一步最正确的决策不是“继续扩 M8”

而是：

> **先做一次 pre-M8 hardening，把当前系统从“能跑、能演示、能审计”拉到“可信、可维护、可交付”。**

如果只让我给一句最实用的建议，那就是：

**先把“治理契约稳定化 + 运行时 timeout/env 边界收紧 + service/validation 去 God Object 化”这三件事做完，再谈下一轮功能扩张。**
