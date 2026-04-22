# M34 Post-Evaluation：当前状态与 M35/M36 方案评估

> 评估时间：2026-04-22
> 评估基线：M34 Phase 0 accepted（最新冻结评审）
> 评估范围：M31→M34 的三轮开发成果 + M35/M36 产品化计划
> 本地测试：280 passed / 2 failed / 覆盖率 88.94%

---

## 一、自上次评估以来发生了什么

上次评估基线是 M31 Phase 0（278 passed）。此后完成了三个完整的里程碑闭环：

| 里程碑 | 主题 | 关键交付 | 测试 |
|--------|------|---------|------|
| M32 Phase 0 | Interaction / Profile / Cluster Foundation | IntentSession、AgentProfile、ExecutionClusterTemplate、DevCluster/ResearchCluster、最小 workbench preview | 281 passed |
| M33 Phase 0 | Orchestration / Service Contraction | 共享编排服务、消除 project_delivery 形状假设、authority alias 诚实化 | 282 passed |
| M34 Phase 0 | Facade Reduction / Authority Interior Cleanup | scheduler-authority 支持逻辑提取、authority 别名深入 projection/dispatch/diagnostics | 282 passed |

**三个里程碑在同一天（2026-04-22）内全部完成并通过冻结评审。** 这证实了用户 vibe coding 的开发速度确实很快。

### 代码变化量化

| 指标 | M31 Phase 0 基线 | M34 当前 | 变化 |
|------|-----------------|---------|------|
| 通过测试 | 278 | 280（+2 failed） | +2 净增，但出现 2 个回归 |
| 冻结评审 | 5 | 8 | +3 |
| 结构债已清偿 | TD-STRUCT-002 | +TD-STRUCT-004 | +1 |
| 结构债未清 | 6 | 4 | -2 |
| git 提交 | 12 | 18 | +6 |

---

## 二、M32-M34 的整体评估

### 2.1 做对的事

**M32 是关键里程碑**。它交付了之前所有评估文档都在讨论的核心对象：
- `IntentSession` / `IntentPacket` / `ClarificationState` / `PlanDraft` / `LaunchDecision` / `FollowupRequest` → interaction plane 契约成立
- `ExecutionClusterTemplate` / `ClusterOutputPacket` / `ClusterReviewRubric` → cluster 契约成立
- `DevCluster` / `ResearchCluster` → 首批集群模板成立
- `/ui/workbench` 最小预览 → workbench 入口存在

**M33 解决了长期存在的 TD-STRUCT-004**（project_delivery 形状假设）。这意味着编排逻辑不再是单一 preset 的特例，而是通过共享 plan builder 支撑所有 multi-role preset。这对未来添加新 Cluster 非常重要。

**M34 继续推进 TD-STRUCT-001 和 TD-STRUCT-003**。虽然没有完全清偿，但 OrchestratorService 的 facade 负担和 scheduler-authority 的语义诚实性都在持续改善。

### 2.2 需要关注的问题

**2 个测试失败**：`test_api_exposes_governance_tech_debt_report` 和 `test_cli_governance_tech_debt_report`。

> [!WARNING]
> 这两个测试失败大概率是因为 tech-debt-registry.md 的内容变更（TD-STRUCT-002/004 被清偿、描述文本变更等）导致治理报告解析结果与测试期望不匹配。这不是严重的运行时问题，但违反了项目自身的 bug-first 原则。按当前 workflow 规范，应在开启 M35 之前修复。

**TD-STRUCT-005 和 TD-STRUCT-006 持续 deferred**。这两项从 M31 起就被推迟：
- TD-STRUCT-005：capability health 仍缺乏完整的运行时遥测
- TD-STRUCT-006：平台对象 promotion 仍缺乏可复用机制

连续三个里程碑都 deferred 同样的债务，需要在 M35 开相时明确决策：是继续 defer 还是纳入 scope。

