## 总体结论

这轮开发**明显把项目从“容易自研漂移的平台”拉回到了“可信 workflow 控制塔”方向**。现在可以认为已经形成了一个比较扎实的 **M72 Trusted Self-Development Baseline**：高风险动作边界、provider 真实性、并发执行契约、文档真相源、self-development manifest 都比之前强很多。README 和当前开发工作流也都把当前状态收敛到 M72，并明确下一阶段是 M73 能力层开发。 

但我不会把它评价为“长期架构已经完成”。更准确地说：

```text
现在完成的是：
可信自开发底座 / workflow dogfood governance baseline

还没真正完成的是：
LangGraph runtime substrate
AutomationLease / PolicyEngine 完整自主授权层
MCP Broker / per-task tool projection
能力层真实扩展与业务闭环
```

所以当前判断是：

```text
M73 能力层开发：GO
但必须继续带着 scoped receipt、live probe、manifest、并发契约和 bug-first gate 前进。
```

---

# 1. 已经做得很好的部分

## 1.1 文档真相源收口成功

之前最大的问题之一是文档和代码事实不一致：M66/M67/M68/M72、长期路线、旧评估报告混在一起，容易误导后续 AI。现在 README、`current_development_workflow.md`、`AGENTS.md` 都把当前接受基线统一为 M72，并明确历史评估、旧执行报告、长期路线图归档到 `docs/archive/evaluations/`。 

M73 两轮深度评估也做得比较稳：第 1 轮发现历史执行报告滞留根目录、manifest 查找逻辑与归档规则不一致；第 2 轮确认 M67-M71 已归档、manifest 能识别归档报告、活动文档不再声明 zero open debt / Gemini CLI 已接入 / gcloud 是 worker adapter / 分布式 scheduler authority 等错误事实。 

这点非常重要。对你的项目来说，**文档不只是说明书，而是后续 AI agent 的行为约束**。这一轮把“AI 读错旧材料然后继续跑偏”的风险降低了很多。

---

## 1.2 高风险动作边界明显增强

M67 P2 把 `OperatorActionReceipt` 升级为 scope-bound receipt：不再只是“这个动作类型被确认过”，而是绑定到具体请求 scope，例如 run_id、goal、preset_id、execute=true、batch run_ids、watchdog apply 参数等。M67 报告里明确写到 `/runs/launch execute=true`、interaction session launch、reconcile apply、watchdog auto-apply 都被绑定到 scope。

代码层也能看到这个机制真实存在：`OperatorActionGuard` 对 high-risk actions 要求 `scope_hash`，消费时会重新计算实际 request scope，如果 hash 不匹配就拒绝；同时还检查 action_type、workspace_root、issued 状态、expiry 和 single-use consume。

API 路径也已经修了关键问题：`/runs/launch` 在 `execute=true` 时消费 `launch_execute` receipt，并把 `goal/preset_id/execute` 作为 scope；resume、approve、reject、cancel、batch-resume、reconcile apply 都绑定了对应 scope。

watchdog 之前最危险的 GET mutate 问题也被修掉了：GET `/interaction/watchdogs/evaluate?auto_apply=true` 现在直接 400，真正 apply 改为 POST `/interaction/watchdogs/evaluate/apply` 且要求 `watchdog_auto_apply` scoped receipt。

测试也不是只测 happy path，而是覆盖了缺 receipt、action type 不匹配、receipt 重用、scope tamper、legacy receipt 无 scope_hash、launch body tamper、batch run_ids tamper、watchdog GET/POST 等场景。

这一块我会给 **A-**。还不是完整 PolicyEngine/Lease，但当前 receipt 边界已经比之前可信很多。

---

## 1.3 Provider 真实性和 capability readiness 收口得很好

M67 P3 把 provider live proof 变成硬门槛，明确拒绝 generic greeting、simulated、dry-run、fallback-only、minimal ok 之类假 ready。M72 报告也说 provider live probe 全部通过，但后续凭据、配额、外部服务失败必须记 blocker，不能伪造 ready。 

M70 又把 provider facts 收敛到 provider contract registry，明确了现在已接入 Shell、Codex、OpenCode、Claude、MMX/MiniMax、Vertex、LangChain；同时澄清 Gemini CLI 未接入、Gemini-family 能力当前通过 Vertex/GCP、`gcloud` 只是凭据/环境工具不是 worker adapter。

`capability_control_plane.py` 也已经有 provider contract registry，并在 policy decision 里返回 provider contract、live proof、mutation mode、write_set、receipt status 和 reasons。

这解决了你项目之前一个很大的隐患：**AI 容易把“配置了 provider”误读为“provider 已真实可用”**。现在 readiness 更接近事实。

