这次我确实基于你上传的压缩包做了**本地源码检查 + 部分动态测试**。结论比上次更明确：这个项目的方向值得继续，但当前仓库已经暴露出几个真实工程问题，尤其是 **测试未完全绿、MCP 工具投影漂移、外部 adapter 假设过强、测试命令执行安全边界偏弱、产品 wedge 不够聚焦**。

## 这次实际检查范围

我解压并检查了压缩包中的源码。压缩包里包含完整项目结构，包括：

```text
apps/
  operator_cli/
  operator_tui/
  orchestrator_api/
  remote_worker_api/
  scheduler_authority_api/

packages/
  contracts/
  core_domain/
  runtime_langgraph/
  worker_adapters/

infra/
  migrations/
  mcp/
  scripts/
  seeds/

tests/
```

本地环境里 Python 是 **3.13.5**，符合项目 `pyproject.toml` 的 `>=3.13` 要求。源码中大约有 **101 个 Python 文件**。我没有再停留在 README 层，而是检查了 `contracts`、`runtime`、`repo_mutation`、`worker_adapters`、`services`、`MCP`、`tests` 等关键路径。

但完整测试没有全部跑绿。原因不是 zip 不完整，而是当前环境和仓库测试本身暴露出真实问题：

| 测试/检查                            |          结果 | 说明                                 |
| -------------------------------- | ----------: | ---------------------------------- |
| `tests/test_contracts.py`        | ✅ 23 passed | 合约层状态机、模型约束基本稳定                    |
| `tests/test_runtime_boundary.py` |  ✅ 5 passed | Runtime boundary / snapshot 相关测试通过 |
| `tests/test_repositories.py`     | ✅ 16 passed | SQLite repository 层基本稳定            |
| `tests/test_governance.py`       | ✅ 10 passed | governance / review policy 基本稳定    |
| `tests/test_api.py`              |    ❌ failed | MCP tool projection 名称和测试期望不一致     |
| `tests/test_cli.py`              |    ❌ failed | 同样是 MCP 工具名漂移问题                    |
| `tests/test_execution_loop.py`   |    ❌ failed | 测试路径依赖本机有 `opencode` 可执行文件         |
| `tests/test_release_closeout.py` |  ⚠️ timeout | closeout/report 生成路径较慢或有阻塞，未完整诊断   |
| `tests/test_web_ui.py`           |  ⚠️ timeout | web UI 测试在当前环境里未完整跑完               |
| full `pytest`                    |     ❌ 未完整通过 | 不是 green 状态                        |

另外，当前环境缺少 `openai` 包，而项目依赖里需要 `openai>=2.26.0,<3.0.0`。环境里 pytest 是 9.x，但项目 pin 的 dev 依赖是 `<9`，所以正式 CI 应该用项目锁定版本再跑一次。尽管如此，已经足够确认：**当前代码不是一个“随便下载就全绿”的状态**。

---

# 一句话总评

**这是一个架构意识很强的 local-first agent workflow runtime，但当前已经有明显平台化过早、产品闭环不够尖锐、执行安全边界不够硬、测试可复现性不足的问题。**

我会给当前仓库这个评分：

| 维度    |     评分 | 判断                                                            |
| ----- | -----: | ------------------------------------------------------------- |
| 项目设想  |   8/10 | 方向对，local-first governed agent runtime 有价值                    |
| 架构设计  |   8/10 | contract、runtime boundary、review policy、mutation contract 都不错 |
| 当前实现  |   6/10 | 关键骨架存在，但测试不全绿，部分外部依赖假设过强                                      |
| 安全边界  |   5/10 | 有治理意识，但 shell/test/env/MCP 仍需硬化                               |
| 可拓展性  | 6.5/10 | SQLite local-first 很好，但 scheduler/remote worker 有过早复杂化迹象      |
| 产品化   | 4.5/10 | 更像工程平台内核，不像一个清晰可卖的产品                                          |
| 易用性   |   5/10 | CLI/API/TUI/Web 都有，但 README 和 onboarding 过重                   |
| 生态竞争力 | 6.5/10 | 方向对，但会被 Copilot/Codex/Claude Code/LangGraph 挤压                |

