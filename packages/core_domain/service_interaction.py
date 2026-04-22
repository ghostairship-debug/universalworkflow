from __future__ import annotations

from typing import Any

from packages.contracts import (
    AgentRoleType,
    ClarificationPrompt,
    ClarificationState,
    ClusterExecutionPlan,
    ClusterHandoffPacket,
    ClusterOutputPacket,
    ExecutionClusterTemplate,
    FollowupRequest,
    IntentPacket,
    IntentSession,
    IntentSessionStatus,
    LaunchDecision,
    OrchestrationBarrier,
    OrchestrationPlan,
    OrchestrationStep,
    PlanDraft,
    PlanDraftStatus,
    RoleAssignment,
)
from packages.core_domain.cluster_router import ClusterRouter
from packages.core_domain.errors import EntityNotFoundError, WorkflowError
from packages.core_domain.interaction_catalog import (
    build_default_agent_profile_registry,
    default_preset_id_for_cluster_template,
    fallback_adapter_for_cluster_member,
    list_default_cluster_templates,
    member_preset_id,
    preferred_adapter_for_cluster_member,
    sequence_no_for_cluster_member,
)


class InteractionServiceMixin:
    def get_agent_profile_registry(self):
        return build_default_agent_profile_registry()

    def list_agent_profiles(self):
        return self.get_agent_profile_registry().profiles

    def list_cluster_templates(self) -> list[ExecutionClusterTemplate]:
        return list_default_cluster_templates()

    def get_cluster_template(self, template_id: str) -> ExecutionClusterTemplate:
        template = next((item for item in self.list_cluster_templates() if item.template_id == template_id), None)
        if template is None:
            raise EntityNotFoundError("cluster_template", template_id)
        return template

    def _cluster_router(self) -> ClusterRouter:
        return ClusterRouter(self.list_cluster_templates())

    def _default_clarification_state(self, intent_packet: IntentPacket) -> ClarificationState:
        prompts: list[ClarificationPrompt] = []
        normalized_goal = intent_packet.goal.strip()
        if len(normalized_goal) < 24 or len(normalized_goal.split()) < 4:
            prompts.append(
                ClarificationPrompt(
                    prompt_id="clarify_target_artifact",
                    question="What concrete artifact, decision, or outcome should this produce?",
                    required=True,
                    source="interaction_plane",
                )
            )
        if (
            any(marker in normalized_goal.lower() for marker in {"project", "delivery", "multi", "cluster", "research"})
            and not intent_packet.preferred_cluster_template_ids
        ):
            prompts.append(
                ClarificationPrompt(
                    prompt_id="clarify_cluster_preference",
                    question="Should this stay on a single preset path, or should it use a cluster template?",
                    required=False,
                    source="interaction_plane",
                    status="not_needed",
                )
            )
        return ClarificationState(prompts=prompts) if prompts else ClarificationState()

    def _selected_cluster_template_ids(
        self,
        *,
        goal: str,
        preset_id: str | None = None,
        preferred_cluster_template_ids: list[str] | None = None,
        plan_graph: dict[str, Any] | None = None,
    ) -> list[str]:
        if preferred_cluster_template_ids:
            return self._cluster_router().suggest_template_ids(
                goal=goal,
                preset_id=preset_id,
                preferred_template_ids=preferred_cluster_template_ids,
            )
        graph_template_ids = (
            plan_graph.get("cluster_template_ids", [])
            if isinstance(plan_graph, dict)
            else []
        )
        if graph_template_ids:
            return self._cluster_router().suggest_template_ids(
                goal=goal,
                preset_id=preset_id,
                preferred_template_ids=list(graph_template_ids),
            )
        return self._cluster_router().suggest_template_ids(goal=goal, preset_id=preset_id)

    def _cluster_templates_for_ids(self, template_ids: list[str]) -> list[ExecutionClusterTemplate]:
        templates: list[ExecutionClusterTemplate] = []
        seen: set[str] = set()
        for template_id in template_ids:
            if template_id in seen:
                continue
            seen.add(template_id)
            template = self._cluster_router().get_template(template_id)
            if template is not None:
                templates.append(template)
        return templates

    def _cluster_member_goal(self, goal: str, template_id: str, role_label: str, public_role: AgentRoleType) -> str:
        role_map = {
            "architect": f"Design the work breakdown and integration handoffs for: {goal}",
            "implementer": f"Implement the primary delivery slice for: {goal}",
            "risk_mapper": f"Research risks, supporting evidence, and open questions for: {goal}",
            "quality_gate": f"Review the implementation and supporting evidence for: {goal}",
            "launch_guard": f"Prepare the operator-facing launch and follow-up checkpoint for: {goal}",
            "research_analyst": f"Investigate and summarize findings for: {goal}",
            "citation_checker": f"Verify citations, claims, and confidence posture for: {goal}",
        }
        if role_label in role_map:
            return role_map[role_label]
        if public_role == AgentRoleType.planner:
            return f"Plan the work for: {goal}"
        if public_role == AgentRoleType.coder:
            return f"Implement the requested change for: {goal}"
        if public_role == AgentRoleType.researcher:
            return f"Research and summarize evidence for: {goal}"
        if public_role == AgentRoleType.reviewer:
            return f"Review the output for: {goal}"
        return f"Keep operator control visible for: {goal}"

    def _cluster_orchestration_plan(
        self,
        *,
        template: ExecutionClusterTemplate,
        goal: str,
        selected_preset_id: str | None = None,
        run_id: str | None = None,
    ) -> OrchestrationPlan:
        return self.orchestration_service.build_cluster_orchestration_plan(
            template=template,
            selected_preset_id=selected_preset_id,
            run_id=run_id,
            include_operator_step=False,
        )

    def _preview_cluster_graph(
        self,
        *,
        goal: str,
        selected_preset_id: str | None,
        selected_cluster_template_ids: list[str],
        plan_graph: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        templates = self._cluster_templates_for_ids(selected_cluster_template_ids)
        if not templates:
            return None
        template = templates[0]
        plan = self._cluster_orchestration_plan(
            template=template,
            goal=goal,
            selected_preset_id=selected_preset_id,
        )
        graph = self.orchestration_engine.build_graph_from_plan(
            run_id=None,
            preset_id=selected_preset_id or plan.preset_id,
            goal=goal,
            plan=plan,
            role_goal_for=lambda parent_goal, role: self._cluster_member_goal(
                parent_goal,
                template.template_id,
                next(
                    (
                        member.role_label
                        for member in template.member_specs
                        if member.public_role == role
                    ),
                    str(role),
                ),
                role,
            ),
            side_effect_level_for_adapter=self._side_effect_level_for_adapter,
            recommended_preset_id=selected_preset_id or plan.preset_id,
            summary=f"{template.name} preview graph for `{selected_preset_id or plan.preset_id}`.",
            risk_summary=[
                f"cluster template `{template.template_id}` is a preview projection layered on top of the shared execution substrate",
            ],
        )
        return graph.model_dump(mode="json")

    def _cluster_policy_preview_payload(
        self,
        *,
        cluster_graph: dict[str, Any] | None,
        selected_clusters: list[ExecutionClusterTemplate],
    ) -> dict[str, Any]:
        if cluster_graph is None:
            return {"enabled": False, "cluster_policy_preview": None}
        capability_policy = self._capability_policy_preview_for_plan_graph(cluster_graph)
        return {
            "enabled": True,
            "selected_cluster_template_ids": [template.template_id for template in selected_clusters],
            "template_summaries": [
                {
                    "template_id": template.template_id,
                    "name": template.name,
                    "execution_mode": str(template.execution_mode),
                    "member_count": len(template.member_specs),
                    "default_review_policy": str(template.default_review_policy),
                }
                for template in selected_clusters
            ],
            "policy_preview": capability_policy,
            "recommended_operator_mode": capability_policy["recommended_operator_mode"],
            "requires_human_checkpoint": capability_policy["requires_human_checkpoint"],
        }

    def _cluster_execution_plans(
        self,
        *,
        goal: str,
        selected_clusters: list[ExecutionClusterTemplate],
        session_id: str | None = None,
        run_id: str | None = None,
    ) -> list[ClusterExecutionPlan]:
        plans: list[ClusterExecutionPlan] = []
        for template in selected_clusters:
            sequence_groups: dict[int, list[str]] = {}
            for member in template.member_specs:
                sequence_groups.setdefault(
                    sequence_no_for_cluster_member(template.template_id, member.role_label, member.public_role),
                    [],
                ).append(member.role_label)
            plans.append(
                ClusterExecutionPlan(
                    cluster_plan_id=f"{template.template_id}_{session_id or run_id or 'preview'}",
                    cluster_template_id=template.template_id,
                    run_id=run_id,
                    session_id=session_id,
                    objective=goal,
                    selected_member_ids=[member.member_id for member in template.member_specs],
                    handoff_points=[
                        " -> ".join(sequence_groups[sequence_no])
                        for sequence_no in sorted(sequence_groups)
                    ],
                    success_criteria=(
                        list(template.review_rubric.criteria)
                        if template.review_rubric is not None
                        else [f"{template.name} completes without blocking escalations"]
                    ),
                    status="planned" if run_id is None else "active",
                )
            )
        return plans

    def _cluster_preview_bundle(
        self,
        *,
        goal: str,
        selected_preset_id: str | None,
        plan_graph: dict[str, Any] | None,
        preferred_cluster_template_ids: list[str] | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        selected_cluster_template_ids = self._selected_cluster_template_ids(
            goal=goal,
            preset_id=selected_preset_id,
            preferred_cluster_template_ids=preferred_cluster_template_ids,
            plan_graph=plan_graph,
        )
        selected_clusters = self._cluster_templates_for_ids(selected_cluster_template_ids)
        cluster_graph = self._preview_cluster_graph(
            goal=goal,
            selected_preset_id=selected_preset_id,
            selected_cluster_template_ids=selected_cluster_template_ids,
            plan_graph=plan_graph,
        )
        return {
            "selected_cluster_template_ids": selected_cluster_template_ids,
            "selected_clusters": selected_clusters,
            "cluster_graph": cluster_graph,
            "cluster_policy_preview": self._cluster_policy_preview_payload(
                cluster_graph=cluster_graph,
                selected_clusters=selected_clusters,
            ),
            "cluster_execution_plans": self._cluster_execution_plans(
                goal=goal,
                selected_clusters=selected_clusters,
                session_id=session_id,
                run_id=run_id,
            ),
        }

    def _cluster_member_progress(
        self,
        *,
        template: ExecutionClusterTemplate,
        run_status: str,
        orchestration: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        role_progress = orchestration.get("role_progress", {}) if isinstance(orchestration, dict) else {}
        member_progress: list[dict[str, Any]] = []
        for member in template.member_specs:
            progress = role_progress.get(str(member.public_role), {})
            member_status = str(progress.get("status") or ("completed" if run_status == "completed" else "pending"))
            member_progress.append(
                {
                    "member_id": member.member_id,
                    "role": str(member.public_role),
                    "role_label": member.role_label,
                    "status": member_status,
                    "run_id": progress.get("run_id"),
                    "parallel_group": member.parallel_group,
                }
            )
        return member_progress

    def _cluster_handoff_packets_for_template(
        self,
        *,
        template: ExecutionClusterTemplate,
        goal: str,
        member_progress: list[dict[str, Any]],
    ) -> list[ClusterHandoffPacket]:
        member_by_sequence: dict[int, list[dict[str, Any]]] = {}
        spec_by_id = {member.member_id: member for member in template.member_specs}
        for item in member_progress:
            spec = spec_by_id[item["member_id"]]
            sequence = sequence_no_for_cluster_member(template.template_id, spec.role_label, spec.public_role)
            member_by_sequence.setdefault(sequence, []).append(item)
        handoffs: list[ClusterHandoffPacket] = []
        ordered_sequences = sorted(member_by_sequence)
        for index, source_sequence in enumerate(ordered_sequences[:-1]):
            target_sequence = ordered_sequences[index + 1]
            for source in member_by_sequence[source_sequence]:
                for target in member_by_sequence[target_sequence]:
                    blocking = []
                    if source["status"] not in {"completed", "awaiting_review"}:
                        blocking.append(f"{source['role_label']} has not completed its handoff output yet")
                    handoffs.append(
                        ClusterHandoffPacket(
                            cluster_handoff_id=(
                                f"{template.template_id}_{source['member_id']}_{target['member_id']}"
                            ),
                            cluster_template_id=template.template_id,
                            from_member_id=source["member_id"],
                            to_member_id=target["member_id"],
                            handoff_summary=(
                                f"{source['role_label']} hands execution to {target['role_label']} for `{goal}`"
                            ),
                            artifact_refs=(
                                [f"run:{source['run_id']}"] if source.get("run_id") else []
                            ),
                            blocking_risks=blocking,
                            escalation_flags=["pending_source_output"] if blocking else [],
                        )
                    )
        return handoffs

    def _cluster_runtime_bundle(
        self,
        *,
        goal: str,
        run_id: str,
        run_status: str,
        selected_preset_id: str,
        plan_graph: dict[str, Any] | None,
        orchestration: dict[str, Any] | None,
        summary_text: str,
    ) -> dict[str, Any]:
        preview_bundle = self._cluster_preview_bundle(
            goal=goal,
            selected_preset_id=selected_preset_id,
            plan_graph=plan_graph,
            run_id=run_id,
        )
        cluster_progress: list[dict[str, Any]] = []
        cluster_packets: list[dict[str, Any]] = []
        cluster_handoffs: list[dict[str, Any]] = []
        child_runs = orchestration.get("child_runs", []) if isinstance(orchestration, dict) else []
        for template in preview_bundle["selected_clusters"]:
            member_progress = self._cluster_member_progress(
                template=template,
                run_status=run_status,
                orchestration=orchestration,
            )
            completed_count = sum(1 for item in member_progress if item["status"] == "completed")
            handoff_packets = self._cluster_handoff_packets_for_template(
                template=template,
                goal=goal,
                member_progress=member_progress,
            )
            cluster_progress.append(
                {
                    "template_id": template.template_id,
                    "name": template.name,
                    "status": run_status,
                    "completed_member_count": completed_count,
                    "total_member_count": len(member_progress),
                    "member_progress": member_progress,
                }
            )
            cluster_handoffs.extend([packet.model_dump(mode="json") for packet in handoff_packets])
            cluster_packets.append(
                ClusterOutputPacket(
                    cluster_output_id=f"{template.template_id}_{run_id}",
                    cluster_template_id=template.template_id,
                    run_id=run_id,
                    objective=goal,
                    summary=summary_text,
                    risks=[
                        item.blocking_risks[0]
                        for item in handoff_packets
                        if item.blocking_risks
                    ],
                    artifact_refs=[f"run:{item['run_id']}" for item in child_runs if item.get("run_id")],
                    quality_verdict=(
                        "completed"
                        if run_status == "completed"
                        else ("awaiting_review" if run_status == "awaiting_review" else "in_progress")
                    ),
                    escalation_flags=[
                        "review_gate_open"
                        for item in handoff_packets
                        if item.blocking_risks
                    ],
                    handoff_packets=handoff_packets,
                ).model_dump(mode="json")
            )
        return {
            **preview_bundle,
            "cluster_progress": cluster_progress,
            "cluster_packets": cluster_packets,
            "cluster_handoffs": cluster_handoffs,
            "cluster_execution_lineage": {
                "selected_cluster_template_ids": preview_bundle["selected_cluster_template_ids"],
                "cluster_plan_ids": [
                    plan.cluster_plan_id
                    for plan in preview_bundle["cluster_execution_plans"]
                ],
                "orchestration_id": orchestration.get("orchestration_id") if isinstance(orchestration, dict) else None,
                "child_runs": child_runs,
                "member_run_count": len(child_runs),
            },
        }

    def _plan_draft_for_session(self, session: IntentSession) -> tuple[PlanDraft | None, dict[str, Any] | None]:
        if session.clarification_state.blocking:
            return None, None
        selected_cluster_template_ids = self._selected_cluster_template_ids(
            goal=session.intent_packet.goal,
            preset_id=session.intent_packet.preferred_preset_id,
            preferred_cluster_template_ids=session.intent_packet.preferred_cluster_template_ids,
        )
        selected_preset_id = session.intent_packet.preferred_preset_id
        if selected_preset_id is None and selected_cluster_template_ids:
            selected_preset_id = default_preset_id_for_cluster_template(selected_cluster_template_ids[0])
        goal_packet = self.preview_goal_packet(
            goal=session.intent_packet.goal,
            preset_id=selected_preset_id,
            preferred_cluster_template_ids=selected_cluster_template_ids,
        )
        selected_cluster_template_ids = [
            item["template_id"]
            for item in goal_packet.get("selected_clusters", [])
            if isinstance(item, dict) and item.get("template_id")
        ]
        draft = PlanDraft(
            draft_id=f"plan_draft_{session.session_id}",
            session_id=session.session_id,
            status=PlanDraftStatus.ready,
            summary=(
                f"Prepare `{goal_packet['selected_preset_id']}`"
                + (
                    f" with {', '.join(selected_cluster_template_ids)}"
                    if selected_cluster_template_ids
                    else " on the single-path preset route"
                )
            ),
            selected_preset_id=goal_packet["selected_preset_id"],
            selected_cluster_template_ids=selected_cluster_template_ids,
            plan_graph=goal_packet["plan_graph"],
            policy_preview=goal_packet["capability_policy_preview"],
            capability_preview=goal_packet,
            notes=[
                f"matched_capability_descriptors={len(goal_packet['matched_capability_descriptors'])}",
                f"selected_clusters={len(selected_cluster_template_ids)}",
            ],
        )
        return draft, goal_packet

    def _persist_session(self, session: IntentSession) -> IntentSession:
        self.intent_session_repo.upsert(session)
        return session

    def _interaction_payload(
        self,
        *,
        session: IntentSession,
        plan_draft: PlanDraft | None,
        goal_packet: dict[str, Any] | None,
        launch_decision: LaunchDecision | None = None,
        launch_payload: dict[str, Any] | None = None,
        followup_request: FollowupRequest | None = None,
    ) -> dict[str, Any]:
        return {
            "session": session.model_dump(mode="json"),
            "plan_draft": plan_draft.model_dump(mode="json") if plan_draft is not None else None,
            "goal_packet": goal_packet,
            "launch_decision": launch_decision.model_dump(mode="json") if launch_decision is not None else None,
            "launch_payload": launch_payload,
            "followup_request": followup_request.model_dump(mode="json") if followup_request is not None else None,
            "agent_profile_registry": self.get_agent_profile_registry().model_dump(mode="json"),
            "available_cluster_templates": [
                template.model_dump(mode="json") for template in self.list_cluster_templates()
            ],
        }

    def create_intent_session(
        self,
        *,
        goal: str,
        preferred_preset_id: str | None = None,
        preferred_cluster_template_ids: list[str] | None = None,
        constraints: list[str] | None = None,
        assumptions: list[str] | None = None,
        referenced_artifact_paths: list[str] | None = None,
        followup_context: list[str] | None = None,
    ) -> dict[str, Any]:
        intent_packet = IntentPacket(
            goal=goal,
            constraints=list(constraints or []),
            assumptions=list(assumptions or []),
            preferred_preset_id=preferred_preset_id,
            preferred_cluster_template_ids=list(preferred_cluster_template_ids or []),
            referenced_artifact_paths=list(referenced_artifact_paths or []),
            followup_context=list(followup_context or []),
        )
        clarification_state = self._default_clarification_state(intent_packet)
        session = IntentSession(
            status=IntentSessionStatus.clarifying if clarification_state.blocking else IntentSessionStatus.planning,
            intent_packet=intent_packet,
            clarification_state=clarification_state,
        )
        plan_draft, goal_packet = self._plan_draft_for_session(session)
        if plan_draft is not None:
            session.latest_plan_draft_id = plan_draft.draft_id
            session.status = IntentSessionStatus.ready_to_launch
        self._persist_session(session)
        return self._interaction_payload(session=session, plan_draft=plan_draft, goal_packet=goal_packet)

    def get_intent_session_payload(self, session_id: str) -> dict[str, Any]:
        session = self.intent_session_repo.get(session_id)
        if session is None:
            raise EntityNotFoundError("intent_session", session_id)
        plan_draft, goal_packet = self._plan_draft_for_session(session)
        if plan_draft is not None:
            session.latest_plan_draft_id = plan_draft.draft_id
            if session.active_run_id is None:
                session.status = IntentSessionStatus.ready_to_launch
            self._persist_session(session)
        return self._interaction_payload(session=session, plan_draft=plan_draft, goal_packet=goal_packet)

    def continue_intent_session(
        self,
        session_id: str,
        *,
        answers: dict[str, str] | None = None,
        preferred_preset_id: str | None = None,
        preferred_cluster_template_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        session = self.intent_session_repo.get(session_id)
        if session is None:
            raise EntityNotFoundError("intent_session", session_id)
        if preferred_preset_id is not None:
            session.intent_packet.preferred_preset_id = preferred_preset_id
        if preferred_cluster_template_ids is not None and preferred_cluster_template_ids:
            session.intent_packet.preferred_cluster_template_ids = list(preferred_cluster_template_ids)
        updated_prompts: list[ClarificationPrompt] = []
        answer_map = {key: value.strip() for key, value in (answers or {}).items() if value and value.strip()}
        for prompt in session.clarification_state.prompts:
            if prompt.prompt_id in answer_map:
                prompt.answer = answer_map[prompt.prompt_id]
            updated_prompts.append(prompt)
        session.clarification_state = ClarificationState(prompts=updated_prompts) if updated_prompts else ClarificationState()
        plan_draft, goal_packet = self._plan_draft_for_session(session)
        if session.clarification_state.blocking:
            session.status = IntentSessionStatus.clarifying
        elif plan_draft is not None:
            session.latest_plan_draft_id = plan_draft.draft_id
            session.status = IntentSessionStatus.ready_to_launch
        else:
            session.status = IntentSessionStatus.planning
        self._persist_session(session)
        return self._interaction_payload(session=session, plan_draft=plan_draft, goal_packet=goal_packet)

    def create_intent_plan_draft(
        self,
        session_id: str,
        *,
        preferred_preset_id: str | None = None,
        preferred_cluster_template_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.continue_intent_session(
            session_id,
            answers={},
            preferred_preset_id=preferred_preset_id,
            preferred_cluster_template_ids=preferred_cluster_template_ids,
        )

    def launch_intent_session(
        self,
        session_id: str,
        *,
        execute: bool = False,
        rationale: str | None = None,
        selected_preset_id: str | None = None,
        selected_cluster_template_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        session = self.intent_session_repo.get(session_id)
        if session is None:
            raise EntityNotFoundError("intent_session", session_id)
        if session.clarification_state.blocking:
            raise WorkflowError(
                "intent session still requires clarification before launch",
                {"session_id": session_id, "status": session.clarification_state.status},
            )
        if selected_preset_id is not None:
            session.intent_packet.preferred_preset_id = selected_preset_id
        if selected_cluster_template_ids is not None and selected_cluster_template_ids:
            session.intent_packet.preferred_cluster_template_ids = list(selected_cluster_template_ids)
        plan_draft, goal_packet = self._plan_draft_for_session(session)
        if plan_draft is None or goal_packet is None:
            raise WorkflowError("intent session could not produce a launchable plan draft", {"session_id": session_id})
        launch_payload = self.launch_goal(
            goal=session.intent_packet.goal,
            preset_id=plan_draft.selected_preset_id,
            preferred_cluster_template_ids=plan_draft.selected_cluster_template_ids,
            execute=execute,
        )
        launch_decision = LaunchDecision(
            session_id=session.session_id,
            approved=True,
            execute=execute,
            selected_preset_id=plan_draft.selected_preset_id,
            selected_cluster_template_ids=plan_draft.selected_cluster_template_ids,
            rationale=rationale,
            target_run_id=launch_payload["run"]["run_id"],
        )
        session.latest_plan_draft_id = plan_draft.draft_id
        session.active_run_id = launch_decision.target_run_id
        session.status = IntentSessionStatus.launched
        self._persist_session(session)
        return self._interaction_payload(
            session=session,
            plan_draft=plan_draft,
            goal_packet=goal_packet,
            launch_decision=launch_decision,
            launch_payload=launch_payload,
        )

    def create_followup_request(
        self,
        session_id: str,
        *,
        instruction: str,
        intent: str = "continue",
        blocking: bool = False,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        session = self.intent_session_repo.get(session_id)
        if session is None:
            raise EntityNotFoundError("intent_session", session_id)
        followup_request = FollowupRequest(
            session_id=session_id,
            run_id=run_id or session.active_run_id,
            instruction=instruction,
            intent=intent,
            blocking=blocking,
            status="pending",
        )
        return self._interaction_payload(
            session=session,
            plan_draft=None,
            goal_packet=None,
            followup_request=followup_request,
        )