---

## 1.4 并发执行契约比之前成熟很多

M71 把 `batch-resume` 从“直接开线程跑”提升为可审计的并发执行契约：执行前生成 parallel batch plan，记录是否启用 barrier、是否降级串行、降级原因、write_set 审计、dirty worktree 审计、SQLite 可用性检查、partial failure resume 指针。

`parallel_execution_contract.py` 里确实实现了 write_set conflict、dirty write_set、SQLite lock 的串行降级，并返回 execution_mode、barrier_enabled、degraded_reasons 和 audit。

这对你的长期目标很重要。你要让 workflow 长程参与自己开发，并且需要无人值守一段时间，那么并发不可能只靠“max_workers=N”。现在至少有了一个可审计的并发前置契约。

---

## 1.5 Self-development manifest 是一个很好的治理入口

M72 新增 `workflowctl governance self-development-manifest`，可以扫描 M67-M72 的执行报告、state evidence、task cards、operator packets 和 git commits，输出 GO/NO-GO，并固化“phase 默认多 task card，单卡必须显式 single_card_exception”的规则。M72 报告里 final manifest 是 GO，并且 full slow pytest 462 passed。

代码层看，manifest 会查根目录和 archive 执行报告路径，扫描 state 下 task_cards/evidence/operator_packets，检查 task-card policy 和 blocking issues，并收集 git log 里的 milestone commits。

这不是业务能力，但非常关键。它把“工作流自开发是否真的有证据”从人类叙述变成机器可检查入口。

---

# 2. 仍然要挑刺的地方

## 2.1 LangGraph 仍然不是 runtime substrate

这是当前最重要的边界判断。

M68 的 LangGraph 集成是安全的、保守的、可忽略的，但它**不是**真正 runtime substrate。M68 报告明确写了：只接入 `planning -> review -> evidence` 的受控子图，是 opt-in advisory runtime，不 compile、不 resume、不 patch apply，也不作为新的 workflow 状态源；它只读取现有 workflow route preview，并在显式 evidence dir 下写 JSON。

这说明你已经避免了“假装全面迁 LangGraph”的风险，但也意味着：**之前讨论的 LangGraph 接管图执行、checkpoint、interrupt、resume、subgraph execution，目前还没有真正发生。**

`pyproject.toml` 里 optional `m8` 只包含 `langchain/langchain-openai/langgraph`，没有 `langgraph-checkpoint-sqlite`，所以也还没有进入 SQLite checkpoint / durable runtime substrate 阶段。

我会给 LangGraph 集成打 **C+ / B-**：

```text
优点：
- 安全
- opt-in
- 不污染 core/contracts
- 没制造双状态源
- 有 route comparison evidence

不足：
- 仍是 advisory-only
- 不承担真正 runtime
- 没有 checkpoint/resume/interrupt 落地
- 没有减少 OrchestrationEngine / durable runtime 的核心重复造轮子
```

当前策略应该是：**不要立刻扩大 LangGraph mutation runtime，但下一步如果继续做 runtime 相关功能，就必须先做真正 LangGraph substrate spike。**

---

## 2.2 PolicyEngine / AutomationLease 还没有真正落地为一等对象

你现在有了 scoped receipt 和 capability control-plane policy，但从代码搜索结果看，`PolicyEngine` 和 `AutomationLease` 这两个名字主要还停留在归档规划文档中，没有作为一等模块/服务出现。实际落地的是：

```text
OperatorActionReceipt v2：单次 scope-bound human confirmation
Capability control-plane：provider live proof + write_set + receipt metadata 的 policy decision
```

这比之前强很多，但还不是我们之前说的：

```text
我授权你在 8 小时内，在这个 workspace / branch / write_set / action set 内无人值守执行
```

也就是说，**当前系统适合“每个高风险动作有 scope-bound receipt”，但还不是真正的 bounded autonomy lease。**

这并不是 M72 的 blocker，因为 README/AGENTS 现在也没有声称 AutomationLease 已完成。但对你“长程任务个人无法长期守着”的需求来说，这是下一阶段必须补的。

---

## 2.3 Capability control-plane 仍偏“观察式”，还不是全路径强制门禁

M69 报告写得很诚实：capability control-plane policy decision 会合并 provider live proof、mutation write_set、operator receipt 元数据，但本阶段保持观察式集成，不会突然改变既有 run 执行成功语义；CLI control-plane check 会对非 allowed 判定返回非零，方便无人值守 gate 使用。

这说明现在还处在：

```text
policy decision 进入 ledger / evidence / CLI gate
```

