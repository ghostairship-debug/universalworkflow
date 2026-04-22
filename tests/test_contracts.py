from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from packages.contracts import (
    AgentRoleType,
    AgentProfileDefinition,
    AgentProfileRegistry,
    BudgetLedger,
    CapabilityDescriptor,
    CapabilityExecutionReceipt,
    CapabilityHealth,
    CapabilityInvocationEnvelope,
    CapabilityRoute,
    CapabilitySourceType,
    ControlPlaneIdentity,
    BarrierSpec,
    ClarificationState,
    DomainPackResolution,
    DomainPackDefinition,
    ClusterExecutionMode,
    ClusterExecutionPlan,
    ClusterHandoffPacket,
    ClusterMemberSpec,
    ClusterOutputPacket,
    ClusterReviewRubric,
    ExecutionClusterTemplate,
    EdgeSpec,
    Evidence,
    ExecutionLaneType,
    GeneratedAgentProfile,
    GeneratedProfileSource,
    HandoffLite,
    MemoryCandidate,
    MemoryItem,
    MemoryNamespace,
    MemoryRetrievalPreview,
    MutationContract,
    MutationMode,
    IntentPacket,
    IntentSession,
    IntentSessionStatus,
    NON_TERMINAL_RUNTIME_GRAPH_STEPS,
    Phase,
    PresetSuggestion,
    PresetDefinition,
    PlanDraft,
    PlanDraftStatus,
    ProfileVisibility,
    ResultEnvelope,
    ResultProvenance,
    ResultRawRef,
    ResultVerification,
    ReviewDecision,
    ReviewVerdict,
    ReviewPolicy,
    RoleEvaluationRubric,
    Run,
    RetryPolicy,
    RunSnapshot,
    RunSnapshotStage,
    RuntimeAttempt,
    RuntimeAttemptStatus,
    RuntimeAttemptTrigger,
    RUN_STATUS_TRANSITIONS,
    RunStatus,
    SchedulerLeaseDecision,
    SchedulerLeaseProposal,
    SchedulerPeerHeartbeat,
    SimulationPolicyDefinition,
    SimulationRecord,
    SimulationRecordSource,
    SimulationReport,
    SimulationTriggerPolicy,
    RepoMutationResult,
    RuntimeClaim,
    RuntimeClaimStatus,
    RuntimeGraphStep,
    OrchestrationGraphNode,
    OrchestrationPlanGraph,
    TERMINAL_RUNTIME_GRAPH_STEPS,
    RuntimeStateRef,
    RuntimeTask,
    TaskCard,
    TaskKind,
    TaskPacket,
    LaunchDecision,
    TerminationRule,
    WorkerLease,
    WorkerLeaseStatus,
    allowed_run_status_transitions,
    can_transition_run_status,
)
from packages.core_domain import PresetNotFoundError, PresetRequiredError, PresetResolver, load_seed_presets
from packages.core_domain.domain_packs import DomainPackRegistry, load_seed_domain_packs
from packages.core_domain.memory import load_seed_memory_namespaces
from packages.core_domain.simulation import load_seed_simulation_policies


