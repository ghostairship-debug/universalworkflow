from __future__ import annotations

from packages.contracts import (
    AgentProfileDefinition,
    AgentProfileRegistry,
    AgentRoleType,
    ClusterExecutionMode,
    ClusterMemberSpec,
    ClusterReviewRubric,
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
                ),
                ClusterMemberSpec(
                    member_id="dev_cluster_implementer",
                    public_role=AgentRoleType.coder,
                    agent_profile_id="coder_implementer",
                    role_label="implementer",
                    responsibilities=["apply bounded repo changes", "run targeted tests"],
                    parallel_group="delivery_parallel",
                ),
                ClusterMemberSpec(
                    member_id="dev_cluster_risk_mapper",
                    public_role=AgentRoleType.researcher,
                    agent_profile_id="researcher_risk_mapper",
                    role_label="risk_mapper",
                    responsibilities=["capture risks", "surface supporting evidence", "list unknowns"],
                    parallel_group="delivery_parallel",
                ),
                ClusterMemberSpec(
                    member_id="dev_cluster_quality_gate",
                    public_role=AgentRoleType.reviewer,
                    agent_profile_id="reviewer_quality_gate",
                    role_label="quality_gate",
                    responsibilities=["review combined output", "call out regressions", "gate approval"],
                ),
                ClusterMemberSpec(
                    member_id="dev_cluster_launch_guard",
                    public_role=AgentRoleType.operator,
                    agent_profile_id="operator_launch_guard",
                    role_label="launch_guard",
                    responsibilities=["keep launch human-visible", "record checkpoints", "own follow-up path"],
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
                ),
                ClusterMemberSpec(
                    member_id="research_cluster_citation_checker",
                    public_role=AgentRoleType.reviewer,
                    agent_profile_id="reviewer_citation_checker",
                    role_label="citation_checker",
                    responsibilities=["verify claims", "check citations", "adjust confidence posture"],
                ),
                ClusterMemberSpec(
                    member_id="research_cluster_launch_guard",
                    public_role=AgentRoleType.operator,
                    agent_profile_id="operator_launch_guard",
                    role_label="launch_guard",
                    responsibilities=["hold the launch gate", "keep operator follow-up explicit"],
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
    ]


def cluster_template_ids_for_preset(preset_id: str | None) -> list[str]:
    mapping = {
        "project_delivery": ["dev_cluster"],
        "guarded_project_delivery": ["dev_cluster"],
        "research_spike": ["research_cluster"],
        "research_spike_reviewable": ["research_cluster"],
    }
    return list(mapping.get(str(preset_id or ""), []))


def default_preset_id_for_cluster_template(template_id: str) -> str | None:
    mapping = {
        "dev_cluster": "project_delivery",
        "research_cluster": "research_spike_reviewable",
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
    if public_role == AgentRoleType.coder:
        return "feature_delivery"
    if public_role == AgentRoleType.reviewer:
        return "advisory_delivery"
    if public_role == AgentRoleType.operator:
        return "guarded_delivery"
    return "optional_delivery"


def preferred_adapter_for_cluster_member(public_role: AgentRoleType) -> str | None:
    if public_role == AgentRoleType.coder:
        return "opencode"
    if public_role in {AgentRoleType.planner, AgentRoleType.researcher, AgentRoleType.reviewer}:
        return "agent"
    return None


def fallback_adapter_for_cluster_member(public_role: AgentRoleType) -> str | None:
    if public_role in {AgentRoleType.planner, AgentRoleType.coder, AgentRoleType.researcher, AgentRoleType.reviewer}:
        return "shell"
    return None