还没有完全进入：

```text
所有真实执行路径必须先经过 capability policy allow
```

这条路线是对的，因为一次性强制会破坏很多旧路径。但 M73 不应该继续只加 evidence。下一步应该选一个很小的真实执行路径做 enforcement pilot，例如：

```text
patch_apply + adapter_route:opencode
或者
capability control-plane CLI + run compile/resume 之间的一条 gate
```

否则 capability control plane 可能会变成“报告系统”，而不是“控制系统”。

---

## 2.4 MCP 仍然不是 MCP Broker

`capability_plane.py` 里 MCP 已经不是全量裸奔：MCP 是 optional dependency，profile 有 enabled、allowed_tools、max_tools、max_schema_bytes，`build_projection_manifest()` 默认 `include_mcp=False`。这比“所有 MCP 工具暴露给 agent”安全。

但它还不是我们前面定义的 MCP Broker。问题包括：

```text
1. include_mcp=True 时仍是所有 enabled profiles 的白名单工具一起进入 projection。
2. 还没有 task_kind / preset / cluster / lease / policy 维度的 per-task projection。
3. call_tool(tool_name, args) 仍按 tool_name 遍历 profiles，未来多个 profile 都有 search/read/query 时会有歧义。
4. 还没有 canonical id：mcp:{profile_id}:{tool_name}。
5. risk tier 仍偏粗，基本 read_only，没有 local_write/network/external_side_effect 的系统分级。
```

所以 MCP 目前我会给 **B-**：方向对，粗粒度安全有了，但还没进入“按任务最小工具投射”。

---

## 2.5 并发 write_set 检查可能还偏保守/偏浅

`parallel_execution_contract.py` 会把路径 normalize 后做 exact conflict 检测，并在 dirty path exact 命中 write_set 时降级串行。

这对当前已有 task card 可能够用，但如果后续 write_set 可以是目录、glob、相对路径模式，就有潜在漏判。例如：

```text
Run A write_set: packages/core_domain
Run B write_set: packages/core_domain/foo.py
```

如果系统只做 exact equality，可能不会认为冲突。后续 M73/M74 若要让更多 coding agent 并发写代码，应把 write_set 规则升级为：

```text
exact path conflict
prefix containment conflict
glob expansion conflict
case-insensitive Windows path conflict
generated artifact path conflict
```

这不是当前 blocker，但应该加入 M73/M74 的并发契约增强项。

---

## 2.6 Self-development manifest 是“完整性检查”，不是“语义真实性检查”

manifest 很有价值，但它目前主要检查：

```text
execution report 是否存在
state directory 是否存在
task cards 数量是否满足规则
evidence 文件是否存在
operator packet 是否存在
git log 是否包含 milestone commit
```

这些是完整性检查。它还没有深度验证：

```text
task card -> run_id -> evidence -> test output -> commit SHA 是否一一对应
evidence schema 是否符合预期
operator packet 是否真的覆盖所有 write_set/test/evidence
report 中的 “passed” 是否能回链到机器产物
```

M73 第 2 轮已经确认 manifest 能识别归档报告并保持 GO，这是好事。 但如果未来你越来越依赖 manifest 作为“可信开发完成”的核心证明，建议做 manifest v2：从“文件存在”升级到“证据可追溯”。

---

## 2.7 热点文件债务还在

M67 P7 已经把 `services.py` 降到 1801 行，拆出了 RepositoryBundle/WorkerRuntimeBundle、若干 mixin、game template、test matrix 等。

但 tech debt registry 仍保留 `M67-CARRY-001`：`repositories.py`、`service_lifecycle.py`、`service_projection.py`、`interaction_catalog.py`、`models.py` 仍偏大，计划 M73+ 能力驱动维护；当前 status 是 non-blocking carry_forward。

这个处理方式是对的：不要为了瘦身而瘦身。但下一阶段每次能力开发碰到这些文件时，要顺手建立 ratchet，不要继续无上限膨胀。

---

# 3. 分项评分

| 维度                       | 评分 | 评价                                                     |
| ------------------------ | -: | ------------------------------------------------------ |
| 战略方向收口                   | A- | 已从“自研平台漂移”拉回 local-first workflow control tower        |
| 文档真相源                    | A- | README/current workflow/AGENTS/M72/M73 基本统一            |
| 高风险动作边界                  | A- | scoped receipt 做得扎实，测试覆盖关键 tamper 场景                   |
| Provider readiness       | A- | live proof 和 provider contract 明显增强                    |
| Capability control-plane | B+ | policy decision 已落地，但还偏 observation-style              |
| 并发执行契约                   | B+ | 有 barrier/degrade/audit，后续需增强 path conflict 语义         |
| LangGraph 集成             | C+ | 安全但浅，advisory-only，不是 runtime substrate                |
| MCP 按需接入                 | B- | profile 白名单 + include_mcp 默认 false，但不是 per-task broker |
| 自开发治理                    | A- | manifest 是很好的入口，后续可做 v2 provenance                     |
| 架构瘦身                     |  B | 热点明显改善，但大 repository/model/test 文件仍在                   |
| M73 能力层准备度               | GO | 可以进入，但要继续 gate，不可放松                                    |

