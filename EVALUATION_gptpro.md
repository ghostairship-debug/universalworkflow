我这次是按你上传的代码快照本身重新评估，不只看 README 和评审文档。结论先说：

这个版本已经不是概念原型了，它有一套真实的 workflow / control-plane 骨架；但它还没有达到“稳定通用 agent OS”的成熟度。更准确的定位是：**一个完成度不错的 agentic workflow control plane 原型**，强项在控制、治理、投影和执行边界，弱项在自治深度、交付基线、以及外部能力整合。

## 1. 当前状态

我会把当前状态概括成四句话：

1. **文档状态高于实际交付状态。**
   `docs/current_development_workflow.md`、`docs/reviews/m20-freeze-review.md`、`docs/tech-debt-registry.md` 都在表达 “M20 已完成 / v1 core 已完成 / tech debt 已清空”。但这次交付的仓库快照本身不是一个干净冻结基线：当前 zip 里带着 `.git`、`.pytest_cache`、`__pycache__`、`state/` 等运行噪声；仓库里明明已经有 `infra/validation/source_package.py` 和 `infra/scripts/export_source_package.py` 用来做干净导出，说明**流程上知道该怎么做，交付上却没有贯彻**。

2. **控制面强于能力面。**
   真正比较扎实的部分，在 `packages/core_domain/service_lifecycle.py`、`service_projection.py`、`repositories.py`、`db.py`、`scheduler_authority.py`、`external_workers.py`、`repo_mutation.py`、`capability_plane.py`、`observability.py`。这部分已经像一个系统，而不是 demo。尤其值得肯定的是，`infra/migrations/*.sql` + `packages/core_domain/db.py` 的**增量 migration 是真实存在的**，这比很多只会 reset-db 的 agent 项目强不少。

3. **流程跑通强于结果可信。**
   `state/workflow.db` 里 schema 和 migration 是齐的，但业务表基本空；`state/artifacts/` 有大量 markdown artifact，不过内容普遍很短，很多更像元数据 stub、占位文本或 orchestration 记录，足以证明“流程能跑”，但还不足以证明“复杂任务能稳定完成”。

4. **测试可信度是部分成立，不是完整闭环。**
   我抽样跑了 `tests/test_contracts.py`、`tests/test_repositories.py`、`tests/test_runtime_boundary.py`，共 41 个通过；但全量 `pytest -q` 在当前环境下会因为 `mcp` 在导入期硬依赖而失败收集。这里要公平一点看：`mcp` 在 `pyproject.toml` 里确实被声明为依赖，所以这不一定等于代码 defect；但它明确说明了一件事：**现在的“外部能力可选接入”，还没有做到真正的可选和可降级。**

## 2. 实现评估

### 我认为已经做得比较好的部分

`services.py` + `service_lifecycle.py` + `service_projection.py` 这条主链，已经把 **编排、恢复、审批、拒绝、投影、审计** 串起来了。
`repositories.py` 不是 ORM 拼装，而是比较明确的 SQLite repository；`scheduler_authority.py`、`external_workers.py` 也已经有了 worker pool / remote dispatch 的雏形；`repo_mutation.py` 说明你们不是只会“让 agent 输出一个 patch”，而是开始考虑 **allowed path、diff apply、test loop、快照恢复** 这些真正会踩坑的边界。

### 我认为目前最明显的实现短板

最核心的问题是：**workflow 很强，agent 很薄。**

* `packages/core_domain/services.py` 已经膨胀成一个 3700+ 行、142 methods 的单体服务，这不是小问题，后续所有需求、修复、策略变更都会持续往里堆。
* `packages/runtime_langgraph/gateway.py` 目前只有 `NullRuntimeGateway` 和 `OpenAIRuntimeGateway`，而后者的 `resume()` 主要是在生成简短 execution brief，并不是一个真正强执行能力的 runtime。
* `project_delivery` 目前仍然主要依赖固定模板；默认 planner/coder/researcher/reviewer/operator + barrier 的设计，说明现在还属于**预设编排**，不是动态角色合成。
* `compile.py` / artifact builder 的默认产出更偏向结构化 markdown 结果，而不是带证据、验证、差异和质量评分的统一结果对象。