def test_wave1_contracts_round_trip() -> None:
    run = Run(goal="Build the first bootstrap artifact.", preset_id="feature_delivery")
    phase = Phase(run_id=run.run_id, name="bootstrap", order_index=0)
    task_card = TaskCard(
        run_id=run.run_id,
        title="Create a bootstrap artifact",
        description="Generate the first task instructions.",
        acceptance_criteria=["artifact exists"],
    )
    runtime_task = RuntimeTask(
        run_id=run.run_id,
        phase_id=phase.phase_id,
        task_card_id=task_card.task_card_id,
        task_kind=TaskKind.shell_exec,
        summary="Generate a markdown artifact",
    )
    packet = TaskPacket(
        runtime_task_id=runtime_task.runtime_task_id,
        run_id=run.run_id,
        task_kind=TaskKind.shell_exec,
        command=["python", "-c", "print('ok')"],
        working_directory=".",
    )
    evidence = Evidence(
        run_id=run.run_id,
        runtime_task_id=runtime_task.runtime_task_id,
        summary="Command completed successfully.",
        return_code=0,
        raw_execution={"stdout": "ok", "stderr": ""},
        result_envelope=ResultEnvelope(
            summary="Command completed successfully.",
            raw_ref=ResultRawRef(runtime_task_id=runtime_task.runtime_task_id),
            artifacts=[],
            verification=ResultVerification(return_code=0, checks=[], known_gaps=[]),
            provenance=ResultProvenance(
                adapter_name="shell",
                started_at=run.created_at,
                finished_at=run.created_at,
                duration_ms=0,
            ),
            confidence=1.0,
        ),
    )
    verdict = ReviewVerdict(
        run_id=run.run_id,
        evidence_id=evidence.evidence_id,
        decision=ReviewDecision.pass_,
        rationale="Return code is zero and stderr is empty.",
    )
    handoff = HandoffLite(
        run_id=run.run_id,
        from_phase_id=phase.phase_id,
        to_phase_id=phase.phase_id,
        summary="No handoff used in M0 runtime path.",
    )
    state_ref = RuntimeStateRef(
        run_id=run.run_id,
        runtime_task_id=runtime_task.runtime_task_id,
        graph_step="compiled",
        state_payload={"entrypoint": "resume"},
    )
    suggestion = PresetSuggestion(preset_id="feature_delivery", score=10, reason="keyword match")
    capability_route = CapabilityRoute(capability="shell_exec", adapter_name="shell", adapter_class="ShellAdapter")
    domain_pack = DomainPackDefinition(
        domain_pack_id="software_delivery_pack",
        name="Software Delivery Pack",
        description="test pack",
        preset_ids=["feature_delivery"],
        task_kinds=[TaskKind.shell_exec],
        artifact_label="software_delivery",
    )
    claim = RuntimeClaim(
        run_id=run.run_id,
        runtime_task_id=runtime_task.runtime_task_id,
        lease_expires_at=run.created_at,
    )
    snapshot = RunSnapshot(
        run_id=run.run_id,
        stage=RunSnapshotStage.compiled,
        run_status=RunStatus.prepared,
        runtime_task_id=runtime_task.runtime_task_id,
        summary="Compile snapshot captured.",
        snapshot_payload={"phase_ids": [phase.phase_id], "task_card_ids": [task_card.task_card_id]},
    )
    ledger = BudgetLedger(
        run_id=run.run_id,
        preset_id=run.preset_id,
        max_retries=2,
        timeout_seconds=300,
        compile_count=1,
    )
    worker_lease = WorkerLease(
        run_id=run.run_id,
        runtime_task_id=runtime_task.runtime_task_id,
        adapter_name="shell",
        lease_expires_at=run.created_at,
    )
    runtime_attempt = RuntimeAttempt(
        run_id=run.run_id,
        runtime_task_id=runtime_task.runtime_task_id,
        sequence_no=1,
        trigger=RuntimeAttemptTrigger.compile,
    )
    memory_namespace = MemoryNamespace(
        namespace_id="repo",
        name="Repository Memory",
        kind="working_context",
        scope="run_and_repo",
        retention_policy="retain_recent_successes",
        retrieval_policy="rule_based_context_pack",
    )
    memory_candidate = MemoryCandidate(
        run_id=run.run_id,
        namespace_id="repo",
        title="candidate",
        summary="summary",
        source_refs=[f"run:{run.run_id}"],
    )
    memory_item = MemoryItem(
        run_id=run.run_id,
        namespace_id="repo",
        source_candidate_id=f"memcand_{run.run_id}_repo",
        title="item",
        summary="summary",
        source_refs=[f"run:{run.run_id}"],
    )
    memory_retrieval_preview = MemoryRetrievalPreview(
        run_id=run.run_id,
        preset_id=run.preset_id,
        namespace_ids=["repo"],
        selected_memory_item_ids=[memory_item.memory_item_id],
        source_run_ids=[run.run_id],
        item_count=1,
        brief_lines=["[repo] item: summary"],
        items=[memory_item],
    )
    simulation_policy = SimulationPolicyDefinition(
        policy_id="delivery_consistency_simulation",
        name="Delivery Consistency Simulation",
        description="test simulation policy",
        preset_ids=["feature_delivery"],
        trigger_policy=SimulationTriggerPolicy.always,
        check_ids=["inspection_consistency"],
    )
    simulation_report = SimulationReport(
        run_id=run.run_id,
        preset_id=run.preset_id,
        policy_id=simulation_policy.policy_id,
        trigger_policy=simulation_policy.trigger_policy,
        simulator_name="local_consistency_check",
        triggered=True,
        status="passed",
        reason="triggered_by_always_policy",
        summary="Simulation passed.",
        check_results=[],
    )
    simulation_record = SimulationRecord(
        run_id=run.run_id,
        policy_id=simulation_policy.policy_id,
        status=simulation_report.status,
        triggered=simulation_report.triggered,
        summary=simulation_report.summary,
        recorded_from=SimulationRecordSource.lifecycle_terminal,
        report=simulation_report,
    )
    mutation_contract = MutationContract(
        task_card_ref="M16-1A",
        task_card_path="docs/current_development_workflow.md",
        write_set=["packages/core_domain/services.py"],
        read_set=["packages/contracts/models.py"],
        test_commands=["python -m pytest tests/test_execution_loop.py -q"],
        max_fix_iterations=1,
        mutation_mode=MutationMode.patch_apply,
    )
    mutation_result = RepoMutationResult(
        changed_files=["packages/core_domain/services.py"],
        applied_patch_hash="abc123",
        test_attempts=[{"iteration": 0, "command": "pytest", "return_code": 0, "passed": True}],
        fix_iteration_count=0,
        final_test_status="passed",
    )
    control_plane_identity = ControlPlaneIdentity(
        control_plane_id="control_plane_alpha",
        name="alpha",
        endpoint="http://alpha.local",
    )
    scheduler_proposal = SchedulerLeaseProposal(
        control_plane_id=control_plane_identity.control_plane_id,
        run_id=run.run_id,
        runtime_task_id=runtime_task.runtime_task_id,
        domain_key=runtime_task.runtime_task_id,
    )
    scheduler_decision = SchedulerLeaseDecision(
        proposal_id=scheduler_proposal.proposal_id,
        control_plane_id=control_plane_identity.control_plane_id,
        run_id=run.run_id,
        runtime_task_id=runtime_task.runtime_task_id,
        domain_key=runtime_task.runtime_task_id,
        lease_epoch=1,
        lease_expires_at=run.created_at,
    )
    scheduler_heartbeat = SchedulerPeerHeartbeat(
        control_plane_id=control_plane_identity.control_plane_id,
        lease_count=1,
        observed_at=run.created_at,
    )

    models = [
        run,
        phase,
        task_card,
        runtime_task,
        packet,
        evidence,
        verdict,
        handoff,
        state_ref,
        suggestion,
        capability_route,
        domain_pack,
        claim,
        snapshot,
        ledger,
        worker_lease,
        runtime_attempt,
        memory_namespace,
        memory_candidate,
        memory_item,
        memory_retrieval_preview,
        simulation_policy,
        simulation_report,
        simulation_record,
        mutation_contract,
        mutation_result,
        control_plane_identity,
        scheduler_proposal,
        scheduler_decision,
        scheduler_heartbeat,
    ]
    for model in models:
        dumped = model.model_dump(mode="json")
        if "schema_version" in dumped:
            assert dumped["schema_version"] == "v1"
        if "created_at" in dumped:
            assert dumped["created_at"]
        restored = type(model).model_validate(dumped)
        assert restored.model_dump(mode="json") == dumped


