# M66 收口后项目深度评估报告

生成日期：2026-04-25

## 评估范围

本报告针对当前 M66 收口后的仓库状态做一轮 bug-first 深度评估，重点交叉检查当前真相源、代码结构、测试门禁、本地 evidence，以及 M61-M66 收口报告中的关键声明。

主要输入：

- `README.md`
- `M61_M66_ISSUE_REGISTER.md`
- `M61_M66_EXECUTION_REPORT.md`
- `docs/governance/tech_debt_registry.json`
- `.github/workflows/ci.yml`
- 核心 runtime / API / CLI / Web / core-domain 模块
- `state/m61_m66_execution/capability_probes/` 下的本地能力探针证据

## 当前验证快照

本轮评估期间实际运行的命令：

| 命令 | 结果 |
| --- | --- |
| `workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" doctor --strict` | 通过 |
| `python -m infra.scripts.check_doc_links` | 通过，检查 7 份 living docs |
| `workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite unit` | 通过，52 tests，约 13 秒 |
| `workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite core` | 通过，87 tests，约 71 秒 |
| `python -m infra.scripts.offline_validation --skip-offline-probe` | 本轮在 184 秒处超时 |

需要先明确一点：当前项目不是“基础不可用”的状态。doctor、doc links、unit matrix、core matrix 都是绿的。下面的问题主要集中在：事实声明是否足够诚实、门禁覆盖是否完整、安全边界是否够硬、架构拆分是否真正到位。

## 总体结论

M61-M66 确实让项目变健康了不少：CLI 主入口已经变薄，chat runtime 已经拆成 package facade，Web UI 高风险动作已经接入 receipt gate，scheduler flag-off 隔离有测试覆盖，CI 已经存在，core tests 也能通过。

但当前最大的问题是：治理收口结论过于乐观。活跃文档里写着 M61-M66 blocking open debt 为零，并且所有 provider live probe 都通过；但本地 evidence 显示，至少一部分 provider probe 仍然是模拟输出、泛泛问候或未强制真实 API 调用。这意味着系统仍可能把“模型生成了一个响应”误记为“外部能力真实可用”。

下一阶段不应该扩功能，应该先把证据语义、验证可靠性、CI 覆盖、安全边界补硬。然后再继续做剩余架构拆分。

## 问题清单

### P0：Capability live probe 仍可能产生假阳性

证据：

- `M61_M66_EXECUTION_REPORT.md` 声称 `workflowctl ... capability probe --provider all --require-live ...` 通过，`blocked_count = 0`。
- `state/m61_m66_execution/capability_probes/vertex_probe.md` 中包含“Simulated Probe Action”，并明确表示无法直接访问外部系统或执行真实世界交互。
- `state/m61_m66_execution/capability_probes/langchain_probe.md` 中给出了计划执行的命令，但同时写到实际 API call 没有被强制执行，属于 dry-run path。
- `state/m61_m66_execution/capability_probes/claude_probe.md` 只有泛泛问候。
- `packages/core_domain/capability_probe.py` 中，对 `codex` 和 `opencode` 有更严格的 proof artifact 判断；但对 MMX、Vertex、Claude、LangChain 等 provider，仍然基本依赖“return code 为 0 且 stdout/artifact 非空”。

影响：

系统可能把模拟输出、泛泛响应、甚至明确声明没有真实外部交互的 artifact 标记为 `verified_ready`。这会直接动摇 M64/M66 最关键的结论：“全部 provider 必须真实实测通过”。

建议：

- 所有 provider 都必须使用 provider-specific live-proof contract，不能只给 Codex/OpenCode 做强校验。
- `--require-live` 模式下，如果 evidence 中出现 simulated、dry-run、cannot access external systems、actual API call not forced 等语义，应直接判为 blocked。
- 结构化 evidence 至少包含：`status=ok`、`probe=executed`、`adapter`、`provider`、`auth_source`、`no_fallback=true`、`live_backend=true`，以及 provider 专属 proof 字段。
- 给 MMX、Vertex、Claude、LangChain 增加“泛泛输出/模拟输出必须拒绝”的回归测试。
- 修完 parser 后重新跑 all-provider probe，再更新 M61-M66 report。

### P1：offline validation 作为常规门禁还不够可靠

证据：

- 本轮运行 `python -m infra.scripts.offline_validation --skip-offline-probe` 在 184 秒处超时。
- 仓库里仍有旧的 `state/offline_validation_report.json`，如果 fresh run 超时，operator 很容易误读旧报告。
- M61-M66 report 把 offline validation 写成 closeout 必跑门禁。

影响：

这个门禁目前不够短、不够稳，也不够可定位。超时后如果没有新的失败报告，就很难判断是仓库真的坏了、某个步骤卡住了，还是只是执行太慢。

建议：

- 把 offline validation 拆成 named shards，并记录每个 check 的耗时。
- 超时或中断时也要写出明确失败报告，包括 `started_at`、`finished_at`、`timeout_seconds`、最后完成的 check、以及 stale report warning。
- 增加 `workflowctl validation run --suite quick|full --shard N/M`，或把它并入现有 test matrix。