所以这套系统当前更像：**一个有治理和审计意识的 agent workflow 操作系统内核**，而不是一个已经成熟的“多智能体生产系统”。

## 3. 主要风险

### 风险 1：基线可信度风险（最高）

现在最危险的不是功能少，而是**“文档说冻结完成，但交付物本身不是干净冻结基线”**。
这会直接影响后续所有事情：评审、回归、对外演示、版本对比、缺陷归因，都会变得模糊。

### 风险 2：单体服务膨胀风险（高）

`OrchestratorService` 体量已经过线。继续演进下去，审批逻辑、状态逻辑、编排逻辑、worker 逻辑、artifact 逻辑会互相污染，最后会很难做局部替换和局部验证。

### 风险 3：伪自治风险（高）

系统很容易给人“多 agent 很完整”的感受，但默认路径里大量产出只是 artifact metadata。
这会形成一种错觉：**workflow 的完备性，被误读成任务完成能力的完备性。**

### 风险 4：可选能力耦合风险（中高）

MCP 相关依赖在导入期耦合进 core domain，说明插件边界还不够干净。
这会让外部能力接入越来越多之后，安装、启动、测试、打包都变复杂。

### 风险 5：外部边界安全/鉴权风险（中高）

一旦开始大规模接入 remote worker、remote MCP、GitHub、浏览器、文件系统、CI，这套系统会立刻从“本地编排问题”变成“权限与审计问题”。
如果不提前做统一 capability scope、凭证托管、审批级别和 side-effect 分级，后面会非常难补。

### 风险 6：路线判断失真风险（中）

文档把 tech debt 基本都标成 retired，但从代码体量、单体服务、能力接缝、产出模型来看，**结构性债务其实还在**。
如果继续按“债已经清空”的心态推进，后面大概率会在外部集成阶段重新爆出来。

## 4. 修改建议

我建议下一步不要继续横向扩功能，而是按这个顺序做。

### 第一组：先把基线做干净

把当前版本切出一个真正可复现的 baseline：

* 只导出 source package，不带 `.git`、cache、`state/`
* 产出正式 validation report，而不是只在文档里写“某次验证通过”
* 给出一组 canonical demo runs，而不是空 DB + 分散 artifact

这一步做完，后续所有评估和版本比较才有意义。

### 第二组：拆 `OrchestratorService`

至少拆成几块边界清楚的服务：

* 生命周期与状态机
* 编排计划与 DAG
* capability / worker gateway
* 审批与治理
* artifact / result projection

这不是“代码美化”，而是后续能不能安全演进的前置条件。

### 第三组：把 artifact 升级成统一结果对象

现在 markdown artifact 可以保留，但应该降级为**人类可读投影**，不该再当系统真相源。
我建议引入一个统一的 `ResultEnvelope`，至少包含：

* summary
* evidence
* raw output reference
* mutations / patches
* verification
* provenance
* usage / cost / latency
* confidence

这样后面无论接 OpenAI 工具、MCP、GitHub、浏览器、CI，结果都能统一落库、统一审批、统一投影。

### 第四组：把“可选能力”做成真正插件化

像 `mcp` 这种依赖，不应该在 core domain 导入期就锁死。
应该改成：

* lazy import
* extras 安装（如 `[mcp]`、`[browser]`、`[github]`、`[vector]`）
* capability registry 启动时探测
* 缺失时可降级，不影响主链路测试

### 第五组：把 `project_delivery` 从模板编排升级成图编排

当前固定角色模板可以保留，但应该变成一种“默认 plan”，不是唯一 plan。
下一步应该让 planner 产出 DAG，再由治理层决定：