我的建议是：**继续做，但立刻收缩。不要继续横向扩展“Universal OS”，先打穿一个高价值闭环：GitHub issue / 本地任务卡 → 受控 patch → 测试 → review → PR-ready output。**

---

# 1. 项目设想是否合理

合理，而且比普通 agent demo 更有价值。

这个项目真正想做的是：

> 一个本地优先、可审计、可恢复、可治理的 agent workflow runtime。

这和当前生态方向一致。GitHub Copilot coding agent 已经把“从 issue、chat、CLI、MCP 工具等入口创建 PR，后台工作，完成后请求 review”变成主流路径；GitHub 文档也明确描述了 cloud agent 会研究仓库、创建计划、创建分支、提交变更，并通过 PR 交付。([GitHub Docs][1])

OpenAI Agents 生态也在强调 traces、tool calls、guardrails、handoffs、eval runs 等 agent workflow 的可观测与评估机制。也就是说，真正的竞争点已经不是“能不能调用模型”，而是能不能把 agent 执行变成**可控、可评估、可审计的工程系统**。([OpenAI开发者][2])

所以项目方向没错。问题在于当前项目名和 README 里的 **“Universal Agentic Workflow OS”** 太大了。它会让你不自觉地继续加能力：MCP、remote worker、scheduler authority、domain pack、memory、simulation、watchdog、TUI、Web UI、generated profile……最后变成一个很强的架构原型，但用户不知道第一天该用它解决什么问题。

更好的定位是：

> **Local-first governed runtime for bounded code-changing agents.**
> 本地优先、带治理的受控代码变更 agent runtime。

这个定位更窄，但更容易形成产品。

---

# 2. 架构优点：项目不是玩具，有几个设计是对的

## 2.1 Contract-first 做得不错

`packages/contracts/models.py` 里的 `RunStatus` 和状态转移很清楚：

```text
pending
prepared
running
awaiting_review
completed
failed
cancelled
```

并且有显式状态转移约束。这比很多 agent 项目里“一个 while loop 跑到底”的做法成熟很多。

`ReviewPolicy` 也把审查分成：

```text
auto_only
optional
recommended
human_required
mandatory
```

这说明你已经意识到 agent workflow 不能默认全自动，必须把 human-in-the-loop 作为 runtime 状态的一部分。

## 2.2 `MutationContract` 是当前最有价值的设计之一

`MutationContract` 要求明确：

```text
write_set
read_set
test_commands
max_fix_iterations
mutation_mode
```

并且当 `mutation_mode=patch_apply` 时强制要求非空 `write_set`。这很关键，因为 coding agent 最大的问题不是“不会写代码”，而是**会不会乱改、会不会越界、会不会在不该动的地方动手**。

你现在已经有了“受控 repo mutation”的雏形，这是项目最应该押注的核心能力。

## 2.3 Runtime boundary / snapshot / claim / lease 方向正确

`packages/contracts/runtime.py` 里有 `RunSnapshot`、`RuntimeClaim`、`WorkerLease` 等模型。这个方向是对的，因为长程 agent 任务一定会遇到：

* 中断恢复；
* 多 worker claim；
* lease 过期；
* replay；
* 任务取消；
* 失败恢复；
* 人工审批暂停。

LangGraph 的 durable execution 文档也强调，长任务需要持久化、恢复、人类介入，并且副作用和非确定性操作必须被小心封装，否则恢复时会重复执行。([LangChain文档][3])

你现在的 runtime boundary 设计是未来可扩展的基础。

## 2.4 Worker adapter 抽象基本正确

`packages/worker_adapters` 里有：

```text
ShellAdapter
CodexAdapter
OpenCodeAdapter
OpenCodeSessionAdapter
LangChainAgentAdapter
NoopAdapter
WorkerRouter
```

`ExecutionResult` 统一记录 return code、stdout、stderr、duration、artifact paths、metadata。这是正确的方向。模型和工具不应该散落在业务逻辑里，必须通过 adapter 层隔离。

---

# 3. 当前最严重的问题：测试没有全绿，而且失败暴露了设计漂移

## 3.1 MCP 工具投影名称漂移

