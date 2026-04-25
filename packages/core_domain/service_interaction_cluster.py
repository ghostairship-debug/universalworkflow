from __future__ import annotations

import os
from typing import Any

from packages.contracts import (
    AgentRoleType,
    AutomationWatchdog,
    ChatMessage,
    ChatMessageRole,
    ChatMessageStatus,
    ChatStreamEvent,
    ChatStreamEventType,
    ChatMessageType,
    ClarificationPrompt,
    ClarificationState,
    ClusterExecutionPlan,
    ClusterHandoffPacket,
    ClusterOutputPacket,
    ClusterRouteDecision,
    ExecutionClusterTemplate,
    FollowupRequest,
    GeneratedAgentProfile,
    GeneratedProfileSource,
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
    RunStatus,
    TerminationRule,
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
from packages.runtime_langgraph.chat_runtime import HIGH_RISK_CHAT_ACTIONS, ChatActionDecision




class ClusterPlanningServiceMixin:
    def list_cluster_templates(self) -> list[ExecutionClusterTemplate]:
        return list_default_cluster_templates()

    def get_cluster_template(self, template_id: str) -> ExecutionClusterTemplate:
        template = next((item for item in self.list_cluster_templates() if item.template_id == template_id), None)
        if template is None:
            raise EntityNotFoundError("cluster_template", template_id)
        return template

    def _cluster_router(self) -> ClusterRouter:
        return ClusterRouter(self.list_cluster_templates())

    @staticmethod
    def _contains_cjk(text: str) -> bool:
        return any("\u4e00" <= char <= "\u9fff" for char in text)

    def _goal_needs_target_clarification(self, goal: str) -> bool:
        normalized = goal.strip()
        if self._contains_cjk(normalized):
            concrete_markers = {
                "产出",
                "输出",
                "生成",
                "创建",
                "编写",
                "写",
                "实现",
                "修复",
                "改造",
                "清理",
                "测试",
                "验证",
                "报告",
                "文档",
                "说明",
                "计划",
                "摘要",
                "评估",
                "代码",
                "补丁",
                "文件",
                "界面",
                "功能",
            }
            return len(normalized) < 12 or not any(marker in normalized for marker in concrete_markers)
        return len(normalized) < 24 or len(normalized.split()) < 4

    def _default_clarification_state(self, intent_packet: IntentPacket) -> ClarificationState:
        prompts: list[ClarificationPrompt] = []
        normalized_goal = intent_packet.goal.strip()
        if self._goal_needs_target_clarification(normalized_goal):
            prompts.append(
                ClarificationPrompt(
                    prompt_id="clarify_target_artifact",
                    question="这次要产出的具体文档、代码改动、决策或结果是什么？",
                    required=True,
                    source="interaction_plane",
                )
            )
        if (
            any(
                marker in normalized_goal.lower()
                for marker in {"project", "delivery", "multi", "cluster", "research", "项目", "交付", "多", "集群", "研究", "调研"}
            )
            and not intent_packet.preferred_cluster_template_ids
        ):
            prompts.append(
                ClarificationPrompt(
                    prompt_id="clarify_cluster_preference",
                    question="这次保持单预设路径即可，还是需要使用集群模板？",
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
        source = "cluster_router"
        if preferred_cluster_template_ids:
            selected = self._cluster_router().suggest_template_ids(
                goal=goal,
                preset_id=preset_id,
                preferred_template_ids=preferred_cluster_template_ids,
            )
            self._record_cluster_route_decision(
                goal=goal,
                preset_id=preset_id,
                selected_template_ids=selected,
                preferred_template_ids=preferred_cluster_template_ids,
                source="preferred_template_ids",
            )
            return selected
        graph_template_ids = (
            plan_graph.get("cluster_template_ids", [])
            if isinstance(plan_graph, dict)
            else []
        )
        if graph_template_ids:
            if str(os.getenv("WORKFLOW_DYNAMIC_CLUSTER_ROUTING_ENABLED") or "").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
                "enabled",
            }:
                routed_template_ids = self._cluster_router().suggest_template_ids(goal=goal, preset_id=preset_id)
                merged_template_ids: list[str] = []
                for template_id in [*list(graph_template_ids), *routed_template_ids]:
                    if template_id not in merged_template_ids:
                        merged_template_ids.append(template_id)
                self._record_cluster_route_decision(
                    goal=goal,
                    preset_id=preset_id,
                    selected_template_ids=merged_template_ids,
                    preferred_template_ids=list(graph_template_ids),
                    source="plan_graph_dynamic_merge",
                )
                return merged_template_ids
            selected = self._cluster_router().suggest_template_ids(
                goal=goal,
                preset_id=preset_id,
                preferred_template_ids=list(graph_template_ids),
            )
            self._record_cluster_route_decision(
                goal=goal,
                preset_id=preset_id,
                selected_template_ids=selected,
                preferred_template_ids=list(graph_template_ids),
                source="plan_graph_preference",
            )
            return selected
        selected = self._cluster_router().suggest_template_ids(goal=goal, preset_id=preset_id)
        self._record_cluster_route_decision(
            goal=goal,
            preset_id=preset_id,
            selected_template_ids=selected,
            preferred_template_ids=[],
            source=source,
        )
        return selected

    def _record_cluster_route_decision(
        self,
        *,
        goal: str,
        preset_id: str | None,
        selected_template_ids: list[str],
        preferred_template_ids: list[str],
        source: str,
    ) -> None:
        if not selected_template_ids:
            return
        dynamic_enabled = str(os.getenv("WORKFLOW_DYNAMIC_CLUSTER_ROUTING_ENABLED") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
            "enabled",
        }
        self.cluster_route_decision_repo.create(
            ClusterRouteDecision(
                goal=goal,
                preset_id=preset_id,
                selected_template_ids=list(selected_template_ids),
                preferred_template_ids=list(preferred_template_ids),
                source=source,
                dynamic_enabled=dynamic_enabled,
            )
        )

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
        graphs: list[dict[str, Any]] = []
        for template in templates:
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
                role_goal_for=lambda parent_goal, role, cluster_template=template: self._cluster_member_goal(
                    parent_goal,
                    cluster_template.template_id,
                    next(
                        (
                            member.role_label
                            for member in cluster_template.member_specs
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
            ).model_dump(mode="json")
            graphs.append(graph)
        if len(graphs) == 1:
            return graphs[0]
        first = dict(graphs[0])
        first["cluster_template_ids"] = [template.template_id for template in templates]
        first["summary"] = (
            "Dynamic cluster preview graph for "
            + ", ".join(template.template_id for template in templates)
            + f" on `{selected_preset_id or first.get('preset_id')}`."
        )
        first["risk_summary"] = [
            f"dynamic cluster route includes `{template.template_id}` as a specialized lane"
            for template in templates
        ]
        first["nodes"] = [node for graph in graphs for node in graph.get("nodes", [])]
        first["edges"] = [edge for graph in graphs for edge in graph.get("edges", [])]
        first["barriers"] = [barrier for graph in graphs for barrier in graph.get("barriers", [])]
        first["retry_policies"] = [policy for graph in graphs for policy in graph.get("retry_policies", [])]
        first["cluster_graphs"] = [
            {
                "template_id": template.template_id,
                "graph": graph,
            }
            for template, graph in zip(templates, graphs, strict=False)
        ]
        return first

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