def test_review_verdict_defaults_to_auto_reviewer() -> None:
    verdict = ReviewVerdict(
        run_id="run_123",
        evidence_id="evidence_123",
        decision=ReviewDecision.pass_,
        rationale="looks good",
    )
    assert verdict.reviewer_type == "auto"


def test_run_status_supports_awaiting_review() -> None:
    run = Run(goal="await human review", preset_id="research_spike", status="awaiting_review")
    assert run.status == "awaiting_review"


def test_run_status_transition_matrix_is_explicit() -> None:
    assert can_transition_run_status("pending", "prepared") is True
    assert can_transition_run_status("prepared", "running") is True
    assert can_transition_run_status("running", "awaiting_review") is True
    assert can_transition_run_status("awaiting_review", "completed") is True
    assert can_transition_run_status("completed", "running") is False
    assert can_transition_run_status("failed", "prepared") is False
    assert can_transition_run_status("cancelled", "awaiting_review") is False
    assert {str(status) for status in allowed_run_status_transitions("prepared")} == {
        "prepared",
        "running",
        "cancelled",
    }
    assert {str(status) for status in RUN_STATUS_TRANSITIONS[RunStatus.awaiting_review]} == {
        "completed",
        "failed",
        "cancelled",
    }


def test_runtime_graph_step_terminality_is_explicit() -> None:
    assert RuntimeGraphStep.completed in TERMINAL_RUNTIME_GRAPH_STEPS
    assert RuntimeGraphStep.compiled in NON_TERMINAL_RUNTIME_GRAPH_STEPS

    state_ref = RuntimeStateRef(
        run_id="run_123",
        runtime_task_id="task_123",
        graph_step=RuntimeGraphStep.compiled,
        state_payload={"entrypoint": "resume"},
    )
    assert state_ref.is_terminal is False

    with pytest.raises(ValidationError):
        RuntimeStateRef(
            run_id="run_123",
            runtime_task_id="task_123",
            graph_step=RuntimeGraphStep.completed,
            state_payload={},
            is_terminal=False,
        )