### P1：CI 没覆盖几块最近最容易回归的风险区

证据：

- `.github/workflows/ci.yml` 当前运行 doc links、doc command smoke、doctor strict、`make test-core`、offline validation。
- `make test-core` 不包含 `tests/test_capability_probe.py`、`tests/test_web_ui.py`、`tests/test_api.py`、`tests/test_cli.py`、`tests/test_test_matrix.py`。
- unit matrix 也没有包含 `tests/test_capability_probe.py`。

影响：

最近刚修过、也最容易再次出问题的区域没有进入默认 CI 核心路径。比如 capability probe false positive、Web receipt gate、test matrix 本身，都可能在 CI 绿灯时悄悄回归。

建议：

- 把 `tests/test_capability_probe.py` 和 `tests/test_test_matrix.py` 加入 unit 或 core。
- 给 Web/API 高风险 receipt 路径加一个小型 smoke，放进 core，而不是只靠完整 integration suite。
- provider-live 的真实外部探针可以继续保持人工或计划任务触发，但 parser 级别的 false-positive 测试必须进普通 CI。

### P1：Web CSP 仍弱于安全叙事

证据：

- `apps/orchestrator_api/main.py` 中 CSP 仍是 `script-src 'self' 'unsafe-inline'` 和 `style-src 'self' 'unsafe-inline'`。
- `apps/orchestrator_api/web_ui_components.py` 仍内嵌一个 `<style>`、一个 `<script>`，还有多个 inline `style=`。
- 当前 decomposition ratchet 只检查 `web_ui.py <= 700` 以及 Web UI 源码中没有 `innerHTML`，并没有禁止 inline script/style。

影响：

receipt gate 已经显著改善状态变更安全，但浏览器侧防线仍然偏软。未来任何模板逃逸失误，都无法充分依赖 CSP 做兜底。

建议：

- 把 CSS 和 JavaScript 移到本地静态资源。
- 移除生成 HTML 中的 inline `style=`。
- 将 CSP 收紧到 `script-src 'self'`、`style-src 'self'`；如果短期必须保留 inline，则使用 nonce/hash，并明确 TODO。
- 增加测试覆盖 CSP header 和 operator UI 中 inline script/style 的缺失。

### P1：治理层“zero open debt”表达过于绝对

证据：

- `README.md` 写着 M61-M66 blocking open debt 为零。
- `docs/governance/tech_debt_registry.json` 中 `"open_items": []`。
- `M61_M66_ISSUE_REGISTER.md` 同时又写着 deeper repository bundle cleanup 可以作为 non-blocking M67 debt 继续。
- 本轮评估已经发现 capability truth、offline validation、Web CSP、CI coverage 等新的 P0/P1/P2 问题。

影响：

“open debt = 0”只在 M61-M66 那个限定 register 内成立，但读起来很容易变成“项目已经没有重要问题”。这会制造治理盲区。

建议：

- 技术债登记表拆成 `blocking_open`、`nonblocking_carry_forward`、`repaid`、`obsolete`。
- 重新登记 capability live-proof semantics、offline validation timeout、Web CSP hardening、CI coverage gaps。
- closeout report 中明确区分“本轮 scope 已关闭”和“项目没有已知债务”。

### P2：架构拆分明显改善，但核心面仍然偏集中

当前行数快照：

| 文件 | 行数 |
| --- | ---: |
| `packages/core_domain/services.py` | 2334 |
| `packages/core_domain/service_interaction_chat.py` | 1285 |
| `packages/core_domain/service_interaction_session.py` | 612 |
| `packages/core_domain/service_interaction_cluster.py` | 608 |
| `packages/core_domain/local_scheduler_lease_arbiter.py` | 809 |
| `packages/core_domain/scheduler_authority.py` | 1650 |
| `apps/orchestrator_api/web_ui_components.py` | 875 |

证据：

- `OrchestratorService.__init__` 仍然直接装配大量 repository、adapter、worker router、runtime gateway、capability plane、scheduler cluster/arbiter 和 helper service。
- Ratchet 能证明项目比之前瘦了，但 facade 仍然是一个很大的对象图构造器。

影响：

构造面过大，会让 import 成本、测试隔离、feature flag 行为更难推理。后续新功能也容易重新堆回 facade。

建议：

- 抽出 typed `RepositoryBundle`。
- 抽出 `WorkerRuntimeBundle`，统一管理 adapter/router 构造。
- 下一轮 ratchet 建议：`services.py <= 2000`、`service_interaction_chat.py <= 900`、`local_scheduler_lease_arbiter.py <= 650`。
- 增加 bundle 独立构造测试，并继续保证 flag-off 时 import 干净。

### P2：scheduler 命名在用户可见界面里仍有残留

证据：

- 活跃文档已经正确说明默认语义是 local-first `LocalSchedulerLeaseArbiter`。
- 但 Web UI 里仍有“调度权威拓扑”“权威节点”“权威任期”等文案。
- CLI help 仍写着 “Scheduler authority and cluster inspection commands.”

影响：

