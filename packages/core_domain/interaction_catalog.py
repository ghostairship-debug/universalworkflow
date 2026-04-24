from __future__ import annotations

from packages.contracts import (
    AgentProfileDefinition,
    AgentProfileRegistry,
    AgentRoleType,
    ClusterExecutionMode,
    ClusterMemberSpec,
    ClusterReviewRubric,
    ExecutionProfileDefinition,
    ExecutionClusterTemplate,
    ProfileVisibility,
    ReviewPolicy,
    RoleEvaluationRubric,
    TerminationRule,
)


def build_default_agent_profile_registry() -> AgentProfileRegistry:
    profiles = [
        AgentProfileDefinition(
            profile_id="planner_architect",
            name="Planner Architect",
            description="Decomposes broad goals into bounded workstreams and integration checkpoints.",
            public_role=AgentRoleType.planner,
            role_label="architect",
            capability_tags=["planning", "decomposition", "integration"],
            capability_scope_tags=["plan_graph", "task_cards", "coordination"],
            visibility=ProfileVisibility.public,
            system_brief="Prefer clear decomposition, explicit assumptions, and narrow handoffs.",
            termination_rule=TerminationRule(
                max_turns=8,
                completion_signals=["work breakdown accepted", "handoff graph published"],
                escalate_on=["unbounded scope", "missing execution owner"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "goal is decomposed into bounded workstreams",
                    "handoff order is explicit",
                    "risks and dependencies are surfaced early",
                ],
                required_artifacts=["plan_graph", "task_card_pack"],
                minimum_confidence=0.75,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
        AgentProfileDefinition(
            profile_id="coder_implementer",
            name="Coder Implementer",
            description="Owns the primary implementation slice and controlled repo mutation path.",
            public_role=AgentRoleType.coder,
            role_label="implementer",
            capability_tags=["implementation", "repo_mutation", "tests"],
            capability_scope_tags=["feature_delivery", "patch_apply"],
            visibility=ProfileVisibility.public,
            system_brief="Prefer minimal diffs, preserve user changes, and validate with targeted tests.",
            termination_rule=TerminationRule(
                max_turns=12,
                max_runtime_minutes=45,
                completion_signals=["targeted tests pass", "artifact updated"],
                escalate_on=["write-scope conflict", "failing regression"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "writes stay inside declared scope",
                    "targeted tests cover the changed behavior",
                    "mutation result is reviewable",
                ],
                required_artifacts=["code_diff", "test_result"],
                minimum_confidence=0.8,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="codex"),
        ),
        AgentProfileDefinition(
            profile_id="researcher_multimodal_evidence",
            name="Multimodal Evidence Researcher",
            description="Uses MMX/Vertex-style artifact evidence to extract facts from PDFs, screenshots, and design inputs.",
            public_role=AgentRoleType.researcher,
            role_label="multimodal_evidence",
            capability_tags=["multimodal", "pdf", "image", "research", "evidence"],
            capability_scope_tags=["multimodal_extract", "research_brief", "source_trace"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Prefer source-grounded extraction, explicit uncertainty, and evidence files that planner can consume.",
            termination_rule=TerminationRule(
                max_turns=6,
                completion_signals=["multimodal evidence artifact produced", "source trace recorded"],
                escalate_on=["missing input path", "unclear source ownership"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "important facts are extracted from referenced media",
                    "source paths and confidence are visible",
                    "planner handoff stays concise",
                ],
                required_artifacts=["multimodal_extract", "research_brief", "source_trace"],
                minimum_confidence=0.72,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="mmx_multimodal"),
        ),
        AgentProfileDefinition(
            profile_id="planner_phase_designer",
            name="Planner Phase Designer",
            description="Turns research and architecture notes into phase plans and active task cards.",
            public_role=AgentRoleType.planner,
            role_label="phase_designer",
            capability_tags=["planning", "phase_breakdown", "task_cards"],
            capability_scope_tags=["phase_plan", "task_cards", "handoff"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Prefer bounded phases, narrow task cards, explicit tests, and Chinese operator-facing notes.",
            termination_rule=TerminationRule(
                max_turns=8,
                completion_signals=["phase plan published", "active task cards ready"],
                escalate_on=["architecture conflict", "unbounded active phase"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "phase boundaries are clear",
                    "active task cards declare write scope and tests",
                    "handoff to worker is executable",
                ],
                required_artifacts=["phase_plan", "task_card_pack"],
                minimum_confidence=0.78,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
        AgentProfileDefinition(
            profile_id="claude_architect_gate",
            name="Claude Architect Gate",
            description="Uses the scarce Claude Code slot once to challenge module boundaries and architecture skeletons.",
            public_role=AgentRoleType.planner,
            role_label="claude_architect_gate",
            capability_tags=["architecture", "boundary_review", "risk_register"],
            capability_scope_tags=["architecture_skeleton", "module_boundaries", "do_not_touch"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Read only. Produce architecture skeleton, interfaces, risks, do-not-touch notes, and planner handoff.",
            termination_rule=TerminationRule(
                max_turns=1,
                completion_signals=["architecture skeleton delivered"],
                escalate_on=["repo mutation requested", "second claude call requested"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "module boundaries are concrete",
                    "interfaces and do-not-touch areas are explicit",
                    "risks are useful to planner before implementation",
                ],
                required_artifacts=["architecture_skeleton", "risk_register", "handoff_to_planner"],
                minimum_confidence=0.8,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="claude_architect"),
        ),
        AgentProfileDefinition(
            profile_id="researcher_risk_mapper",
            name="Research Risk Mapper",
            description="Builds supporting evidence, risk notes, and open-question coverage alongside delivery work.",
            public_role=AgentRoleType.researcher,
            role_label="risk_mapper",
            capability_tags=["research", "risk_assessment", "evidence"],
            capability_scope_tags=["research_spike", "references"],
            visibility=ProfileVisibility.public,
            system_brief="Prefer concise evidence, explicit unknowns, and actionable risk framing.",
            termination_rule=TerminationRule(
                max_turns=10,
                completion_signals=["risk brief produced", "open questions enumerated"],
                escalate_on=["missing evidence", "contradictory findings"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "major risks are explicitly listed",
                    "supporting references or rationale are attached",
                    "unknowns are clearly separated from facts",
                ],
                required_artifacts=["risk_brief"],
                minimum_confidence=0.7,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
        AgentProfileDefinition(
            profile_id="doc_curator_chinese_closeout",
            name="Chinese Doc Curator",
            description="Closes phases by absorbing useful decisions into current Chinese docs and pruning temporary detail.",
            public_role=AgentRoleType.reviewer,
            role_label="doc_curator",
            capability_tags=["documentation", "chinese", "closeout"],
            capability_scope_tags=["current_docs", "milestone_history", "tech_debt"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Prefer concise Chinese current-state docs over historical document piles.",
            termination_rule=TerminationRule(
                max_turns=6,
                completion_signals=["current docs updated", "temporary docs pruned"],
                escalate_on=["stale English public docs", "lost current workflow rule"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "Chinese current docs reflect the shipped behavior",
                    "milestone and tech debt notes are compact",
                    "temporary phase/task detail is not kept unnecessarily",
                ],
                required_artifacts=["doc_closeout_summary"],
                minimum_confidence=0.76,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
        AgentProfileDefinition(
            profile_id="reviewer_quality_gate",
            name="Reviewer Quality Gate",
            description="Checks completeness, regression risk, and release readiness across cluster outputs.",
            public_role=AgentRoleType.reviewer,
            role_label="quality_gate",
            capability_tags=["review", "regression", "readiness"],
            capability_scope_tags=["review", "governance"],
            visibility=ProfileVisibility.public,
            system_brief="Lead with findings, verify behavioral risk, and keep acceptance criteria explicit.",
            termination_rule=TerminationRule(
                max_turns=8,
                completion_signals=["review verdict recorded", "open findings listed"],
                escalate_on=["blocking regression", "missing tests"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "findings are prioritized by severity",
                    "behavioral regressions are called out explicitly",
                    "test gaps are visible before approval",
                ],
                required_artifacts=["review_verdict"],
                minimum_confidence=0.8,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
        AgentProfileDefinition(
            profile_id="operator_launch_guard",
            name="Operator Launch Guard",
            description="Keeps the execution path human-visible and enforces launch/approval checkpoints.",
            public_role=AgentRoleType.operator,
            role_label="launch_guard",
            capability_tags=["operator_control", "launch", "approval"],
            capability_scope_tags=["goal_packet", "operator_packet", "launch"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Prefer explicit operator checkpoints and safe default launch behavior.",
            termination_rule=TerminationRule(
                max_turns=6,
                completion_signals=["launch approved", "checkpoint recorded"],
                escalate_on=["human approval required", "policy mismatch"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "launch decision is explicit",
                    "policy preview is surfaced to the operator",
                    "follow-up path stays observable",
                ],
                required_artifacts=["launch_decision", "operator_packet"],
                minimum_confidence=0.75,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="shell"),
        ),
        AgentProfileDefinition(
            profile_id="researcher_research_analyst",
            name="Research Analyst",
            description="Performs focused investigation and captures structured evidence for research-led tasks.",
            public_role=AgentRoleType.researcher,
            role_label="research_analyst",
            capability_tags=["research", "analysis", "evidence"],
            capability_scope_tags=["research_cluster", "analysis"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Prefer explicit source handling, evidence summaries, and uncertainty tracking.",
            termination_rule=TerminationRule(
                max_turns=10,
                completion_signals=["research memo produced", "key findings summarized"],
                escalate_on=["source ambiguity", "unsupported claim"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "key findings are summarized cleanly",
                    "evidence is distinguishable from inference",
                    "follow-up questions are explicit",
                ],
                required_artifacts=["research_memo"],
                minimum_confidence=0.72,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
        AgentProfileDefinition(
            profile_id="reviewer_citation_checker",
            name="Citation Checker",
            description="Verifies references, evidentiary integrity, and confidence posture for research outputs.",
            public_role=AgentRoleType.reviewer,
            role_label="citation_checker",
            capability_tags=["citations", "verification", "research_review"],
            capability_scope_tags=["research_cluster", "verification"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Prefer explicit citation gaps over silent confidence inflation.",
            termination_rule=TerminationRule(
                max_turns=8,
                completion_signals=["citation review completed", "confidence posture updated"],
                escalate_on=["missing citations", "unsupported claims"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "claims map cleanly to evidence",
                    "citation gaps are called out before approval",
                    "confidence posture matches the evidence quality",
                ],
                required_artifacts=["citation_review"],
                minimum_confidence=0.78,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
        AgentProfileDefinition(
            profile_id="researcher_search_scout",
            name="Search Scout",
            description="Finds relevant sources, narrows search branches, and records what was searched.",
            public_role=AgentRoleType.researcher,
            role_label="search_scout",
            capability_tags=["search", "source_discovery", "research"],
            capability_scope_tags=["search_cluster", "source_trace"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Prefer focused search branches, source traceability, and explicit gaps over broad unsourced claims.",
            termination_rule=TerminationRule(
                max_turns=8,
                completion_signals=["source list produced", "search gaps recorded"],
                escalate_on=["missing source path", "ambiguous search target"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "queries or source paths are explicit",
                    "top sources are ranked by usefulness",
                    "known gaps are carried forward",
                ],
                required_artifacts=["source_trace", "search_brief"],
                minimum_confidence=0.72,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
        AgentProfileDefinition(
            profile_id="researcher_source_synthesizer",
            name="Source Synthesizer",
            description="Turns search results into a compact research brief with claims, evidence, and uncertainty.",
            public_role=AgentRoleType.researcher,
            role_label="source_synthesizer",
            capability_tags=["synthesis", "research", "evidence"],
            capability_scope_tags=["search_cluster", "research_brief"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Separate facts from inference and keep downstream planner handoff concise.",
            termination_rule=TerminationRule(
                max_turns=8,
                completion_signals=["research brief produced", "evidence handoff ready"],
                escalate_on=["contradictory evidence", "missing source trace"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "claims are grounded in evidence",
                    "uncertainty is visible",
                    "planner handoff is actionable",
                ],
                required_artifacts=["research_brief"],
                minimum_confidence=0.76,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
        AgentProfileDefinition(
            profile_id="planner_product_designer",
            name="Product Designer",
            description="Shapes user goals into product direction, interaction surfaces, and acceptance criteria.",
            public_role=AgentRoleType.planner,
            role_label="product_designer",
            capability_tags=["product_design", "ux", "requirements"],
            capability_scope_tags=["design_cluster", "product_brief"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Prefer concrete user flows, tradeoffs, and crisp acceptance criteria.",
            termination_rule=TerminationRule(
                max_turns=8,
                completion_signals=["product brief ready", "flow boundaries defined"],
                escalate_on=["unclear user goal", "unbounded surface area"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "primary user flow is explicit",
                    "non-goals are visible",
                    "acceptance criteria are testable",
                ],
                required_artifacts=["product_brief", "ux_flow"],
                minimum_confidence=0.75,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
        AgentProfileDefinition(
            profile_id="planner_visual_interaction_designer",
            name="Visual Interaction Designer",
            description="Translates product direction into visual language, UI states, and interaction notes.",
            public_role=AgentRoleType.planner,
            role_label="visual_interaction_designer",
            capability_tags=["visual_design", "interaction_design", "ui"],
            capability_scope_tags=["design_cluster", "ui_spec"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Prefer distinctive but implementable UI direction, state coverage, and responsive constraints.",
            termination_rule=TerminationRule(
                max_turns=8,
                completion_signals=["ui spec ready", "state coverage documented"],
                escalate_on=["unbuildable visual direction", "missing key state"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "visual direction is concrete",
                    "important UI states are covered",
                    "implementation constraints are explicit",
                ],
                required_artifacts=["ui_spec", "state_matrix"],
                minimum_confidence=0.74,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
        AgentProfileDefinition(
            profile_id="reviewer_design_critic",
            name="Design Critic",
            description="Reviews product and UI plans for usability, clarity, feasibility, and personal workflow fit.",
            public_role=AgentRoleType.reviewer,
            role_label="design_critic",
            capability_tags=["design_review", "usability", "feasibility"],
            capability_scope_tags=["design_cluster", "review"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Lead with practical UX risks, missing states, and implementation pitfalls.",
            termination_rule=TerminationRule(
                max_turns=6,
                completion_signals=["design review completed", "blocking gaps listed"],
                escalate_on=["missing core flow", "unresolved usability risk"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "usability risks are explicit",
                    "missing states are called out",
                    "recommendations are actionable",
                ],
                required_artifacts=["design_review"],
                minimum_confidence=0.78,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
        AgentProfileDefinition(
            profile_id="researcher_multimodal_synthesizer",
            name="Multimodal Synthesizer",
            description="Combines MMX/Vertex evidence into a planner-ready brief with source confidence.",
            public_role=AgentRoleType.researcher,
            role_label="multimodal_synthesizer",
            capability_tags=["multimodal", "synthesis", "evidence"],
            capability_scope_tags=["multimodal_cluster", "research_brief"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Preserve source paths, confidence, and extracted constraints for downstream planning.",
            termination_rule=TerminationRule(
                max_turns=6,
                completion_signals=["multimodal brief ready", "source confidence recorded"],
                escalate_on=["conflicting extracted facts", "missing referenced media"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "source confidence is explicit",
                    "important constraints are extracted",
                    "planner handoff is concise",
                ],
                required_artifacts=["multimodal_brief"],
                minimum_confidence=0.74,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
        AgentProfileDefinition(
            profile_id="reviewer_test_sentinel",
            name="Test Sentinel",
            description="Focuses on test evidence, failure modes, and regression containment.",
            public_role=AgentRoleType.reviewer,
            role_label="test_sentinel",
            capability_tags=["tests", "regression", "failure_analysis"],
            capability_scope_tags=["review_cluster", "test_evidence"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Prefer concrete test gaps, failure reproduction notes, and minimal validation commands.",
            termination_rule=TerminationRule(
                max_turns=6,
                completion_signals=["test evidence reviewed", "test gaps listed"],
                escalate_on=["missing critical test", "unreproduced failure"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "test evidence is verified",
                    "regression gaps are explicit",
                    "next validation command is clear",
                ],
                required_artifacts=["test_review"],
                minimum_confidence=0.8,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
        AgentProfileDefinition(
            profile_id="reviewer_governance_sentinel",
            name="Governance Sentinel",
            description="Checks policy, tech-debt, documentation, and release readiness implications.",
            public_role=AgentRoleType.reviewer,
            role_label="governance_sentinel",
            capability_tags=["governance", "tech_debt", "release_readiness"],
            capability_scope_tags=["management_cluster", "review_cluster"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Prefer explicit governance impact, debt updates, and release-readiness risks.",
            termination_rule=TerminationRule(
                max_turns=6,
                completion_signals=["governance review completed", "debt updates listed"],
                escalate_on=["undocumented debt", "policy mismatch"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "policy impact is explicit",
                    "tech-debt changes are recorded",
                    "release readiness is not overstated",
                ],
                required_artifacts=["governance_review"],
                minimum_confidence=0.78,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
        AgentProfileDefinition(
            profile_id="planner_roadmap_manager",
            name="Roadmap Manager",
            description="Keeps milestone scope, phase order, task cards, and closeout gates coherent.",
            public_role=AgentRoleType.planner,
            role_label="roadmap_manager",
            capability_tags=["roadmap", "phase_management", "task_cards"],
            capability_scope_tags=["management_cluster", "planning"],
            visibility=ProfileVisibility.internal,
            cluster_only=True,
            system_brief="Prefer current-phase focus, explicit closeout gates, and compact Chinese summaries.",
            termination_rule=TerminationRule(
                max_turns=8,
                completion_signals=["roadmap updated", "active phase gates clear"],
                escalate_on=["scope creep", "missing closeout verification"],
            ),
            evaluation_rubric=RoleEvaluationRubric(
                criteria=[
                    "phase order is coherent",
                    "task cards map to verification",
                    "closeout gates are explicit",
                ],
                required_artifacts=["roadmap_update", "phase_gate_summary"],
                minimum_confidence=0.78,
            ),
            execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
        ),
    ]
    return AgentProfileRegistry(profiles=profiles, generated_profiles=[])


def list_default_cluster_templates() -> list[ExecutionClusterTemplate]:
    return [
        ExecutionClusterTemplate(
            template_id="dev_cluster",
            name="DevCluster",
            description="Planner-led software delivery cluster with parallel implementation and risk mapping lanes.",
            domain_tags=["software_delivery", "project_delivery", "orchestration"],
            primary_public_role=AgentRoleType.operator,
            default_review_policy=ReviewPolicy.recommended,
            execution_mode=ClusterExecutionMode.parallel,
            member_specs=[
                ClusterMemberSpec(
                    member_id="dev_cluster_architect",
                    public_role=AgentRoleType.planner,
                    agent_profile_id="planner_architect",
                    role_label="architect",
                    responsibilities=["decompose scope", "publish work breakdown", "define handoff edges"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="dev_cluster_implementer",
                    public_role=AgentRoleType.coder,
                    agent_profile_id="coder_implementer",
                    role_label="implementer",
                    responsibilities=["apply bounded repo changes", "run targeted tests"],
                    parallel_group="delivery_parallel",
                    execution_profile=ExecutionProfileDefinition(adapter_name="codex"),
                ),
                ClusterMemberSpec(
                    member_id="dev_cluster_risk_mapper",
                    public_role=AgentRoleType.researcher,
                    agent_profile_id="researcher_risk_mapper",
                    role_label="risk_mapper",
                    responsibilities=["capture risks", "surface supporting evidence", "list unknowns"],
                    parallel_group="delivery_parallel",
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="dev_cluster_quality_gate",
                    public_role=AgentRoleType.reviewer,
                    agent_profile_id="reviewer_quality_gate",
                    role_label="quality_gate",
                    responsibilities=["review combined output", "call out regressions", "gate approval"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="dev_cluster_launch_guard",
                    public_role=AgentRoleType.operator,
                    agent_profile_id="operator_launch_guard",
                    role_label="launch_guard",
                    responsibilities=["keep launch human-visible", "record checkpoints", "own follow-up path"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="shell"),
                ),
            ],
            review_rubric=ClusterReviewRubric(
                name="DevCluster Review Rubric",
                criteria=[
                    "implementation, risk mapping, and review are all represented",
                    "repo mutation stays bounded and test-backed",
                    "launch visibility remains intact",
                ],
                required_artifacts=["plan_graph", "code_diff", "review_verdict"],
                escalation_conditions=["missing review evidence", "failing targeted tests", "write-scope conflict"],
                quality_bar="delivery_ready",
            ),
        ),
        ExecutionClusterTemplate(
            template_id="research_cluster",
            name="ResearchCluster",
            description="Research-led cluster for investigation, citation checking, and guarded operator handoff.",
            domain_tags=["research", "analysis", "evidence"],
            primary_public_role=AgentRoleType.researcher,
            default_review_policy=ReviewPolicy.human_required,
            execution_mode=ClusterExecutionMode.sequential,
            member_specs=[
                ClusterMemberSpec(
                    member_id="research_cluster_analyst",
                    public_role=AgentRoleType.researcher,
                    agent_profile_id="researcher_research_analyst",
                    role_label="research_analyst",
                    responsibilities=["investigate the question", "produce findings", "record open questions"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="research_cluster_citation_checker",
                    public_role=AgentRoleType.reviewer,
                    agent_profile_id="reviewer_citation_checker",
                    role_label="citation_checker",
                    responsibilities=["verify claims", "check citations", "adjust confidence posture"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="research_cluster_launch_guard",
                    public_role=AgentRoleType.operator,
                    agent_profile_id="operator_launch_guard",
                    role_label="launch_guard",
                    responsibilities=["hold the launch gate", "keep operator follow-up explicit"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="shell"),
                ),
            ],
            review_rubric=ClusterReviewRubric(
                name="ResearchCluster Review Rubric",
                criteria=[
                    "research findings are explicit",
                    "unsupported claims are blocked before launch",
                    "operator follow-up remains visible",
                ],
                required_artifacts=["research_memo", "citation_review"],
                escalation_conditions=["missing citations", "contradictory evidence", "confidence mismatch"],
                quality_bar="evidence_ready",
            ),
        ),
        ExecutionClusterTemplate(
            template_id="architecture_delivery_cluster",
            name="ArchitectureDeliveryCluster",
            description=(
                "Strong-model dogfood delivery chain: evidence, planner design, one-shot Claude architecture gate, "
                "phase/task breakdown, bounded implementation, review, and Chinese documentation closeout."
            ),
            domain_tags=["architecture", "dogfood", "multimodal", "project_delivery", "workflow_development"],
            primary_public_role=AgentRoleType.operator,
            default_review_policy=ReviewPolicy.human_required,
            execution_mode=ClusterExecutionMode.sequential,
            member_specs=[
                ClusterMemberSpec(
                    member_id="architecture_delivery_multimodal_evidence",
                    public_role=AgentRoleType.researcher,
                    agent_profile_id="researcher_multimodal_evidence",
                    role_label="multimodal_evidence",
                    responsibilities=["extract evidence from referenced PDF/image paths", "publish source trace"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="mmx_multimodal"),
                ),
                ClusterMemberSpec(
                    member_id="architecture_delivery_design_planner",
                    public_role=AgentRoleType.planner,
                    agent_profile_id="planner_architect",
                    role_label="planner_design",
                    responsibilities=["turn evidence into a design draft", "list constraints and open risks"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="architecture_delivery_claude_gate",
                    public_role=AgentRoleType.planner,
                    agent_profile_id="claude_architect_gate",
                    role_label="claude_architect_gate",
                    responsibilities=["produce architecture skeleton once", "challenge boundaries", "record do-not-touch zones"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="claude_architect"),
                ),
                ClusterMemberSpec(
                    member_id="architecture_delivery_phase_planner",
                    public_role=AgentRoleType.planner,
                    agent_profile_id="planner_phase_designer",
                    role_label="phase_designer",
                    responsibilities=["absorb Claude skeleton", "split phases", "write active task cards"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="architecture_delivery_worker",
                    public_role=AgentRoleType.coder,
                    agent_profile_id="coder_implementer",
                    role_label="implementer",
                    responsibilities=["execute only active task card write scope", "run targeted tests"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="codex"),
                ),
                ClusterMemberSpec(
                    member_id="architecture_delivery_quality_gate",
                    public_role=AgentRoleType.reviewer,
                    agent_profile_id="reviewer_quality_gate",
                    role_label="quality_gate",
                    responsibilities=["review behavior and regressions", "block unsafe merge-ready claims"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="architecture_delivery_doc_curator",
                    public_role=AgentRoleType.reviewer,
                    agent_profile_id="doc_curator_chinese_closeout",
                    role_label="doc_curator",
                    responsibilities=["update active Chinese docs", "summarize history and tech debt"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="architecture_delivery_launch_guard",
                    public_role=AgentRoleType.operator,
                    agent_profile_id="operator_launch_guard",
                    role_label="launch_guard",
                    responsibilities=["keep confirmation checkpoints visible", "record human takeover points"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="shell"),
                ),
            ],
            review_rubric=ClusterReviewRubric(
                name="ArchitectureDeliveryCluster Review Rubric",
                criteria=[
                    "multimodal evidence and source trace exist when input paths are provided",
                    "Claude architect gate is at most once and artifact-only",
                    "planner converts architecture into bounded phase/task work",
                    "worker declares write scope and targeted tests",
                    "review and Chinese doc closeout are represented",
                ],
                required_artifacts=[
                    "multimodal_extract",
                    "architecture_skeleton",
                    "task_card_pack",
                    "test_result",
                    "review_verdict",
                    "doc_closeout_summary",
                ],
                escalation_conditions=[
                    "second Claude call requested",
                    "repo mutation outside worker scope",
                    "missing evidence for referenced media",
                    "failing targeted tests",
                ],
                quality_bar="dogfood_delivery_ready",
            ),
        ),
        ExecutionClusterTemplate(
            template_id="search_cluster",
            name="SearchCluster",
            description="Source discovery and synthesis cluster for search-led tasks.",
            domain_tags=["search", "research", "source_discovery", "evidence"],
            primary_public_role=AgentRoleType.researcher,
            default_review_policy=ReviewPolicy.human_required,
            execution_mode=ClusterExecutionMode.sequential,
            member_specs=[
                ClusterMemberSpec(
                    member_id="search_cluster_scout",
                    public_role=AgentRoleType.researcher,
                    agent_profile_id="researcher_search_scout",
                    role_label="search_scout",
                    responsibilities=["discover useful sources", "record search branches", "surface source gaps"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="search_cluster_synthesizer",
                    public_role=AgentRoleType.researcher,
                    agent_profile_id="researcher_source_synthesizer",
                    role_label="source_synthesizer",
                    responsibilities=["synthesize source findings", "separate facts from inference"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="search_cluster_citation_checker",
                    public_role=AgentRoleType.reviewer,
                    agent_profile_id="reviewer_citation_checker",
                    role_label="citation_checker",
                    responsibilities=["verify claims", "flag weak evidence", "adjust confidence"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="search_cluster_launch_guard",
                    public_role=AgentRoleType.operator,
                    agent_profile_id="operator_launch_guard",
                    role_label="launch_guard",
                    responsibilities=["keep follow-up visible", "record human takeover points"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="shell"),
                ),
            ],
            review_rubric=ClusterReviewRubric(
                name="SearchCluster Review Rubric",
                criteria=[
                    "source trace is explicit",
                    "facts and inference are separated",
                    "citation confidence is visible",
                ],
                required_artifacts=["source_trace", "research_brief", "citation_review"],
                escalation_conditions=["unsupported claim", "missing source trace", "contradictory evidence"],
                quality_bar="source_ready",
            ),
        ),
        ExecutionClusterTemplate(
            template_id="design_cluster",
            name="DesignCluster",
            description="Product and interaction design cluster for UI, UX, and artifact direction.",
            domain_tags=["design", "ux", "ui", "product", "visual"],
            primary_public_role=AgentRoleType.planner,
            default_review_policy=ReviewPolicy.recommended,
            execution_mode=ClusterExecutionMode.sequential,
            member_specs=[
                ClusterMemberSpec(
                    member_id="design_cluster_product_designer",
                    public_role=AgentRoleType.planner,
                    agent_profile_id="planner_product_designer",
                    role_label="product_designer",
                    responsibilities=["define product direction", "map primary user flow", "write acceptance criteria"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="design_cluster_visual_interaction_designer",
                    public_role=AgentRoleType.planner,
                    agent_profile_id="planner_visual_interaction_designer",
                    role_label="visual_interaction_designer",
                    responsibilities=["define UI states", "set visual direction", "capture responsive constraints"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="design_cluster_design_critic",
                    public_role=AgentRoleType.reviewer,
                    agent_profile_id="reviewer_design_critic",
                    role_label="design_critic",
                    responsibilities=["review usability", "call out missing states", "check feasibility"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="design_cluster_launch_guard",
                    public_role=AgentRoleType.operator,
                    agent_profile_id="operator_launch_guard",
                    role_label="launch_guard",
                    responsibilities=["record design decision", "keep implementation handoff explicit"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="shell"),
                ),
            ],
            review_rubric=ClusterReviewRubric(
                name="DesignCluster Review Rubric",
                criteria=[
                    "primary flow and non-goals are explicit",
                    "UI state coverage is sufficient",
                    "design risks are reviewed before implementation",
                ],
                required_artifacts=["product_brief", "ui_spec", "design_review"],
                escalation_conditions=["missing core flow", "unbuildable design direction", "unresolved usability risk"],
                quality_bar="design_ready",
            ),
        ),
        ExecutionClusterTemplate(
            template_id="multimodal_cluster",
            name="MultimodalCluster",
            description="PDF/image/screenshot evidence cluster with MMX primary extraction and synthesis fallback.",
            domain_tags=["multimodal", "pdf", "image", "screenshot", "mmx", "vertex"],
            primary_public_role=AgentRoleType.researcher,
            default_review_policy=ReviewPolicy.human_required,
            execution_mode=ClusterExecutionMode.sequential,
            member_specs=[
                ClusterMemberSpec(
                    member_id="multimodal_cluster_mmx_evidence",
                    public_role=AgentRoleType.researcher,
                    agent_profile_id="researcher_multimodal_evidence",
                    role_label="multimodal_evidence",
                    responsibilities=["extract PDF/image evidence", "publish source trace"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="mmx_multimodal"),
                ),
                ClusterMemberSpec(
                    member_id="multimodal_cluster_synthesizer",
                    public_role=AgentRoleType.researcher,
                    agent_profile_id="researcher_multimodal_synthesizer",
                    role_label="multimodal_synthesizer",
                    responsibilities=["synthesize extracted facts", "record confidence", "prepare planner handoff"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="multimodal_cluster_citation_checker",
                    public_role=AgentRoleType.reviewer,
                    agent_profile_id="reviewer_citation_checker",
                    role_label="citation_checker",
                    responsibilities=["verify extracted claims", "flag missing or ambiguous media evidence"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="multimodal_cluster_launch_guard",
                    public_role=AgentRoleType.operator,
                    agent_profile_id="operator_launch_guard",
                    role_label="launch_guard",
                    responsibilities=["keep referenced media and follow-up visible"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="shell"),
                ),
            ],
            review_rubric=ClusterReviewRubric(
                name="MultimodalCluster Review Rubric",
                criteria=[
                    "referenced media paths are visible",
                    "extracted facts include confidence",
                    "ambiguous evidence is not overclaimed",
                ],
                required_artifacts=["multimodal_extract", "multimodal_brief", "citation_review"],
                escalation_conditions=["missing media path", "failed extraction without fallback", "unsupported extracted claim"],
                quality_bar="multimodal_evidence_ready",
            ),
        ),
        ExecutionClusterTemplate(
            template_id="review_cluster",
            name="ReviewCluster",
            description="Quality, test, governance, and documentation review cluster for high-risk changes.",
            domain_tags=["review", "quality", "tests", "governance", "release_readiness"],
            primary_public_role=AgentRoleType.reviewer,
            default_review_policy=ReviewPolicy.human_required,
            execution_mode=ClusterExecutionMode.parallel,
            member_specs=[
                ClusterMemberSpec(
                    member_id="review_cluster_quality_gate",
                    public_role=AgentRoleType.reviewer,
                    agent_profile_id="reviewer_quality_gate",
                    role_label="quality_gate",
                    responsibilities=["review behavior", "find regressions", "gate readiness"],
                    parallel_group="review_parallel",
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="review_cluster_test_sentinel",
                    public_role=AgentRoleType.reviewer,
                    agent_profile_id="reviewer_test_sentinel",
                    role_label="test_sentinel",
                    responsibilities=["inspect test evidence", "surface missing tests", "suggest targeted validation"],
                    parallel_group="review_parallel",
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="review_cluster_governance_sentinel",
                    public_role=AgentRoleType.reviewer,
                    agent_profile_id="reviewer_governance_sentinel",
                    role_label="governance_sentinel",
                    responsibilities=["check policy impact", "record debt changes", "verify release-readiness claims"],
                    parallel_group="review_parallel",
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="review_cluster_doc_curator",
                    public_role=AgentRoleType.reviewer,
                    agent_profile_id="doc_curator_chinese_closeout",
                    role_label="doc_curator",
                    responsibilities=["close Chinese docs", "summarize review outcome"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="review_cluster_launch_guard",
                    public_role=AgentRoleType.operator,
                    agent_profile_id="operator_launch_guard",
                    role_label="launch_guard",
                    responsibilities=["hold final human-visible gate", "record follow-up actions"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="shell"),
                ),
            ],
            review_rubric=ClusterReviewRubric(
                name="ReviewCluster Review Rubric",
                criteria=[
                    "quality findings are prioritized",
                    "test gaps are explicit",
                    "governance and documentation impacts are recorded",
                ],
                required_artifacts=["review_verdict", "test_review", "governance_review", "doc_closeout_summary"],
                escalation_conditions=["blocking regression", "missing critical test", "unrecorded tech debt"],
                quality_bar="review_ready",
            ),
        ),
        ExecutionClusterTemplate(
            template_id="management_cluster",
            name="ManagementCluster",
            description="Roadmap, phase/task, governance, and closeout management cluster for long-running personal work.",
            domain_tags=["management", "roadmap", "phase", "task_cards", "closeout"],
            primary_public_role=AgentRoleType.operator,
            default_review_policy=ReviewPolicy.human_required,
            execution_mode=ClusterExecutionMode.sequential,
            member_specs=[
                ClusterMemberSpec(
                    member_id="management_cluster_roadmap_manager",
                    public_role=AgentRoleType.planner,
                    agent_profile_id="planner_roadmap_manager",
                    role_label="roadmap_manager",
                    responsibilities=["set phase order", "keep active task cards scoped", "define closeout gates"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="management_cluster_phase_designer",
                    public_role=AgentRoleType.planner,
                    agent_profile_id="planner_phase_designer",
                    role_label="phase_designer",
                    responsibilities=["write current phase plan", "produce executable task cards"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="management_cluster_governance_sentinel",
                    public_role=AgentRoleType.reviewer,
                    agent_profile_id="reviewer_governance_sentinel",
                    role_label="governance_sentinel",
                    responsibilities=["check policy and debt updates", "verify closeout scope"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="management_cluster_doc_curator",
                    public_role=AgentRoleType.reviewer,
                    agent_profile_id="doc_curator_chinese_closeout",
                    role_label="doc_curator",
                    responsibilities=["absorb conclusions into Chinese docs", "avoid historical doc piles"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="agent"),
                ),
                ClusterMemberSpec(
                    member_id="management_cluster_launch_guard",
                    public_role=AgentRoleType.operator,
                    agent_profile_id="operator_launch_guard",
                    role_label="launch_guard",
                    responsibilities=["record owner decision", "surface next phase or stop condition"],
                    execution_profile=ExecutionProfileDefinition(adapter_name="shell"),
                ),
            ],
            review_rubric=ClusterReviewRubric(
                name="ManagementCluster Review Rubric",
                criteria=[
                    "phase/task scope is coherent",
                    "closeout gates are explicit",
                    "current docs and debt registry stay aligned",
                ],
                required_artifacts=["roadmap_update", "task_card_pack", "governance_review", "doc_closeout_summary"],
                escalation_conditions=["scope creep", "missing closeout validation", "doc/debt mismatch"],
                quality_bar="management_ready",
            ),
        ),
    ]


def cluster_template_ids_for_preset(preset_id: str | None) -> list[str]:
    mapping = {
        "project_delivery": ["dev_cluster"],
        "guarded_project_delivery": ["dev_cluster"],
        "architecture_delivery": ["architecture_delivery_cluster"],
        "dogfood_delivery": ["architecture_delivery_cluster"],
        "research_spike": ["research_cluster"],
        "research_spike_reviewable": ["research_cluster"],
    }
    return list(mapping.get(str(preset_id or ""), []))


def default_preset_id_for_cluster_template(template_id: str) -> str | None:
    mapping = {
        "dev_cluster": "project_delivery",
        "research_cluster": "research_spike_reviewable",
        "architecture_delivery_cluster": "project_delivery",
        "search_cluster": "research_spike_reviewable",
        "design_cluster": "advisory_delivery",
        "multimodal_cluster": "research_spike_reviewable",
        "review_cluster": "advisory_delivery",
        "management_cluster": "project_delivery",
    }
    return mapping.get(template_id)


def sequence_no_for_cluster_member(template_id: str, role_label: str, public_role: AgentRoleType) -> int:
    if template_id == "dev_cluster":
        mapping = {
            "architect": 1,
            "implementer": 2,
            "risk_mapper": 2,
            "quality_gate": 3,
            "launch_guard": 4,
        }
        return mapping.get(role_label, 4)
    if template_id == "research_cluster":
        mapping = {
            "research_analyst": 1,
            "citation_checker": 2,
            "launch_guard": 3,
        }
        return mapping.get(role_label, 3)
    if template_id == "architecture_delivery_cluster":
        mapping = {
            "multimodal_evidence": 1,
            "planner_design": 2,
            "claude_architect_gate": 3,
            "phase_designer": 4,
            "implementer": 5,
            "quality_gate": 6,
            "doc_curator": 7,
            "launch_guard": 8,
        }
        return mapping.get(role_label, 8)
    if template_id == "search_cluster":
        mapping = {
            "search_scout": 1,
            "source_synthesizer": 2,
            "citation_checker": 3,
            "launch_guard": 4,
        }
        return mapping.get(role_label, 4)
    if template_id == "design_cluster":
        mapping = {
            "product_designer": 1,
            "visual_interaction_designer": 2,
            "design_critic": 3,
            "launch_guard": 4,
        }
        return mapping.get(role_label, 4)
    if template_id == "multimodal_cluster":
        mapping = {
            "multimodal_evidence": 1,
            "multimodal_synthesizer": 2,
            "citation_checker": 3,
            "launch_guard": 4,
        }
        return mapping.get(role_label, 4)
    if template_id == "review_cluster":
        mapping = {
            "quality_gate": 1,
            "test_sentinel": 1,
            "governance_sentinel": 1,
            "doc_curator": 2,
            "launch_guard": 3,
        }
        return mapping.get(role_label, 3)
    if template_id == "management_cluster":
        mapping = {
            "roadmap_manager": 1,
            "phase_designer": 2,
            "governance_sentinel": 3,
            "doc_curator": 4,
            "launch_guard": 5,
        }
        return mapping.get(role_label, 5)
    if public_role == AgentRoleType.planner:
        return 1
    if public_role in {AgentRoleType.coder, AgentRoleType.researcher}:
        return 2
    if public_role == AgentRoleType.reviewer:
        return 3
    return 4


def member_preset_id(template_id: str, role_label: str, public_role: AgentRoleType) -> str:
    if template_id == "dev_cluster":
        mapping = {
            "architect": "optional_delivery",
            "implementer": "feature_delivery",
            "risk_mapper": "optional_delivery",
            "quality_gate": "advisory_delivery",
            "launch_guard": "guarded_delivery",
        }
        return mapping.get(role_label, "optional_delivery")
    if template_id == "research_cluster":
        mapping = {
            "research_analyst": "research_spike_reviewable",
            "citation_checker": "advisory_delivery",
            "launch_guard": "guarded_delivery",
        }
        return mapping.get(role_label, "research_spike_reviewable")
    if template_id == "architecture_delivery_cluster":
        mapping = {
            "multimodal_evidence": "research_spike_reviewable",
            "planner_design": "advisory_delivery",
            "claude_architect_gate": "advisory_delivery",
            "phase_designer": "optional_delivery",
            "implementer": "feature_delivery",
            "quality_gate": "advisory_delivery",
            "doc_curator": "advisory_delivery",
            "launch_guard": "guarded_delivery",
        }
        return mapping.get(role_label, "optional_delivery")
    if template_id == "search_cluster":
        mapping = {
            "search_scout": "research_spike_reviewable",
            "source_synthesizer": "research_spike_reviewable",
            "citation_checker": "advisory_delivery",
            "launch_guard": "guarded_delivery",
        }
        return mapping.get(role_label, "research_spike_reviewable")
    if template_id == "design_cluster":
        mapping = {
            "product_designer": "advisory_delivery",
            "visual_interaction_designer": "advisory_delivery",
            "design_critic": "advisory_delivery",
            "launch_guard": "guarded_delivery",
        }
        return mapping.get(role_label, "advisory_delivery")
    if template_id == "multimodal_cluster":
        mapping = {
            "multimodal_evidence": "research_spike_reviewable",
            "multimodal_synthesizer": "research_spike_reviewable",
            "citation_checker": "advisory_delivery",
            "launch_guard": "guarded_delivery",
        }
        return mapping.get(role_label, "research_spike_reviewable")
    if template_id == "review_cluster":
        mapping = {
            "quality_gate": "advisory_delivery",
            "test_sentinel": "advisory_delivery",
            "governance_sentinel": "advisory_delivery",
            "doc_curator": "advisory_delivery",
            "launch_guard": "guarded_delivery",
        }
        return mapping.get(role_label, "advisory_delivery")
    if template_id == "management_cluster":
        mapping = {
            "roadmap_manager": "advisory_delivery",
            "phase_designer": "optional_delivery",
            "governance_sentinel": "advisory_delivery",
            "doc_curator": "advisory_delivery",
            "launch_guard": "guarded_delivery",
        }
        return mapping.get(role_label, "optional_delivery")
    if public_role == AgentRoleType.coder:
        return "feature_delivery"
    if public_role == AgentRoleType.reviewer:
        return "advisory_delivery"
    if public_role == AgentRoleType.operator:
        return "guarded_delivery"
    return "optional_delivery"


def preferred_adapter_for_cluster_member(public_role: AgentRoleType) -> str | None:
    if public_role == AgentRoleType.coder:
        return "codex"
    if public_role in {AgentRoleType.planner, AgentRoleType.researcher, AgentRoleType.reviewer}:
        return "agent"
    return None


def fallback_adapter_for_cluster_member(public_role: AgentRoleType) -> str | None:
    if public_role in {AgentRoleType.planner, AgentRoleType.coder, AgentRoleType.researcher, AgentRoleType.reviewer}:
        return "shell"
    return None