def test_runtime_claim_requires_release_metadata_when_not_active() -> None:
    active_claim = RuntimeClaim(
        run_id="run_123",
        runtime_task_id="task_123",
        lease_expires_at=Run(goal="g", preset_id="feature_delivery").created_at,
    )
    assert active_claim.status == "active"
    assert active_claim.owner_kind == "control_plane"
    assert active_claim.owner_id == "control_plane_local"
    assert active_claim.domain_kind == "runtime_task"
    assert active_claim.domain_key == "task_123"

    with pytest.raises(ValidationError):
        RuntimeClaim(
            run_id="run_123",
            runtime_task_id="task_123",
            status=RuntimeClaimStatus.released,
            lease_expires_at=Run(goal="g", preset_id="feature_delivery").created_at,
        )


def test_run_snapshot_requires_lightweight_projection_fields() -> None:
    snapshot = RunSnapshot(
        run_id="run_123",
        stage=RunSnapshotStage.repaired,
        run_status=RunStatus.prepared,
        summary="Repair snapshot",
        snapshot_payload={"problem": "prepared_compile_snapshot_incomplete"},
    )

    dumped = snapshot.model_dump(mode="json")
    assert dumped["stage"] == "repaired"
    assert dumped["run_status"] == "prepared"
    assert dumped["snapshot_payload"]["problem"] == "prepared_compile_snapshot_incomplete"


def test_budget_ledger_tracks_non_negative_counters() -> None:
    ledger = BudgetLedger(
        run_id="run_123",
        preset_id="feature_delivery",
        max_retries=1,
        timeout_seconds=120,
        compile_count=1,
        execution_count=1,
        total_runtime_ms=55,
        last_return_code=0,
    )
    dumped = ledger.model_dump(mode="json")
    assert dumped["compile_count"] == 1
    assert dumped["execution_count"] == 1
    assert dumped["total_runtime_ms"] == 55


def test_worker_lease_requires_release_metadata_when_not_active() -> None:
    active_lease = WorkerLease(
        run_id="run_123",
        runtime_task_id="task_123",
        adapter_name="shell",
        lease_expires_at=Run(goal="g", preset_id="feature_delivery").created_at,
    )
    assert active_lease.status == "active"
    assert active_lease.worker_kind == "worker"
    assert active_lease.worker_id == "worker_local"
    assert active_lease.domain_kind == "runtime_task"
    assert active_lease.domain_key == "task_123"

    with pytest.raises(ValidationError):
        WorkerLease(
            run_id="run_123",
            runtime_task_id="task_123",
            adapter_name="shell",
            status=WorkerLeaseStatus.released,
            lease_expires_at=Run(goal="g", preset_id="feature_delivery").created_at,
        )