`test_api.py` 和 `test_cli.py` 都失败在类似问题上：

```text
expected: mcp_list_workspace_files
actual:   list_workspace_files
          read_workspace_text
          read_execution_brief
```

仓库里的 `infra/mcp/readonly_workspace_server.py` 定义的是类似 `mcp_list_workspace_files` 的只读 workspace MCP 工具，但 API/CLI 投影出来的工具名已经变成了非 MCP 前缀的名字，或者走到了 built-in fallback。

这说明 **MCP capability projection 层已经和测试期望漂移**。

这不是大 bug，但它暴露了一个重要架构问题：你现在的 capability plane 同时要处理 built-in tools、MCP stdio tools、MCP HTTP tools、profile seed、projection preview、UI display name，很容易出现命名冲突和语义漂移。

建议改成三层名字：

```text
canonical_id:  mcp:<profile_id>:mcp_list_workspace_files
display_name:  list workspace files
raw_name:      mcp_list_workspace_files
```

测试应该断言 canonical identity，而不是只断言 display name。否则以后多个 MCP server 暴露同名工具时会出问题。

MCP 官方工具规范也强调工具是 model-controlled，客户端 UI 应清楚展示暴露给模型的工具、调用提示和确认机制；工具注解如果不是来自可信 server，也不应无条件信任。([Model Context Protocol][4])

## 3.2 `opencode` adapter 测试依赖本机可执行文件

`tests/test_execution_loop.py` 失败原因是：

```text
WorkerAdapterUnavailableError:
worker adapter 'opencode' is unavailable:
opencode executable was not found on PATH
```

这说明测试里有路径默认会真实寻找 `opencode`。这在集成测试里可以，但不能影响普通单元测试或离线测试。

建议：

* 单元测试注入 fake adapter；
* 没有 `opencode` 时自动 skip integration test；
* `workflowctl doctor` 显示 adapter availability；
* runtime 不应因为 optional adapter 缺失而导致普通工作流崩掉；
* `WorkerRouter` 应该能返回 degraded capability，而不是直接失败。

## 3.3 `release_closeout` 和 `web_ui` 测试有超时迹象

`tests/test_release_closeout.py` 和 `tests/test_web_ui.py` 在当前环境里没有稳定完成。可能是测试慢、report 生成路径太重，也可能存在等待/阻塞。

这类测试建议拆分：

```text
unit tests      < 5s
integration     < 30s
slow/e2e        单独 marker
release         手动或 CI nightly
```

现在所有东西混在一起，会导致本地开发者很难判断“项目是否健康”。

---

# 4. 安全风险：`run_test_commands` 是当前 P0 级问题

我认为当前最需要优先修的是：

```text
packages/core_domain/repo_mutation.py
```

里面 `run_test_commands` 使用了类似这样的执行方式：

```python
subprocess.run(
    command,
    cwd=...,
    shell=True,
    capture_output=True,
    text=True,
    env={**os.environ},
    check=False,
)
```

这有三个严重问题：

1. **`shell=True`**：任务卡里的 test command 变成任意 shell 执行通道。
2. **继承完整 `os.environ`**：可能把 `OPENAI_API_KEY`、`OPENCODE_*`、`WORKFLOW_*` 等敏感信息暴露给测试命令。
3. **没有明确 timeout**：恶意或错误命令可以挂住整个 run。

这会削弱你前面做得很好的 `write_set` 设计。因为即使 patch 只能改指定文件，`test_commands` 仍然可以执行任意命令。

建议立刻改成：

```python
@dataclass
class TestCommandSpec:
    argv: list[str]
    cwd: str | None
    timeout_seconds: int
    allowed_env_keys: list[str]
    risk_level: str
```

并加上：

* 默认禁止 `shell=True`；
* 必须有 timeout；
* stdout/stderr byte cap；
* 默认不传模型 API key；
* 高风险命令需要 review；
* `curl`、`wget`、`rm -rf`、`ssh`、`scp`、`nc`、重定向、管道、命令替换等进入高风险；
* 所有 test command 写入 trace；
* 输出做 secret redaction。

