from __future__ import annotations

import json
from typing import Callable

from packages.contracts import (
    AgentRoleType,
    BarrierSpec,
    EdgeSpec,
    OrchestrationGraphNode,
    OrchestrationPlan,
    OrchestrationPlanGraph,
    RetryPolicy,
)


class OrchestrationEngine:
    """Minimum graph orchestration substrate for the current M31 line."""

    def validate(self, graph: OrchestrationPlanGraph) -> OrchestrationPlanGraph:
        node_ids = [node.node_id for node in graph.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("orchestration graph contains duplicate node ids")
        node_id_set = set(node_ids)
        for edge in graph.edges:
            if edge.from_node_id not in node_id_set or edge.to_node_id not in node_id_set:
                raise ValueError("orchestration graph edge references an unknown node")
        for barrier in graph.barriers:
            if any(member_id not in node_id_set for member_id in barrier.member_node_ids):
                raise ValueError("orchestration graph barrier references an unknown node")
        for policy in graph.retry_policies:
            if any(target_id not in node_id_set for target_id in policy.target_node_ids):
                raise ValueError("orchestration graph retry policy references an unknown node")
        return graph

    def persist_payload(self, graph: OrchestrationPlanGraph) -> str:
        return json.dumps(self.validate(graph).model_dump(mode="json"), ensure_ascii=False)

    def build_single_path_graph(
        self,
        *,
        run_id: str | None,
        preset_id: str,
        goal: str,
        summary: str,
        node: OrchestrationGraphNode,
        risk_summary: list[str] | None = None,
        recommended_preset_id: str | None = None,
    ) -> OrchestrationPlanGraph:
        graph = OrchestrationPlanGraph(
            run_id=run_id,
            preset_id=preset_id,
            goal=goal,
            execution_mode="single_path",
            summary=summary,
            risk_summary=list(risk_summary or []),
            nodes=[node],
            retry_policies=[RetryPolicy(target_node_ids=[node.node_id], max_attempts=1)],
            recommended_preset_id=recommended_preset_id or preset_id,
        )
        return self.validate(graph)

    def build_graph_from_plan(
        self,
        *,
        run_id: str | None,
        preset_id: str,
        goal: str,
        plan: OrchestrationPlan,
        role_goal_for: Callable[[str, AgentRoleType], str],
        side_effect_level_for_adapter: Callable[[str | None], str],
        recommended_preset_id: str | None = None,
        summary: str | None = None,
        risk_summary: list[str] | None = None,
    ) -> OrchestrationPlanGraph:
        nodes: list[OrchestrationGraphNode] = []
        step_to_node_id: dict[str, str] = {}
        sequence_to_node_ids: dict[int, list[str]] = {}
        barrier_members: dict[str, list[str]] = {}

        for step in sorted(plan.steps, key=lambda item: (item.sequence_no, str(item.role), item.step_id)):
            dependency_ids = list(sequence_to_node_ids.get(step.sequence_no - 1, []))
            node = OrchestrationGraphNode(
                role=step.role,
                goal=role_goal_for(goal, step.role),
                agent_profile_id=step.agent_profile_id,
                cluster_template_id=step.cluster_template_id,
                cluster_member_id=step.cluster_member_id,
                role_label=step.role_label,
                required_capabilities=[step.preset_id, *([step.preferred_adapter] if step.preferred_adapter else [])],
                dependencies=dependency_ids,
                barrier_id=step.barrier_id,
                review_gate="advisory_review" if step.role == AgentRoleType.reviewer else "none",
                side_effect_level=side_effect_level_for_adapter(step.preferred_adapter),
                fallback_path=[adapter for adapter in (step.preferred_adapter, step.fallback_adapter) if adapter is not None],
                preset_id=step.preset_id,
                preferred_adapter=step.preferred_adapter,
                execution_profile=(
                    step.execution_profile.model_dump(mode="json") if step.execution_profile is not None else None
                ),
            )
            nodes.append(node)
            step_to_node_id[step.step_id] = node.node_id
            sequence_to_node_ids.setdefault(step.sequence_no, []).append(node.node_id)
            if step.barrier_id is not None:
                barrier_members.setdefault(step.barrier_id, []).append(node.node_id)

        barriers: list[BarrierSpec] = []
        for barrier in plan.barriers:
            barriers.append(
                BarrierSpec(
                    barrier_id=barrier.barrier_id,
                    label=barrier.label,
                    member_node_ids=list(barrier_members.get(barrier.barrier_id, [])),
                    release_condition="all_success",
                    status=barrier.status,
                )
            )

        edges: list[EdgeSpec] = []
        for node in nodes:
            for dependency_id in node.dependencies:
                edges.append(
                    EdgeSpec(
                        from_node_id=dependency_id,
                        to_node_id=node.node_id,
                        edge_type="depends_on",
                        description="sequence_dependency",
                    )
                )

        retry_policy = RetryPolicy(target_node_ids=[node.node_id for node in nodes], max_attempts=2)
        graph = OrchestrationPlanGraph(
            run_id=run_id,
            preset_id=preset_id,
            goal=goal,
            execution_mode="planner_generated_graph_with_parallel_children",
            summary=summary
            or "Planner decomposes the goal, child roles execute, and review closes the loop.",
            risk_summary=list(risk_summary or []),
            nodes=nodes,
            edges=edges,
            barriers=barriers,
            retry_policies=[retry_policy],
            recommended_preset_id=recommended_preset_id or preset_id,
            cluster_template_ids=list(plan.cluster_template_ids),
        )
        return self.validate(graph)