def test_runtime_attempt_requires_supersede_or_close_metadata() -> None:
    current_attempt = RuntimeAttempt(
        run_id="run_123",
        runtime_task_id="task_123",
        sequence_no=1,
        trigger=RuntimeAttemptTrigger.compile,
    )
    assert current_attempt.status == "current"

    superseded_attempt = RuntimeAttempt(
        run_id="run_123",
        runtime_task_id="task_123",
        sequence_no=1,
        trigger=RuntimeAttemptTrigger.compile,
        status=RuntimeAttemptStatus.superseded,
        superseded_by_attempt_id="attempt_next",
        superseded_at=Run(goal="g", preset_id="feature_delivery").created_at,
        supersede_reason="recompile",
    )
    assert superseded_attempt.status == "superseded"

    with pytest.raises(ValidationError):
        RuntimeAttempt(
            run_id="run_123",
            runtime_task_id="task_123",
            sequence_no=1,
            trigger=RuntimeAttemptTrigger.resume,
            status=RuntimeAttemptStatus.interrupted,
        )

    with pytest.raises(ValidationError):
        RuntimeAttempt(
            run_id="run_123",
            runtime_task_id="task_123",
            sequence_no=1,
            trigger=RuntimeAttemptTrigger.compile,
            status=RuntimeAttemptStatus.current,
            close_reason="should-not-be-set",
        )


def test_preset_seed_file_parses() -> None:
    presets = load_seed_presets(Path("infra/seeds/presets.json"))
    assert {preset.preset_id for preset in presets} == {
        "feature_delivery",
        "optional_delivery",
        "research_spike",
        "research_spike_reviewable",
        "advisory_delivery",
        "guarded_delivery",
        "project_delivery",
        "guarded_project_delivery",
    }
    for preset in presets:
        assert isinstance(preset, PresetDefinition)
        assert preset.default_budget_policy.timeout_seconds > 0


def test_m31_graph_and_capability_contracts_round_trip() -> None:
    run = Run(goal="Validate M31 additive contracts", preset_id="guarded_project_delivery")
    descriptor = CapabilityDescriptor(
        capability_id="adapter_route:shell_exec:shell",
        provider_kind="adapter_route",
        transport="local_cli",
        auth_mode="local_process",
        scopes=["ShellAdapter"],
        allowed_task_kinds=[TaskKind.shell_exec],
        display_name="shell route",
        source_type=CapabilitySourceType.built_in,
        adapter_name="shell",
    )
    health = CapabilityHealth(
        descriptor=descriptor,
        status="ready",
        runtime_probe_status="runtime_ready",
        runtime_probe_detail={"adapter_name": "shell"},
    )
    envelope = CapabilityInvocationEnvelope(
        run_id=run.run_id,
        runtime_task_id="task_demo",
        preset_id=run.preset_id,
        task_kind=TaskKind.shell_exec,
        lane_type=ExecutionLaneType.repo_change_controlled,
        review_policy="mandatory",
        authority_mode="single_store_quorum",
        descriptor=descriptor,
        tool_projection_id="projection_demo",
        mutation_mode=MutationMode.patch_apply,
    )
    receipt = CapabilityExecutionReceipt(
        envelope=envelope,
        adapter_name="shell",
        return_code=0,
        started_at=run.created_at,
        finished_at=run.created_at,
        artifact_paths=["state/artifacts/demo.md"],
        metadata={"source": "test"},
        control_plane_id="control_plane_local",
    )
    planner = OrchestrationGraphNode(
        node_id="node_planner",
        role=AgentRoleType.planner,
        goal="decompose goal",
        required_capabilities=["planner"],
    )
    reviewer = OrchestrationGraphNode(
        node_id="node_reviewer",
        role=AgentRoleType.reviewer,
        goal="review result",
        required_capabilities=["reviewer"],
        dependencies=["node_planner"],
        barrier_id="barrier_review",
        retry_policy_id="retry_default",
        review_gate="advisory_review",
    )
    graph = OrchestrationPlanGraph(
        run_id=run.run_id,
        preset_id=run.preset_id,
        goal=run.goal,
        execution_mode="planner_generated_graph_with_parallel_children",
        nodes=[planner, reviewer],
        edges=[
            EdgeSpec(
                from_node_id="node_planner",
                to_node_id="node_reviewer",
                description="planner_to_reviewer",
            )
        ],
        barriers=[
            BarrierSpec(
                barrier_id="barrier_review",
                label="wait_for_parallel_children",
                member_node_ids=["node_reviewer"],
            )
        ],
        retry_policies=[RetryPolicy(policy_id="retry_default", target_node_ids=["node_reviewer"], max_attempts=2)],
    )

    for model in [descriptor, health, envelope, receipt, graph]:
        dumped = model.model_dump(mode="json")
        restored = type(model).model_validate(dumped)
        assert restored.model_dump(mode="json") == dumped

    assert health.runtime_probe_status == "runtime_ready"
    assert envelope.authority_mode == "single_store_quorum"
    assert graph.engine_version == "m31_v1"
    assert graph.barriers[0].member_node_ids == ["node_reviewer"]