GitHub 对 Copilot 生成的 PR 也有类似安全假设：PR 应像任何贡献一样 review，GitHub Actions 默认不会自动运行，因为 workflow 可能拥有权限和 secrets，需要先检查变更再批准。([GitHub Docs][5])

你的项目也应该采取同样保守的安全模型。

---

# 5. Shell / env / adapter 风险

`ShellAdapter` 本身比 `run_test_commands` 稍好一些：它用的是 list command，不是 `shell=True`，并且有 120 秒 timeout。但仍然缺少：

* command allowlist；
* destructive command detector；
* network egress policy；
* stdout/stderr size cap；
* per-task risk level；
* per-adapter secret scope；
* trace redaction。

`packages/worker_adapters/subprocess_support.py` 里 env allowlist 包含：

```text
OPENAI_
OPENCODE_
PYTHON
WORKFLOW_
```

这对 adapter 调模型很方便，但对普通 shell/test 执行太宽。建议分成不同 env scope：

| Scope              | 可见环境变量                  |
| ------------------ | ----------------------- |
| `test`             | 最小 Python/Path，不含模型 key |
| `shell_safe`       | 最小 PATH + 显式传入变量        |
| `codex_adapter`    | Codex 所需 key            |
| `opencode_adapter` | OpenCode 所需 key         |
| `mcp_server`       | MCP server 专用变量         |
| `remote_worker`    | worker secret，但不传模型 key |

`OpenCodeAdapter` 里如果 `auto_approve=True` 会追加：

```text
--dangerously-skip-permissions
```

这个 flag 名字已经说明它必须被 policy 强管控。建议把它定义成 R4/R5 风险操作，默认禁止，只允许在：

```text
local sandbox
无敏感 env
明确用户授权
trace 完整记录
可回滚 workspace
```

的情况下开启。

---

# 6. MCP 接入方向对，但不能只当插件系统

你已经有 MCP optional dependency、MCP server profile、只读 workspace MCP pilot，这个方向很好。MCP 正在成为 agent 接外部工具和上下文的核心协议之一。

但 MCP 的安全边界必须更硬。官方 MCP 工具规范建议应用展示工具、展示调用过程、支持人工确认、验证输入、限制访问、记录 audit log。([Model Context Protocol][4])

你的 MCP Gateway 最少应该有：

```text
MCP Registry
  - server_profile_id
  - transport
  - startup command
  - version/hash
  - trust tier
  - allowed tools

MCP Policy Gateway
  - tool allowlist
  - schema validation
  - read/write/execute classification
  - confirmation requirement
  - timeout
  - output sanitizer

MCP Runtime Guard
  - stdio command allowlist
  - env scope
  - network policy
  - secret redaction
  - audit log
```

当前你已经有 `MCPServerProfile`、`TrustTier`、`ToolProjectionEntry` 等基础模型，但还需要把它们从“配置/投影”推进到“强制执行”。

---

# 7. 可拓展性：SQLite local-first 是优势，但 remote/scheduler 可能过早

我支持你继续保留 **SQLite local-first**。这是一个差异化点。

在 GitHub Copilot、Codex、Claude Code 这类平台型工具越来越强的情况下，你如果也做云端 agent，很容易被平台吃掉。local-first 的价值在于：

* 代码和状态留在本地；
* 用户可审计；
* 可自带模型；
* 可接本地工具；
* 可做私有化；
* 可更严格地管控 shell 和 secrets；
* 可回放 agent run。

OpenAI Agents SDK 当前也把 sandbox、工具调用、状态保持、审批和 orchestration 作为重要能力；如果应用自己掌控 orchestration、tool execution、approvals 和 state，就需要更底层的 agent runtime 能力。([OpenAI开发者][6])

但你当前又同时做了：

```text
remote worker pool
scheduler authority
lease ownership
cluster router
quorum-style control plane
durable snapshots
automation watchdog
```

这些不是错，但对现阶段可能过早。分布式调度会引入非常复杂的问题：

* 幂等；
* lease fencing；
* callback 重放；
* worker identity；
* 网络分区；
* 任务重复执行；
* side effect 去重；
* run ownership 转移；
* artifact 一致性。