* 哪些节点必须 review
* 哪些节点可并行
* 哪些能力可用
* 哪些 side-effect 需要人批

### 第六组：建立真正的 golden workflow 回归

别只跑单元测试。
你们已经有控制面了，就应该有黄金回归：从 compile → run → review → artifact → projection 全链路重放，验证 run state、artifact、审计记录、worker side-effect 是否一致。

## 5. 哪些外部能力适合接入，而不是自己重复造轮子

这里我会讲得很直接：**最适合外接的，不是另一个“总控 agent framework”，而是 commodity 能力。**
也就是说，不要再找一个 LangChain / AutoGen / 其他上层框架来包住你现有系统；你已经有自己的 control plane，再叠一个总控，只会形成双状态机、双调度语义。外部化的对象应该是工具层、执行层和基础设施层。

### 1) OpenAI Responses 托管工具：适合优先接入

Responses API 现在已经把 web search、file search、computer use、Code Interpreter、remote MCP servers 这些能力做成统一工具接口，而且支持 long-running/background 模式。对你这套系统来说，最合理的方式不是自己再造一层搜索、文件检索、浏览器和代码执行底座，而是在 `RuntimeGateway` / `CapabilityPlane` 下面新增 `HostedToolProvider`，把调用、成本、证据、审批都映射回你自己的 run/task 模型。([OpenAI][1])

### 2) MCP 生态：应该作为主能力接缝，而不是旁路

MCP 官方架构已经把 host / client / server、local stdio 和 remote Streamable HTTP 的边界定义得很清楚；而对涉及用户数据或管理动作的远程 server，官方也明确建议采用 OAuth 2.1 风格授权。你现有 `capability_plane.py` 已经有很好的接缝，所以不该再造私有“工具协议”，而应把 MCP 作为一等公民：统一 capability descriptor、transport、auth、scope、healthcheck、quota、审计。([Model Context Protocol][2])

### 3) OTel + Langfuse：观测后端不要自己造

OpenTelemetry 是 vendor-neutral 的埋点/导出标准，不是后端本身；Langfuse 也支持经 OTel 接入，并建议优先走 SDK/OTel 路径。你已经有 `observability.py`，所以最正确的路线不是继续维护私有 trace schema，而是把 run / task / worker / tool call 映射成 OTel spans 和 attributes，再把导出器接到 Langfuse 或任意 OTLP backend。这样以后要换观测后端，系统内核不用跟着重写。([OpenTelemetry][3])

### 4) GitHub Checks + GitHub Actions：代码协作层直接接现成能力

GitHub Checks API 能承载 rich status、行级注释和重新运行；GitHub Actions 又能把测试/构建外包给 hosted 或 self-hosted runners。你已经有 `repo_mutation.py` 和 review 入口，所以很适合把 patch、review、test、annotation 投影到 PR checks，而不是自己再造一套代码托管/CI 展示层。([GitHub Docs][4])

### 5) Playwright MCP：浏览器能力直接接，不建议自研 browser worker

Playwright 的 MCP server 已经把浏览器控制暴露成 MCP 能力，而且使用结构化 accessibility snapshots；Playwright CLI 也明确面向 coding agents 做了 token-efficient 的浏览器控制设计。你们如果后面要做网页调研、表单操作、控制台验证，直接把它接成 `browser.playwright` capability，比自己维护 DOM 解析、状态同步、截图语义都划算。([Playwright][5])

### 6) Temporal：只在长时任务/等待/回调场景接入，不要拿来替代整套控制平面

Temporal 的强项是 durable workflow state、失败后恢复，以及 activities 的 retry / timeout。它适合承接“外部长时间执行、等待人工、等待第三方回调、跨进程恢复”这些场景；但不适合拿来替代你已经写好的审批、治理、证据和 run 真相源。正确整合方式是：**SQLite run 仍是业务真相源，Temporal workflow id 只是 external execution handle。**([Temporal 文档][6])