def test_m32_interaction_and_cluster_contracts_round_trip() -> None:
    profile_registry = AgentProfileRegistry(
        profiles=[
            AgentProfileDefinition(
                profile_id="planner_architect",
                name="Planner Architect",
                description="Decomposes broad goals into bounded workstreams.",
                public_role=AgentRoleType.planner,
                role_label="architect",
                capability_tags=["planning", "decomposition"],
                repo_scope_paths=["docs/"],
                capability_scope_tags=["plan_graph"],
                visibility=ProfileVisibility.public,
                system_brief="Prefer explicit handoffs and bounded scope.",
                termination_rule=TerminationRule(
                    max_turns=8,
                    completion_signals=["handoff graph published"],
                ),
                evaluation_rubric=RoleEvaluationRubric(
                    criteria=["work is decomposed", "handoffs are explicit"],
                    required_artifacts=["plan_graph"],
                    minimum_confidence=0.75,
                ),
            )
        ],
        generated_profiles=[
            GeneratedAgentProfile(
                base_profile_id="planner_architect",
                source_type=GeneratedProfileSource.interaction_generated,
                public_role=AgentRoleType.planner,
                role_label="architect",
                session_id="intent_session_123",
                cluster_template_id="dev_cluster",
            )
        ],
    )
    intent_packet = IntentPacket(
        goal="Coordinate a multi-role project delivery slice",
        constraints=["keep operator checkpoints visible"],
        assumptions=["workspace is clean"],
        preferred_preset_id="project_delivery",
        preferred_cluster_template_ids=["dev_cluster"],
    )
    clarification_state = ClarificationState()
    session = IntentSession(intent_packet=intent_packet, clarification_state=clarification_state)
    assert session.status == IntentSessionStatus.open
    plan_draft = PlanDraft(
        session_id=session.session_id,
        status=PlanDraftStatus.ready,
        summary="Launch the dev cluster path.",
        selected_preset_id="project_delivery",
        selected_cluster_template_ids=["dev_cluster"],
        plan_graph={"cluster_template_ids": ["dev_cluster"]},
        policy_preview={"recommended_operator_mode": "human_visible"},
        capability_preview={"selected_clusters": [{"template_id": "dev_cluster"}]},
    )
    launch_decision = LaunchDecision(
        session_id=session.session_id,
        approved=True,
        execute=False,
        selected_preset_id="project_delivery",
        selected_cluster_template_ids=["dev_cluster"],
        rationale="ready to launch",
    )
    cluster_template = ExecutionClusterTemplate(
        template_id="dev_cluster",
        name="DevCluster",
        description="Planner-led delivery cluster with a guarded operator lane.",
        domain_tags=["software_delivery", "project_delivery"],
        primary_public_role=AgentRoleType.operator,
        member_specs=[
            ClusterMemberSpec(
                member_id="dev_cluster_architect",
                public_role=AgentRoleType.planner,
                agent_profile_id="planner_architect",
                role_label="architect",
                responsibilities=["decompose scope"],
            ),
            ClusterMemberSpec(
                member_id="dev_cluster_implementer",
                public_role=AgentRoleType.coder,
                agent_profile_id="coder_implementer",
                role_label="implementer",
                responsibilities=["apply bounded repo changes"],
                parallel_group="delivery_parallel",
            ),
        ],
        default_review_policy=ReviewPolicy.recommended,
        execution_mode=ClusterExecutionMode.parallel,
        review_rubric=ClusterReviewRubric(
            name="DevCluster Review Rubric",
            criteria=["implementation is bounded", "launch visibility remains intact"],
            required_artifacts=["plan_graph", "code_diff"],
            escalation_conditions=["missing review evidence"],
        ),
    )
    cluster_plan = ClusterExecutionPlan(
        cluster_template_id=cluster_template.template_id,
        run_id="run_123",
        session_id=session.session_id,
        objective=intent_packet.goal,
        selected_member_ids=["dev_cluster_architect", "dev_cluster_implementer"],
        handoff_points=["architect -> implementer"],
        success_criteria=["delivery completes without blocking escalations"],
    )
    cluster_handoff = ClusterHandoffPacket(
        cluster_template_id=cluster_template.template_id,
        from_member_id="dev_cluster_architect",
        to_member_id="dev_cluster_implementer",
        handoff_summary="architect hands execution to implementer",
        artifact_refs=["run:run_123"],
    )
    cluster_output = ClusterOutputPacket(
        cluster_template_id=cluster_template.template_id,
        run_id="run_123",
        objective=intent_packet.goal,
        summary="cluster output summary",
        handoff_packets=[cluster_handoff],
    )

    models = [
        profile_registry,
        intent_packet,
        session,
        plan_draft,
        launch_decision,
        cluster_template,
        cluster_plan,
        cluster_handoff,
        cluster_output,
    ]
    for model in models:
        dumped = model.model_dump(mode="json")
        restored = type(model).model_validate(dumped)
        assert restored.model_dump(mode="json") == dumped