建议先把单机 local-first 的 replay / idempotency / trace 做到非常扎实，再把 remote worker 标为 experimental。

---

# 8. 产品化问题：现在不像产品，更像平台内核

README 和项目结构给人的感觉是：

> 这是一个很复杂、很有野心的 agent OS。

但用户真正想知道的是：

> 我今天能用它完成什么？

现在最应该收缩成一个产品承诺：

> 给定一个本地任务卡或 GitHub issue，它会在明确 `write_set` 内生成 patch，运行受控测试，记录 trace，等待你 review，然后输出 PR-ready summary。

这比 “Universal Agentic Workflow OS” 更有说服力。

因为 GitHub Copilot 已经把 “issue → branch → code changes → PR → reviewer” 这条路径教育给用户了。GitHub 文档里也明确支持从 Issues、agents panel、Copilot Chat、CLI、MCP 工具等入口创建 Copilot PR。([GitHub Docs][1])

你要差异化，不能说“我也能创建 PR”。你应该强调：

```text
local-first
strict write_set
test command policy
multi-model routing
full trace
replay
human approval
private workspace
adapter-neutral
MCP governance
```

也就是：**不是更自动，而是更可控。**

---

# 9. 易用性问题：需要 `doctor` 和更清晰的 stable/preview 分层

当前项目很需要一个：

```bash
workflowctl doctor
```

它应该检查：

```text
Python version
required dependencies
optional dependencies
openai package
opencode executable
codex executable
MCP optional support
SQLite state path
env keys, redacted
available adapters
disabled adapters
pytest/dev mismatch
```

这能直接解决我这次遇到的问题：环境里有 Python 3.13，但缺 `openai`；测试路径假设有 `opencode`；pytest 版本和项目 pin 不一致。

README 也应该重写为四层：

```text
Stable
  - contracts
  - local SQLite runtime
  - bounded patch apply
  - governance policy
  - basic CLI/API

Preview
  - MCP capability projection
  - Web UI/TUI
  - Codex/OpenCode adapters

Experimental
  - remote worker pool
  - scheduler authority
  - generated profiles
  - automation watchdogs

Design-only / roadmap
  - universal domain packs
  - multi-agent project delivery presets
```

现在很多能力被放在同一个叙事层级，容易让外部用户误以为都已经稳定。

---

# 10. 架构层建议：`core_domain` 需要拆

`packages/core_domain` 已经有太多职责：

```text
capability
cluster_router
compile
config
db
domain_packs
external_workers
governance
memory
observability
orchestration_engine
repo_mutation
scheduler_authority
simulation
services
```

建议拆成更清晰的包：

```text
packages/runtime_core/
  state_machine.py
  snapshots.py
  claims.py
  leases.py

packages/repo_mutation/
  contracts.py
  patch_apply.py
  test_runner.py
  workspace_snapshot.py

packages/governance/
  policy.py
  approvals.py
  audit.py
  risk.py

packages/capability_gateway/
  mcp_registry.py
  tool_projection.py
  tool_policy.py
  schema_validation.py

packages/adapters/
  models/
  workers/
  tools/

packages/observability/
  traces.py
  metrics.py
  redaction.py

packages/evals/
  runner.py
  graders.py
  datasets.py
```

现在不是必须马上大重构，但要停止继续把新东西塞进 `core_domain`。

---

# 11. 生态位置：不要和 Copilot/Codex 正面硬拼

你不应该把项目定位成“另一个 coding agent”。

平台型竞争已经很强：

* GitHub Copilot coding agent：天然在 GitHub issue/PR 里；
* Codex：天然在 OpenAI/Codex 环境里；
* Claude Code：天然在 Anthropic developer workflow 里；
* Cursor：天然在 IDE 里；
* LangGraph：在 durable agent orchestration 上已有生态；
* OpenAI Agents SDK：tracing、guardrails、evals、tools 正在体系化。OpenAI 的 guardrails 文档也强调可以在工具执行前后包装检查、阻止或抛错。([OpenAI GitHub Pages][7])

你的机会不是“比他们更会写代码”，而是：

> **更本地、更受控、更可审计、更容易私有化、更适合企业或高级开发者自己定义 policy。**

这是一个可行 niche。