### 7) 向量检索：后面需要时再接，不要现在半自研

pgvector 适合未来如果你们把状态层迁到 Postgres，希望向量和业务数据放在一起；Qdrant 更适合把记忆层独立出来，尤其在向量 + sparse/text retrieval 混合场景下。当前这套系统还是 SQLite local-first，我不建议现在就为了“看起来更 agentic”而先造一个半成品 semantic memory；等跨 run 记忆、检索和长上下文复用成为刚需时再接。([GitHub][7])

## 6. 如何整合外部资源进这个系统

我建议不要“每接一个外部能力就写一条特例逻辑”，而是统一走两层契约。

### 第一层：CapabilityDescriptor

每个外部能力都注册成一个统一描述对象，至少包含：

* `capability_id`
* `provider_kind`：`builtin` / `mcp_stdio` / `mcp_http` / `responses_tool` / `github` / `temporal` / `vector_store`
* `auth_mode`
* `scopes`
* `allowed_task_kinds`
* `cost_class`
* `latency_class`
* `side_effect_level`
* `evidence_schema`

### 第二层：ResultEnvelope

所有外部调用结果都统一成一个结果对象：

* `summary`
* `raw_ref`
* `artifacts`
* `evidence`
* `mutations`
* `verification`
* `usage`
* `provenance`
* `confidence`

然后系统内部只做四件事：

1. planner 按 task kind 和 policy 选 capability
2. gateway 负责调用和重试
3. governance 负责审批和 side-effect 约束
4. projection 负责把结果投影成 UI / artifact / audit log

这样外部资源越多，系统越稳；否则外部资源越多，系统越像一堆 hardcode。

## 7. 未来规划

我建议下一阶段按这个顺序推进：

**第一阶段：基线硬化。**
先把仓库交付、导出、验证、golden replay 做扎实，解决“我看到的到底是不是一个可信版本”。

**第二阶段：能力平面产品化。**
把 capability registry、optional deps、auth/scope、ResultEnvelope、trace 统一起来，让外部能力接入变成标准动作。

**第三阶段：受控自治。**
把固定模板编排升级成 DAG + policy 驱动；引入质量门、人工介入点、成本门、失败恢复语义。

**第四阶段：知识与多域扩展。**
在控制平面稳定后，再去做更强的 memory、多 domain pack、跨项目协同和长期知识复用。

## 最后一句判断

这版最值钱的不是某个 agent adapter，而是你已经开始形成的**控制面思维**：生命周期、审批、投影、证据、worker 边界、repo mutation 安全带。
所以下一步最重要的，不是再加更多角色和更多 prompt，而是：

**把基线做干净，把 commodity 能力外接，把内部精力集中到治理、证据、审批、编排这几个真正差异化的地方。**

如果你愿意，我下一步可以直接按这个结论，给你出一版更落地的 **“重构路线图 + 模块拆分方案 + 外部能力接入架构图”**。

[1]: https://openai.com/index/new-tools-and-features-in-the-responses-api/ "New tools and features in the Responses API | OpenAI"
[2]: https://modelcontextprotocol.io/docs/learn/architecture "Architecture overview - Model Context Protocol"
[3]: https://opentelemetry.io/docs/what-is-opentelemetry/ "What is OpenTelemetry? | OpenTelemetry"
[4]: https://docs.github.com/en/rest/guides/using-the-rest-api-to-interact-with-checks "Using the REST API to interact with checks - GitHub Docs"
[5]: https://playwright.dev/docs/getting-started-mcp "Playwright MCP | Playwright"
[6]: https://docs.temporal.io/workflow-execution "Temporal Workflow Execution overview | Temporal Platform Documentation"
[7]: https://github.com/pgvector/pgvector/blob/master/README.md "pgvector/README.md at master · pgvector/pgvector · GitHub"