def test_memory_namespace_seed_file_parses() -> None:
    namespaces = load_seed_memory_namespaces(Path("infra/seeds/memory_namespaces.json"))
    assert [namespace.namespace_id for namespace in namespaces] == ["repo", "failure", "policy", "release"]
    assert namespaces[0].retrieval_policy == "rule_based_context_pack"


def test_simulation_policy_seed_file_parses() -> None:
    policies = load_seed_simulation_policies(Path("infra/seeds/simulation_policies.json"))
    assert [policy.policy_id for policy in policies] == [
        "delivery_consistency_simulation",
        "advisory_failure_simulation",
        "research_no_simulation",
    ]
    assert policies[0].trigger_policy == "always"
    assert policies[1].simulator_name == "local_consistency_check"


def test_manual_preset_selection_is_required_and_strict() -> None:
    resolver = PresetResolver()
    with pytest.raises(PresetRequiredError):
        resolver.manual_select(None)
    with pytest.raises(PresetNotFoundError):
        resolver.manual_select("missing")
    preset = resolver.manual_select("feature_delivery")
    assert preset.preset_id == "feature_delivery"


def test_domain_pack_seed_file_parses() -> None:
    domain_packs = load_seed_domain_packs(Path("infra/seeds/domain_packs.json"))
    assert [domain_pack.domain_pack_id for domain_pack in domain_packs] == ["software_delivery_pack"]
    assert domain_packs[0].enabled is True
    assert domain_packs[0].match.preset_ids == [
        "feature_delivery",
        "optional_delivery",
        "advisory_delivery",
        "guarded_delivery",
    ]
    assert domain_packs[0].compile_projection.artifact_label == "software_delivery"
    assert domain_packs[0].capability_exposure.preferred_adapter_name == "shell"
    assert domain_packs[0].runtime_projection.operator_label == "software-delivery"