**NEXT_DEVELOPMENT_PLAN.md 已过时**。该文件仍以 M20 为基线，引用 264 passed，与当前 M34 状态严重脱节。应更新或归档。

---

## 三、M35/M36 产品化计划评估

### 3.1 M35：Role/Execution Configuration Productization

**方向评估：正确且必要。**

当前痛点准确识别：
- 不同角色（planner/coder/researcher/reviewer）使用不同 LLM 的配置目前是"aspirational"而非"productized"
- adapter/model/variant/policy 的映射散落在环境变量和隐式默认中
- cluster 成员的执行默认值没有 operator-facing 的可解释性

**交付物设计评估：**

| 交付物 | 评估 |
|--------|------|
| Role/Profile Execution Profiles | ✅ 核心需求。让不同角色用不同模型从"能做"变成"易做" |
| Multi-Profile OpenCode/Agent Config | ✅ 必要。当前全局单一 model 配置是真实限制 |
| Stable Default Mappings | ✅ 务实。先固定 5 个公共角色 + 2 个集群的默认值 |
| Productized Config Surfaces | ✅ workflow.toml + CLI/API 读取面 |
| Validation & Dogfood | ✅ 包含 DevCluster 和 ResearchCluster dogfood 路径 |

**非目标设定合理**：不做 automation plane、不做 marketplace、不做无约束动态角色、不做大规模前端重设计。

**风险**：M35 的 scope 看起来适中，但"让不同角色使用不同模型"的实现可能需要修改 compile/resume 的核心路径。如果触及 lifecycle 内核，回归风险不低。

### 3.2 M36：Natural-Language Workbench V1

**方向评估：正确，且是之前所有对话中讨论的"面向小白的入口"的第一步。**

从最小 workbench preview 升级为可用的 NL workbench v1，对应的正是用户的三层级产品中第二、第三层级用户的需求入口。

**交付物设计评估：**

| 交付物 | 评估 |
|--------|------|
| Conversational Workbench Flow | ✅ 从 preview 到可用的自然升级 |
| Run/Cluster Visibility | ✅ 让用户在 workbench 中看到集群执行状态 |
| Workbench-Level Config Awareness | ✅ 依赖 M35 的配置产品化——顺序依赖正确 |
| Operator/Workbench Separation | ✅ 保持 operator surface 和 workbench 的分离——架构诚实 |
| Validation & Dogfood | ✅ 包含 workbench 交互测试和 smoke evidence |

**非目标设定合理**：不做完整 automation plane、不做无约束多 agent 对话、不替代 CLI/API/operator 路径。

**关键约束正确**：
- M35 必须先于 M36（配置稳定后 UI 才有东西可展示）
- 不能反转顺序

### 3.3 M35/M36 对用户游戏开发目标的影响

| 能力 | M35 后 | M36 后 |
|------|--------|--------|
| 不同角色用不同模型 | ✅ 首次成为产品级能力 | ✅ |
| DevCluster 有可解释的执行默认值 | ✅ | ✅ |
| 通过自然语言启动 cluster-aware 任务 | CLI/API 可用 | **workbench 可用** |
| 视觉验证流水线 | ❌ 不在 scope 内 | ❌ 不在 scope 内 |
| DesignCluster | ❌ 不在 scope 内 | ❌ 不在 scope 内 |

> [!IMPORTANT]
> M35/M36 解决的是**平台产品化**问题（配置可解释、workbench 可用），不是**游戏开发质量**问题（设计层、视觉验证）。用户之前识别的两个核心缺失（DesignCluster + 多模态视觉验证）在 M35/M36 中均未被纳入。这是正确的 scope 控制，但意味着 M36 之后仍然不能直接用于高质量游戏开发——还需要一个专门的 DesignCluster + 视觉验证里程碑。

---

## 四、当前技术债务状态