---

# 4. 下一步建议

## M73 的主题不应是“再写一堆功能”，而应是“能力层真实落地”

我建议 M73 拆成 4 条主线。

### M73A：Capability enforcement pilot

目标：把 M69 的 policy decision 从 evidence/CLI gate 推进到一条真实执行路径。

建议选一条最小路径：

```text
adapter_route + patch_apply + write_set + receipt + live proof
```

验收标准：

```text
1. 缺 live proof => 不执行 mutation
2. 缺 write_set => blocked
3. 缺 receipt => needs_receipt / forbidden
4. allowed => 执行并写 execution receipt
5. 所有 decision 进入 ledger
```

不要一开始全路径强制，否则容易破坏历史兼容。

---

### M73B：MCP Broker v1

目标：把当前 MCP profile whitelist 升级成真正 per-task broker。

最低实现：

```text
1. canonical id: mcp:{profile_id}:{tool_name}
2. call_tool 必须支持 canonical id
3. 同名 tool collision 测试
4. projection 支持 profile/tool selector
5. include_mcp=True 不再等于所有 enabled profiles
6. task_kind / preset / review_policy 最小过滤
7. schema budget 和 risk tier 进入 manifest
```

先不要接更多 MCP。先把机制做好。

---

### M73C：AutomationLease v0

如果你确实需要无人值守长程任务，现在就该补这一层。不要做复杂权限系统，只做最小 lease：

```text
lease_id
workspace_root
allowed_actions
denied_actions
write_set_allowlist
expires_at
max_resume_count
max_fix_iterations
status
```

第一版只允许：

```text
resume_run
batch_resume_runs
run_tests
write_artifact
advisory review approve
```

继续禁止：

```text
git push / PR / publish
secrets
workspace_root 扩大
未知外部副作用
```

它可以复用 scoped receipt 的思想，但必须支持多次、有界、可撤销。

---

### M73D：LangGraph 只做一个“真 runtime spike”，不要扩大 mutation

当前 M68 是 advisory-only。下一步如果继续 LangGraph，建议做一个 non-mutating but real-runtime spike：

```text
Plan
→ Review interrupt
→ Resume
→ Evidence
```

必须包含：

```text
checkpoint
interrupt
resume
state inspection
streaming event
```

但仍不要碰 patch apply。等这条稳定后，再考虑是否把 cluster/subgraph execution 迁进去。

---

### M73E：Manifest v2 provenance

目标：让 manifest 不只是“文件存在”，而是“证据链可追溯”。

建议加：

```text
task_card_id
run_id
operator_packet_path
evidence_paths
test_command
test_result_path
commit_sha
write_set
decision
```

并检查：

```text
task card 数量
task card -> evidence 有链接
operator packet 覆盖所有 task card
报告中的 passed 命令能找到 evidence
commit message 包含 milestone/phase
```

---

# 5. 最终判断

这轮开发的方向总体是对的，而且完成度比我预期高。你现在已经不再是“只是写了一堆文档和 demo”，而是有了：

```text
scoped high-risk receipt
provider live-proof hard gate
provider contract registry
capability control-plane decision
parallel execution contract
self-development manifest
文档真相源治理
M73 复评机制
```

这些都是 workflow 控制塔真正需要的东西。

但要避免一个新的误判：**M72 不是能力层完成，也不是 LangGraph 迁移完成。M72 是可信开发底座完成。**

当前最准确的状态是：

```text
可信底座：基本完成
能力治理：第一版完成，需进入 enforcement
MCP Broker：未完成
AutomationLease：未完成
LangGraph runtime substrate：未完成，只有 advisory focused runtime
业务闭环：尚未开始真正验证
```

所以我建议你现在可以进入 M73，但 M73 的第一目标应该是：

```text
把 capability control plane 从“可见”推进到“可控”；
把 MCP 从“profile 白名单”推进到“per-task broker”；
把无人值守从“scope receipt”推进到“bounded lease”。
```

这三件事做完后，再去扩更多 MCP、更多 CLI agent、更多 cluster，项目才不会再次膨胀失控。