def test_domain_pack_definition_supports_flat_shape_upgrade() -> None:
    domain_pack = DomainPackDefinition.model_validate(
        {
            "domain_pack_id": "flat_pack",
            "name": "Flat Pack",
            "description": "legacy flat shape",
            "preset_ids": ["feature_delivery"],
            "task_kinds": ["shell_exec"],
            "artifact_label": "legacy",
            "goal_prefix": "[legacy]",
        }
    )

    assert domain_pack.match.preset_ids == ["feature_delivery"]
    assert domain_pack.compile_projection.artifact_label == "legacy"
    assert domain_pack.goal_prefix == "[legacy]"


def test_domain_pack_resolution_round_trip() -> None:
    resolution = DomainPackResolution.model_validate(
        {
            "domain_pack_id": "software_delivery_pack",
            "name": "Software Delivery Pack",
            "description": "test resolution",
            "matched_preset_id": "feature_delivery",
            "matched_task_kind": "shell_exec",
            "capability_exposure": {
                "preferred_adapter_name": "shell",
                "capability_tags": ["artifact_generation"],
            },
            "compile_projection": {
                "artifact_label": "software_delivery",
                "goal_prefix": "[software-delivery]",
                "artifact_context_lines": ["domain_context: software_delivery"],
            },
            "runtime_projection": {
                "operator_label": "software-delivery",
                "evidence_expectations": ["artifact exists"],
            },
        }
    )

    dumped = resolution.model_dump(mode="json")
    restored = DomainPackResolution.model_validate(dumped)
    assert restored.model_dump(mode="json") == dumped


def test_domain_pack_catalog_validation_reports_invalid_preferred_adapter() -> None:
    presets = load_seed_presets(Path("infra/seeds/presets.json"))
    registry = DomainPackRegistry(
        [
            DomainPackDefinition.model_validate(
                {
                    "domain_pack_id": "bad_pack",
                    "name": "Bad Pack",
                    "description": "invalid preferred adapter",
                    "match": {
                        "preset_ids": ["feature_delivery"],
                        "task_kinds": ["shell_exec"],
                    },
                    "capability_exposure": {
                        "preferred_adapter_name": "missing_adapter",
                        "capability_tags": [],
                    },
                    "compile_projection": {
                        "artifact_label": "bad",
                    },
                    "runtime_projection": {
                        "operator_label": "bad-pack",
                    },
                }
            )
        ]
    )

    report = registry.validate_catalog(
        presets,
        [
            {"capability": "shell_exec", "adapter_name": "shell", "adapter_class": "ShellAdapter"},
            {"capability": "noop", "adapter_name": "noop", "adapter_class": "NoopAdapter"},
        ],
    )

    assert report["passed"] is False
    assert report["issue_count"] == 1
    assert report["issues"][0]["issue_code"] == "preferred_adapter_unavailable"


def test_preset_suggestions_are_deterministic_and_explained() -> None:
    resolver = PresetResolver()
    suggestions = resolver.suggest("Research and compare implementation options")
    assert suggestions[0].preset_id == "research_spike"
    assert suggestions[0].score >= suggestions[1].score
    assert suggestions[0].reason

    guarded = resolver.suggest("Sensitive compliance change that needs approval")
    assert guarded[0].preset_id == "guarded_delivery"
    assert guarded[0].reason

    fallback = resolver.suggest("General task")
    assert [item.preset_id for item in fallback] == [
        "feature_delivery",
        "optional_delivery",
        "research_spike",
        "advisory_delivery",
        "guarded_delivery",
        "research_spike_reviewable",
        "project_delivery",
        "guarded_project_delivery",
    ]
    assert all(item.reason for item in fallback)


def test_budget_policy_value_domains_are_validated() -> None:
    with pytest.raises(ValidationError):
        PresetDefinition.model_validate(
            {
                "preset_id": "bad",
                "name": "Bad Preset",
                "description": "invalid budget policy",
                "allowed_task_kinds": ["shell_exec"],
                "default_review_policy": "auto_only",
                "default_budget_policy": {"max_retries": -1, "timeout_seconds": 0},
            }
        )


def test_patch_apply_mutation_contract_requires_write_set() -> None:
    with pytest.raises(ValidationError):
        MutationContract(
            mutation_mode=MutationMode.patch_apply,
        )