代码层保留 compatibility 命名可以理解，但默认用户界面继续使用“权威”字样，会让人误以为默认提供了更强的分布式 authority/consensus 语义。

建议：

- 默认 UI 文案改成“调度租约仲裁”“仲裁节点”“租约任期”等更准确的表达。
- `scheduler-authority` 只保留在兼容文档和 cluster-on 路径说明中。
- 增加默认 local-only UI copy 测试。

### P2：生成游戏 artifact 模板仍使用 `innerHTML`

证据：

- `packages/contributions/games/local_game_artifacts.py` 中生成的浏览器游戏模板仍有 `innerHTML`。
- Web UI decomposition test 只检查 `apps/orchestrator_api/web_ui.py` 和 `web_ui_components.py`，不覆盖 contribution-generated browser surfaces。

影响：

这不是 operator Web UI 主路径，所以优先级低于 CSP。但它仍然是浏览器 surface，如果未来把模型/用户文本插入模板，就会产生 XSS 风险。

建议：

- 清空节点时使用 `replaceChildren()`。
- 动态文本使用 `textContent`，复杂结构使用 DOM API 创建节点。
- 给 contribution HTML/JS 模板增加安全模式测试。

### P2：广义 `except Exception` 仍可能掩盖 provider/API 漂移

证据：

- chat runtime、capability probe subprocess parsing、lifecycle cleanup、gateway、observability 等路径仍有多个 broad `except Exception`。
- 一部分是合理边界 catch，但也有一些会把未知 provider/schema 错误折叠成普通 degraded/blocked。

影响：

真实根因会变得不容易定位。对 bug-first 工作流来说，这会降低“先修 workflow 自身 bug”的效率，因为失败分类不够清晰。

建议：

- 引入更细的 failure class：provider schema mismatch、auth failure、timeout、subprocess parse failure、empty output、simulated evidence 等。
- 保留边界 catch，但必须记录原始异常类型、稳定 remediation hint 和 failure class。
- 增加 malformed provider response 的分类测试。

### P2：release evidence 多数仍是本地 ignored 状态

证据：

- `.gitignore` 忽略 `state/*`。
- M61-M66 report 引用了 `state/m61_m66_execution/...` 下的 task cards、workflow bug queue、capability probes 等证据。

影响：

报告本身是 tracked 的，但很多支撑证据不是。fresh clone 无法独立审计这些 closeout 证据，除非另有导出。

建议：

- 每次 closeout 导出一份 tracked evidence manifest，包含命令、时间戳、return code、hash、redacted summary。
- raw state 继续 ignored，但至少保留可审计的摘要和路径哈希。
- 当报告引用 ignored local path 时，增加 stale/missing evidence warning。

## 当前做得好的地方

- 当前主分支是 clean 且已推送状态。
- `doctor --strict`、doc links、unit matrix、core matrix 全部通过。
- scheduler flag-off import isolation 有测试，且当前仍为绿。
- `apps/operator_cli/main.py` 已缩到 96 行。
- `packages.runtime_langgraph.chat_runtime` facade 只有 47 行，并保留旧 import 兼容。
- API import 不再隐式迁移默认 DB，已有 startup coverage。
- 高风险 API path 已有 operator receipt 测试。

## 建议的下一阶段计划

### M67：Evidence Truth Hardening

目标：优先修 P0。

- 为所有 provider 建立 provider-specific `CapabilityProbeResult` proof contract。
- `--require-live` 下拒绝 simulated/dry-run/generic evidence。
- 扩展 `tests/test_capability_probe.py`，覆盖所有 provider 的 false-positive 情况。
- 严格 proof 通过后，重新跑 all-provider probe，并更新 M61-M66 report。

### M68：Validation And CI Reliability

- 拆分 offline validation，并让 timeout 也产生明确 evidence。
- 将 capability probe parser tests 和 Web/API receipt smoke 纳入 CI。
- 避免 stale validation report 被误读成 fresh success。

### M69：Web Security Hardening

- 将 Web UI CSS/JS 移到 static assets。
- 移除 CSP 中的 `unsafe-inline`。
- 替换 contribution template 中的 `innerHTML`。

### M70：Architecture Ratchet

- 抽出 `RepositoryBundle` 和 `WorkerRuntimeBundle`。
- 继续降低 `services.py`、`service_interaction_chat.py`、scheduler arbiter 的体量。
- 保持旧 public imports、CLI 命令、API route 兼容。

### M71：Governance Truth Reset

- 用本报告发现的 P0/P1/P2 重新登记 open/carry-forward debt。
- 区分 blocking debt 和 non-blocking carry-forward debt。
- 导出 tracked closeout evidence manifest。
- 在 M67-M71 收口前，把“zero open debt”改成“上一轮限定 scope 内无 blocking open debt”。

## 最终判断

项目比 M61 前健康很多，基本运行面是可用的；但它还没有达到“事实层完全可信”的状态。当前最应该优先修的是 capability probe 的假阳性路径：现在的 evidence 能证明某个 agent 生成了响应，却可能被治理层记录成外部 provider 真实可用。这是下一阶段恢复“诚实 all-clear”状态的首要阻塞项。