---

# 12. 下一阶段最重要的 30 天计划

## 第 1 周：先把安全和测试基线修好

P0：

1. 修 `run_test_commands`

   * 禁止默认 `shell=True`
   * 加 timeout
   * 加 stdout/stderr size cap
   * 使用 scoped env
   * 默认不传模型 key
   * 高风险命令要求 review

2. 修 MCP tool projection test drift

   * 明确 canonical id / display name / raw name
   * 防止 built-in 和 MCP 工具名冲突

3. 修 `opencode` 测试

   * 无 executable 时 skip integration test
   * 单元测试用 fake adapter

4. 标记慢测试

   * `release_closeout`
   * `web_ui`
   * 归入 `slow` 或 `e2e`

5. 恢复一个可信命令

   ```bash
   pytest -q -o addopts=''
   ```

目标不是覆盖率，而是**普通开发者能稳定跑完测试**。

## 第 2 周：收缩产品闭环

做一个最小可演示流程：

```text
task_card.yaml
  ↓
compile plan
  ↓
bounded patch apply
  ↓
safe test runner
  ↓
mutation result
  ↓
review policy
  ↓
PR-ready summary
```

不要再扩 domain pack / scheduler / multi-agent。

## 第 3 周：GitHub 最小集成

只做四件事：

```text
read issue
create local branch
generate PR body
create draft PR only after approval
```

GitHub push/create PR 都必须人工确认。

## 第 4 周：建立 evals 目录

新增：

```text
evals/
  repo_mutation/
    cases/
    runner.py
    graders.py
```

至少 20 个 case：

| 指标                      |   目标 |
| ----------------------- | ---: |
| patch 不越界               | 100% |
| unsafe command 被拦截      | 100% |
| test pass rate          | >80% |
| human review acceptance | >70% |
| secret leakage          |    0 |
| timeout/hang            |    0 |
| trace completeness      | 100% |

OpenAI agent eval 文档也建议用 traces、graders、datasets、eval runs 来系统化发现 regression 和 failure modes。([OpenAI开发者][2])

---

# 13. 最终建议

这个项目值得继续，但下一步不应该继续扩成更大的 “Universal OS”。

我建议你把项目战略改成：

> **一个 local-first、policy-governed、traceable 的代码变更 agent runtime。**

核心闭环：

```text
GitHub issue / local task card
  ↓
structured plan
  ↓
bounded write_set
  ↓
patch generation
  ↓
safe test runner
  ↓
trace + eval
  ↓
human review
  ↓
PR-ready output
```

当前最该做的不是加新能力，而是：

1. **让测试稳定绿。**
2. **修掉 `run_test_commands` 的安全边界。**
3. **修 MCP tool projection 漂移。**
4. **让 optional adapter 不影响普通测试。**
5. **把 README 从架构宣言改成产品 quickstart。**
6. **把 GitHub issue → bounded patch → review → PR-ready summary 做成第一条主线。**

我的最终判断是：**这个项目的骨架比普通 agent demo 强很多，但它现在正处在“架构复杂度超过产品验证”的阶段。接下来一轮迭代必须是收缩式迭代，而不是扩张式迭代。**

[1]: https://docs.github.com/copilot/using-github-copilot/coding-agent/asking-copilot-to-create-a-pull-request "Asking GitHub Copilot to create a pull request - GitHub Docs"
[2]: https://developers.openai.com/api/docs/guides/agent-evals "Evaluate agent workflows | OpenAI API"
[3]: https://docs.langchain.com/oss/python/langgraph/durable-execution "Durable execution - Docs by LangChain"
[4]: https://modelcontextprotocol.io/specification/2025-11-25/server/tools "Tools - Model Context Protocol"
[5]: https://docs.github.com/pt/enterprise-cloud%40latest/copilot/how-tos/use-copilot-agents/cloud-agent/review-copilot-prs "Examinar a saída de Copilot - GitHub Enterprise Cloud Docs"
[6]: https://developers.openai.com/api/docs/guides/agents "Agents SDK | OpenAI API"
[7]: https://openai.github.io/openai-agents-python/guardrails/ "Guardrails - OpenAI Agents SDK"