| ID | 状态 | 评估 |
|----|------|------|
| TD-STRUCT-001 | partially_repaid | M32 提取了 interaction service，M33 提取了 orchestration service，M34 提取了 scheduler-authority support。facade 负担持续下降但未消除 |
| TD-STRUCT-003 | partially_repaid | 公共语义已诚实，operator UI 已更新，但内部存储表和事件名仍保留旧命名 |
| TD-STRUCT-005 | deferred | 连续 3 个里程碑 deferred。应在 M35 决策：纳入还是接受长期 defer |
| TD-STRUCT-006 | partially_repaid | promotion 在实践中存在（review/governance），但缺乏可复用机制 |

---

## 五、2 个测试失败的诊断

`test_api_exposes_governance_tech_debt_report` 和 `test_cli_governance_tech_debt_report` 的失败最可能的原因：

1. tech-debt-registry.md 的内容在 M32-M34 期间发生了变更（TD-STRUCT-002/004 被清偿、描述文本更新）
2. 治理报告解析器提取的结构与测试中的硬编码期望不匹配

**建议**：在 M35 开相之前修复。这是 bug-first 原则的直接要求。修复方式大概率是更新测试期望值以匹配当前 registry 内容。

---

## 六、综合判断

### 6.1 M32-M34 的执行质量

| 维度 | 评分 | 说明 |
|------|------|------|
| 交付完整性 | ⭐⭐⭐⭐⭐ | 三个里程碑全部有 phase doc、task cards、freeze review、dogfood evidence |
| 结构债管理 | ⭐⭐⭐⭐ | 清偿了 2 项，持续偿还 2 项，defer 2 项，账目清晰 |
| 测试纪律 | ⭐⭐⭐⭐ | 280 passed + 88.94% 覆盖率，但出现 2 个回归 |
| scope 控制 | ⭐⭐⭐⭐⭐ | automation plane 持续 deferred，没有 scope creep |
| 开发速度 | ⭐⭐⭐⭐⭐ | 三个里程碑在一天内完成，vibe coding 效率极高 |

### 6.2 M35/M36 计划质量

| 维度 | 评分 | 说明 |
|------|------|------|
| 方向正确性 | ⭐⭐⭐⭐⭐ | 配置产品化 → workbench 产品化的顺序完全正确 |
| scope 定义 | ⭐⭐⭐⭐⭐ | 交付物明确、非目标明确、验收标准明确 |
| 与用户目标的对齐 | ⭐⭐⭐⭐ | 解决平台产品化问题，但不直接解决游戏开发质量问题 |
| 依赖顺序 | ⭐⭐⭐⭐⭐ | M35 先于 M36，不可反转——这是正确的 |
| 文档治理 | ⭐⭐⭐ | M35/M36 计划标记为 reference-only，正确；但 NEXT_DEVELOPMENT_PLAN.md 已过时 |

---

## 七、行动建议

### 立即执行

1. **修复 2 个失败的测试**。Bug-first 原则要求在 M35 开相前完成
2. **更新或归档 NEXT_DEVELOPMENT_PLAN.md**。该文件仍以 M20 为基线，264 passed，与 M34 现状严重脱节

### M35 开相时

3. **对 TD-STRUCT-005/006 做明确决策**：纳入 M35 scope 还是接受长期 defer 并记录理由
4. **评估 M35 对 lifecycle 核心路径的影响范围**：多 profile 模型配置可能需要修改 compile/resume 内核

### M35/M36 之后

5. **规划 DesignCluster + 视觉验证里程碑**。这是用户游戏开发目标的真正瓶颈，M35/M36 不覆盖
6. **考虑将"翻译层"（把专业判断转化为小白选择题）纳入 workbench v1 的设计**

---

## 八、一句话总结

> M32-M34 在一天内完成了 interaction/profile/cluster 基础、编排收口和 authority 诚实化——执行质量和速度都很强。M35/M36 的产品化方向完全正确，但要注意两件事：修复当前的 2 个测试回归（bug-first），以及认识到 M36 之后仍需要 DesignCluster + 视觉验证才能真正开始高质量的游戏开发。
