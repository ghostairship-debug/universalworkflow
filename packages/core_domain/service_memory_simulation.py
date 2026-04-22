from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.contracts import (
    AgentRoleType,
    ExecutionLaneType,
    DomainPackDefinition,
    MemoryCandidate,
    MemoryItem,
    MemoryNamespace,
    MemoryRetrievalPreview,
    OrchestrationGraphNode,
    OrchestrationPlanGraph,
    ReviewPolicy,
    RunEvent,
    RunEventType,
    RunStatus,
    SimulationPolicyDefinition,
    SimulationRecord,
    SimulationRecordSource,
    SimulationReport,
    TaskKind,
)
from packages.core_domain.db import unit_of_work
from packages.core_domain.errors import EntityNotFoundError, PresetNotFoundError, WorkflowError
from packages.core_domain.m8_flags import is_mcp_source_enabled, is_skill_export_enabled
from packages.core_domain.memory import load_seed_memory_namespaces
from packages.core_domain.skills import export_domain_pack_skill_bundle


class MemorySimulationServiceMixin:
    def list_domain_packs(self) -> list[DomainPackDefinition]:
        return self.domain_pack_registry.list()

    def list_memory_namespaces(self) -> list[MemoryNamespace]:
        return load_seed_memory_namespaces()

    def list_memory_items(
        self,
        *,
        run_id: str | None = None,
        namespace_id: str | None = None,
    ) -> list[MemoryItem]:
        return self.memory_item_repo.list(run_id=run_id, namespace_id=namespace_id)

    def _memory_candidate_id(self, run_id: str, namespace_id: str) -> str:
        return f"memcand_{run_id}_{namespace_id}"

    def preview_domain_pack_resolution(
        self,
        preset_id: str,
        task_kind: TaskKind | str | None = None,
        adapter_name: str | None = None,
    ) -> dict[str, Any]:
        preset = self.preset_repo.get(preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {preset_id}")
        resolved_task_kind = self._resolve_task_kind(preset, task_kind)
        domain_pack = self._resolve_domain_pack(preset, resolved_task_kind)
        selected_adapter = adapter_name or self._default_adapter_for_preset(preset, resolved_task_kind, domain_pack)
        capability_route = self._resolve_capability_route(resolved_task_kind, requested_adapter=selected_adapter)
        return {
            "preset": preset.model_dump(mode="json"),
            "task_kind": str(resolved_task_kind),
            "domain_pack": domain_pack.model_dump(mode="json") if domain_pack is not None else None,
            "capability_resolution": capability_route.model_dump(mode="json") if capability_route is not None else None,
            "resolved": domain_pack is not None,
        }

    def validate_domain_pack_catalog(self) -> dict[str, Any]:
        return self.domain_pack_registry.validate_catalog(self.list_presets(), self.list_capability_routes())

    def list_capability_routes(self) -> list[dict[str, str]]:
        return self.worker_router.routes()

    def list_capability_sources(self) -> list[dict[str, Any]]:
        return self.capability_plane.list_capability_sources()

    def list_capability_descriptors(self) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in self.capability_plane.list_capability_descriptors(
                worker_pool_profiles=self.worker_pool_profiles,
                runtime_gateway_description=self.runtime_gateway.describe(),
                capability_routes=self.list_capability_routes(),
                default_worker_pool_id=self.effective_config["worker_pools"]["default_pool_id"],
            )
        ]

    def list_capability_health(self) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in self.capability_plane.list_capability_health(
                worker_pool_profiles=self.worker_pool_profiles,
                runtime_gateway_description=self.runtime_gateway.describe(),
                capability_routes=self.list_capability_routes(),
                default_worker_pool_id=self.effective_config["worker_pools"]["default_pool_id"],
            )
        ]

    def list_mcp_server_profiles(self) -> list[dict[str, Any]]:
        return [profile.model_dump(mode="json") for profile in self.capability_plane.list_mcp_profiles()]

    def preview_tool_projection(
        self,
        *,
        preset_id: str,
        task_kind: TaskKind | str | None = None,
        adapter_name: str | None = None,
    ) -> dict[str, Any]:
        preset = self.preset_repo.get(preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {preset_id}")
        resolved_task_kind = self._resolve_task_kind(preset, task_kind)
        domain_pack = self._resolve_domain_pack(preset, resolved_task_kind)
        selected_adapter = adapter_name or self._default_adapter_for_preset(preset, resolved_task_kind, domain_pack)
        capability_route = self._resolve_capability_route(resolved_task_kind, requested_adapter=selected_adapter)
        lane_type = self._resolve_execution_lane(
            preset=preset,
            task_kind=resolved_task_kind,
            selected_adapter=capability_route.adapter_name if capability_route is not None else selected_adapter,
        )
        manifest, profiles = self.capability_plane.build_projection_manifest(
            run_id=None,
            preset_id=preset.preset_id,
            task_kind=resolved_task_kind,
            review_policy=ReviewPolicy(preset.default_review_policy),
            lane_type=lane_type,
            domain_pack_id=domain_pack.domain_pack_id if domain_pack is not None else None,
            include_mcp=lane_type != ExecutionLaneType.native_deterministic and is_mcp_source_enabled(),
        )
        return {
            "preset": preset.model_dump(mode="json"),
            "task_kind": str(resolved_task_kind),
            "execution_lane": str(lane_type),
            "capability_resolution": capability_route.model_dump(mode="json") if capability_route is not None else None,
            "tool_projection_manifest": manifest.model_dump(mode="json"),
            "mcp_server_profiles": [profile.model_dump(mode="json") for profile in profiles],
        }

    def _primary_role_for_preset(self, preset_id: str) -> AgentRoleType:
        mapping = {
            "feature_delivery": AgentRoleType.coder,
            "research_spike": AgentRoleType.researcher,
            "research_spike_reviewable": AgentRoleType.researcher,
            "optional_delivery": AgentRoleType.planner,
            "advisory_delivery": AgentRoleType.reviewer,
            "guarded_delivery": AgentRoleType.operator,
            "guarded_project_delivery": AgentRoleType.operator,
            "project_delivery": AgentRoleType.operator,
        }
        return mapping.get(preset_id, AgentRoleType.operator)

    def _review_gate_for_policy(self, review_policy: ReviewPolicy | str) -> str:
        normalized = str(review_policy)
        if normalized == str(ReviewPolicy.mandatory):
            return "mandatory_human_review"
        if normalized == str(ReviewPolicy.human_required):
            return "human_review_required"
        if normalized == str(ReviewPolicy.recommended):
            return "recommended_review"
        if normalized == str(ReviewPolicy.optional):
            return "advisory_review"
        return "none"

    def _side_effect_level_for_adapter(self, adapter_name: str | None) -> str:
        if adapter_name == "opencode":
            return "repo_mutation_controlled"
        if adapter_name in {"agent", "opencode_session"}:
            return "session_read_write"
        return "artifact_only"

    def _build_orchestration_plan_graph(
        self,
        *,
        goal: str,
        preset_id: str,
        run_id: str | None = None,
        recommended_preset_id: str | None = None,
        adapter_name: str | None = None,
        task_kind: TaskKind | str | None = None,
    ) -> OrchestrationPlanGraph:
        if preset_id in {"project_delivery", "guarded_project_delivery"}:
            plan = self._default_orchestration_plan_for_preset(preset_id, run_id or "preview_run")
            if plan is None:
                raise WorkflowError("orchestration plan was not available", {"preset_id": preset_id})
            summary = (
                "Planner decomposes the goal, coder and researcher run in parallel, reviewer closes the loop."
                if preset_id == "project_delivery"
                else "Planner decomposes the goal, coder and researcher run in parallel, and guarded review enforces mandatory sign-off."
            )
            risk_summary = [
                "parallel child runs require barrier release before review",
                "repo mutation stays isolated to the coder lane",
                "human intervention may still be required when review policy escalates",
            ]
            if preset_id == "guarded_project_delivery":
                risk_summary.append("guarded review keeps the orchestration on the human-signoff path")
            return self.orchestration_engine.build_graph_from_plan(
                run_id=run_id,
                preset_id=preset_id,
                goal=goal,
                plan=plan,
                role_goal_for=lambda parent_goal, role: self._role_goal_for(parent_goal, role),
                side_effect_level_for_adapter=self._side_effect_level_for_adapter,
                recommended_preset_id=recommended_preset_id or preset_id,
                summary=summary,
                risk_summary=risk_summary,
            )

        preset = self.preset_repo.get(preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {preset_id}")
        resolved_task_kind = self._resolve_task_kind(preset, task_kind)
        domain_pack = self._resolve_domain_pack(preset, resolved_task_kind)
        selected_adapter = adapter_name or self._default_adapter_for_preset(preset, resolved_task_kind, domain_pack)
        capability_route = self._resolve_capability_route(resolved_task_kind, requested_adapter=selected_adapter)
        lane_type = self._resolve_execution_lane(
            preset=preset,
            task_kind=resolved_task_kind,
            selected_adapter=capability_route.adapter_name if capability_route is not None else selected_adapter,
        )
        adapter_name = capability_route.adapter_name if capability_route is not None else None
        node = OrchestrationGraphNode(
            role=self._primary_role_for_preset(preset_id),
            goal=goal,
            required_capabilities=[
                str(resolved_task_kind),
                str(lane_type),
                *( [adapter_name] if adapter_name is not None else [] ),
            ],
            review_gate=self._review_gate_for_policy(preset.default_review_policy),
            side_effect_level=self._side_effect_level_for_adapter(adapter_name),
            fallback_path=[item for item in [adapter_name] if item is not None],
            preset_id=preset_id,
            preferred_adapter=adapter_name,
        )
        risk_summary: list[str] = []
        if str(preset.default_review_policy) != str(ReviewPolicy.auto_only):
            risk_summary.append(f"review policy `{preset.default_review_policy}` may insert a human approval step")
        if lane_type == ExecutionLaneType.sessionful_external_agent:
            risk_summary.append("sessionful external lane must stay outside default repo mutation flow")
        return self.orchestration_engine.build_single_path_graph(
            run_id=run_id,
            preset_id=preset_id,
            goal=goal,
            summary=f"Single-path execution through `{preset_id}` with `{resolved_task_kind}`.",
            node=node,
            risk_summary=risk_summary,
            recommended_preset_id=recommended_preset_id or preset_id,
        )

    def preview_orchestration_plan_graph(
        self,
        *,
        goal: str,
        preset_id: str | None = None,
        preferred_cluster_template_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        suggestions = [item.model_dump(mode="json") for item in self.suggest_presets(goal)]
        selected_preset_id = preset_id or (suggestions[0]["preset_id"] if suggestions else "feature_delivery")
        graph = self._build_orchestration_plan_graph(
            goal=goal,
            preset_id=selected_preset_id,
            recommended_preset_id=suggestions[0]["preset_id"] if suggestions else selected_preset_id,
        )
        graph.cluster_template_ids = self._selected_cluster_template_ids(
            goal=goal,
            preset_id=selected_preset_id,
            preferred_cluster_template_ids=preferred_cluster_template_ids,
            plan_graph=graph.model_dump(mode="json"),
        )
        return {
            "goal": goal,
            "selected_preset_id": selected_preset_id,
            "suggestions": suggestions,
            "plan_graph": graph.model_dump(mode="json"),
        }

    def launch_goal(
        self,
        *,
        goal: str,
        preset_id: str | None = None,
        preferred_cluster_template_ids: list[str] | None = None,
        execute: bool = False,
    ) -> dict[str, Any]:
        preview = self.preview_orchestration_plan_graph(
            goal=goal,
            preset_id=preset_id,
            preferred_cluster_template_ids=preferred_cluster_template_ids,
        )
        policy_preview = self.preview_capability_policy(
            goal=goal,
            preset_id=preset_id,
            preferred_cluster_template_ids=preferred_cluster_template_ids,
        )
        goal_packet = self.preview_goal_packet(
            goal=goal,
            preset_id=preset_id,
            preferred_cluster_template_ids=preferred_cluster_template_ids,
        )
        selected_preset_id = str(preview["selected_preset_id"])
        run = self.create_run(goal=goal, preset_id=selected_preset_id)
        prepared = self.compile_run(run.run_id)
        payload = {
            "goal": goal,
            "selected_preset_id": selected_preset_id,
            "plan_graph": preview["plan_graph"],
            "capability_policy_preview": policy_preview["policy_preview"],
            "selected_clusters": goal_packet["selected_clusters"],
            "cluster_graph": goal_packet["cluster_graph"],
            "cluster_policy_preview": goal_packet["cluster_policy_preview"],
            "goal_packet": goal_packet,
            "suggestions": preview["suggestions"],
            "run": prepared.run.model_dump(mode="json"),
            "runtime_task_id": prepared.task_packet.runtime_task_id,
            "handoff_id": prepared.handoff.handoff_id,
            "state_ref_id": prepared.state_ref.state_ref_id,
            "execution_lane": str(prepared.execution_lane),
            "capability_adapter": (
                prepared.capability_route.adapter_name if prepared.capability_route is not None else None
            ),
        }
        if execute:
            executed = self.resume_run(run.run_id)
            payload["run"] = executed.run.model_dump(mode="json")
            payload["evidence_id"] = executed.evidence.evidence_id
            payload["review_decision"] = (
                executed.review_verdict.decision if executed.review_verdict is not None else None
            )
        return payload

    def _descriptor_matches_graph_node(self, descriptor: dict[str, Any], node: dict[str, Any]) -> bool:
        adapter_name = descriptor.get("adapter_name")
        preferred_adapter = node.get("preferred_adapter")
        if adapter_name and preferred_adapter and adapter_name == preferred_adapter:
            return True
        descriptor_scopes = {str(item) for item in descriptor.get("scopes", [])}
        if descriptor_scopes & {str(item) for item in node.get("required_capabilities", [])}:
            return True
        descriptor_task_kinds = {str(item) for item in descriptor.get("allowed_task_kinds", [])}
        if descriptor_task_kinds & {str(item) for item in node.get("required_capabilities", [])}:
            return True
        return False

    def _recommended_operator_mode(self, node_policies: list[dict[str, Any]], execution_mode: str) -> str:
        if any(item["review_gate"] not in {"none", None} for item in node_policies):
            return "human_visible"
        if any(item["side_effect_level"] in {"repo_mutation_controlled", "session_read_write"} for item in node_policies):
            return "human_visible"
        if execution_mode != "single_path":
            return "operator_observe"
        return "auto_ok"

    def _capability_policy_preview_for_plan_graph(self, plan_graph: dict[str, Any]) -> dict[str, Any]:
        descriptors = self.list_capability_descriptors()
        node_policies: list[dict[str, Any]] = []
        for node in plan_graph.get("nodes", []):
            matched = [item for item in descriptors if self._descriptor_matches_graph_node(item, node)]
            node_policies.append(
                {
                    "node_id": node.get("node_id"),
                    "role": node.get("role"),
                    "goal": node.get("goal"),
                    "review_gate": node.get("review_gate"),
                    "side_effect_level": node.get("side_effect_level"),
                    "required_capabilities": list(node.get("required_capabilities", [])),
                    "matched_descriptor_ids": [item["capability_id"] for item in matched],
                    "matched_provider_kinds": sorted({str(item["provider_kind"]) for item in matched}),
                    "descriptor_coverage_count": len(matched),
                }
            )
        sessionful_nodes = [item for item in node_policies if item["side_effect_level"] == "session_read_write"]
        repo_mutation_nodes = [item for item in node_policies if item["side_effect_level"] == "repo_mutation_controlled"]
        review_nodes = [item for item in node_policies if item["review_gate"] not in {"none", None}]
        execution_mode = str(plan_graph.get("execution_mode") or "single_path")
        return {
            "policy_version": "m26_phase_0_v1",
            "selected_preset_id": plan_graph.get("preset_id"),
            "execution_mode": execution_mode,
            "recommended_operator_mode": self._recommended_operator_mode(node_policies, execution_mode),
            "requires_human_checkpoint": bool(review_nodes),
            "sessionful_node_count": len(sessionful_nodes),
            "repo_mutation_node_count": len(repo_mutation_nodes),
            "review_node_count": len(review_nodes),
            "node_policies": node_policies,
        }

    def preview_capability_policy(
        self,
        *,
        goal: str,
        preset_id: str | None = None,
        preferred_cluster_template_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        preview = self.preview_orchestration_plan_graph(
            goal=goal,
            preset_id=preset_id,
            preferred_cluster_template_ids=preferred_cluster_template_ids,
        )
        return {
            "goal": goal,
            "selected_preset_id": preview["selected_preset_id"],
            "suggestions": preview["suggestions"],
            "plan_graph": preview["plan_graph"],
            "policy_preview": self._capability_policy_preview_for_plan_graph(preview["plan_graph"]),
        }

    def preview_goal_packet(
        self,
        *,
        goal: str,
        preset_id: str | None = None,
        preferred_cluster_template_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        policy_preview = self.preview_capability_policy(
            goal=goal,
            preset_id=preset_id,
            preferred_cluster_template_ids=preferred_cluster_template_ids,
        )
        capability_descriptors = self.list_capability_descriptors()
        capability_health = self.list_capability_health()
        matched_descriptor_ids = {
            descriptor_id
            for node in policy_preview["policy_preview"]["node_policies"]
            for descriptor_id in node.get("matched_descriptor_ids", [])
        }
        cluster_bundle = self._cluster_preview_bundle(
            goal=goal,
            selected_preset_id=policy_preview["selected_preset_id"],
            plan_graph=policy_preview["plan_graph"],
            preferred_cluster_template_ids=preferred_cluster_template_ids,
        )
        return {
            "goal": goal,
            "selected_preset_id": policy_preview["selected_preset_id"],
            "suggestions": policy_preview["suggestions"],
            "plan_graph": policy_preview["plan_graph"],
            "capability_policy_preview": policy_preview["policy_preview"],
            "selected_clusters": [
                template.model_dump(mode="json") for template in cluster_bundle["selected_clusters"]
            ],
            "cluster_graph": cluster_bundle["cluster_graph"],
            "cluster_policy_preview": cluster_bundle["cluster_policy_preview"],
            "cluster_execution_plans": [
                plan.model_dump(mode="json") for plan in cluster_bundle["cluster_execution_plans"]
            ],
            "matched_capability_descriptors": [
                item for item in capability_descriptors if item["capability_id"] in matched_descriptor_ids
            ],
            "matched_capability_health": [
                item
                for item in capability_health
                if isinstance(item.get("descriptor"), dict)
                and item["descriptor"]["capability_id"] in matched_descriptor_ids
            ],
        }

    def get_run_capability_policy_preview(self, run_id: str) -> dict[str, Any]:
        plan_graph_payload = self.get_run_orchestration_plan_graph(run_id)
        if not plan_graph_payload["enabled"] or plan_graph_payload["plan_graph"] is None:
            return {"run_id": run_id, "enabled": False, "policy_preview": None}
        return {
            "run_id": run_id,
            "enabled": True,
            "plan_graph": plan_graph_payload["plan_graph"],
            "policy_preview": self._capability_policy_preview_for_plan_graph(plan_graph_payload["plan_graph"]),
        }

    def runtime_gateway_status(self) -> dict[str, Any]:
        return self.runtime_gateway.describe()

    def list_simulation_policies(self) -> list[SimulationPolicyDefinition]:
        return self.simulation_policy_registry.list()

    def get_run_memory_candidates(self, run_id: str) -> list[MemoryCandidate]:
        detail = self.get_status_detail(run_id)
        summary = self.get_run_summary(run_id)
        inspection = self.inspect_run_state(run_id)
        audit_report = self.get_run_audit_report(run_id)
        timeline = self.get_timeline(run_id)
        runtime_task_ids = detail.get("runtime_task_ids", [])
        latest_review = detail.get("latest_review_verdict")
        domain_pack = detail.get("domain_pack")
        namespaces = {item.namespace_id: item for item in self.list_memory_namespaces()}

        candidates: list[MemoryCandidate] = []
        if "repo" in namespaces:
            candidates.append(
                MemoryCandidate(
                    candidate_id=self._memory_candidate_id(run_id, "repo"),
                    run_id=run_id,
                    namespace_id="repo",
                    title=f"Run summary for {detail['run']['preset_id']}",
                    summary=summary["headline"],
                    tags=[
                        detail["run"]["status"],
                        detail["review_policy"],
                        domain_pack["domain_pack_id"] if domain_pack is not None else "no_domain_pack",
                    ],
                    source_refs=[
                        f"run:{run_id}",
                        *[f"task:{task_id}" for task_id in runtime_task_ids],
                    ],
                )
            )
        if "policy" in namespaces:
            candidates.append(
                MemoryCandidate(
                    candidate_id=self._memory_candidate_id(run_id, "policy"),
                    run_id=run_id,
                    namespace_id="policy",
                    title=f"Review policy outcome for {run_id}",
                    summary=(
                        f"Policy `{detail['review_policy']}` ended in "
                        f"`{detail['effective_review_state']}` with next action `{detail['next_action']}`."
                    ),
                    tags=[detail["review_policy"], detail["effective_review_state"]],
                    source_refs=[
                        f"run:{run_id}",
                        *( [f"verdict:{latest_review['verdict_id']}"] if latest_review is not None else [] ),
                    ],
                )
            )
        failure_category = summary["failure_taxonomy"]["category"]
        if failure_category != "success" and "failure" in namespaces:
            candidates.append(
                MemoryCandidate(
                    candidate_id=self._memory_candidate_id(run_id, "failure"),
                    run_id=run_id,
                    namespace_id="failure",
                    title=f"Failure memory candidate for {run_id}",
                    summary=(
                        f"Failure category `{failure_category}` with closure state "
                        f"`{audit_report['review_packet']['closure_summary']['state']}`."
                    ),
                    tags=[
                        failure_category,
                        detail["run"]["status"],
                        detail["failure_reason"] or "no_failure_reason",
                    ],
                    source_refs=[f"run:{run_id}", "audit:run_audit_report"],
                )
            )
        if detail["run"]["status"] == RunStatus.completed and "release" in namespaces:
            candidates.append(
                MemoryCandidate(
                    candidate_id=self._memory_candidate_id(run_id, "release"),
                    run_id=run_id,
                    namespace_id="release",
                    title=f"Release-ready candidate for {run_id}",
                    summary=(
                        f"Completed run with review state `{detail['effective_review_state']}` and "
                        f"{inspection['problem_count']} inspection problems."
                    ),
                    tags=[
                        "completed",
                        detail["effective_review_state"],
                        domain_pack["domain_pack_id"] if domain_pack is not None else "generic",
                    ],
                    source_refs=[
                        f"run:{run_id}",
                        *( [f"event:{event.event_id}" for event in timeline[-3:]] ),
                    ],
                )
            )
        return candidates

    def materialize_run_memory_candidate(self, run_id: str, candidate_id: str) -> MemoryItem:
        candidates = self.get_run_memory_candidates(run_id)
        selected_candidate = next((item for item in candidates if item.candidate_id == candidate_id), None)
        if selected_candidate is None:
            raise EntityNotFoundError("memory_candidate", candidate_id)

        existing_item = self.memory_item_repo.get_by_source_candidate(candidate_id)
        if existing_item is not None:
            return existing_item

        with unit_of_work(self.db_path) as connection:
            memory_item = MemoryItem(
                run_id=run_id,
                namespace_id=selected_candidate.namespace_id,
                source_candidate_id=selected_candidate.candidate_id,
                title=selected_candidate.title,
                summary=selected_candidate.summary,
                tags=selected_candidate.tags,
                source_refs=selected_candidate.source_refs,
            )
            self.memory_item_repo.create(memory_item, connection=connection)
            self.event_repo.append(
                RunEvent(
                    run_id=run_id,
                    event_type=RunEventType.memory_item_materialized,
                    object_type="memory_item",
                    object_id=memory_item.memory_item_id,
                    summary=f"Memory item materialized in namespace `{memory_item.namespace_id}`",
                    payload_json={
                        "run_id": run_id,
                        "memory_item_id": memory_item.memory_item_id,
                        "namespace_id": memory_item.namespace_id,
                        "source_candidate_id": memory_item.source_candidate_id,
                    },
                ),
                connection=connection,
            )
        return memory_item

    def preview_memory_retrieval(
        self,
        *,
        preset_id: str | None = None,
        run_id: str | None = None,
        namespace_id: str | None = None,
        memory_item_ids: list[str] | None = None,
        limit: int = 5,
    ) -> MemoryRetrievalPreview:
        if run_id is not None:
            self.get_run(run_id)
        if preset_id is not None and self.preset_repo.get(preset_id) is None:
            raise PresetNotFoundError(f"preset not found: {preset_id}")

        items = self.list_memory_items(run_id=run_id, namespace_id=namespace_id)

        if preset_id is not None:
            items = [
                item
                for item in items
                if (origin_run := self.run_repo.get(item.run_id)) is not None and origin_run.preset_id == preset_id
            ]

        items = sorted(items, key=lambda item: (item.created_at, item.memory_item_id), reverse=True)

        if memory_item_ids:
            item_by_id = {item.memory_item_id: item for item in items}
            missing_item_ids = [item_id for item_id in memory_item_ids if item_id not in item_by_id]
            if missing_item_ids:
                raise EntityNotFoundError("memory_item", ",".join(missing_item_ids))
            selected_items = [item_by_id[item_id] for item_id in memory_item_ids]
        else:
            selected_items = items[:limit]

        namespace_ids = list(dict.fromkeys(item.namespace_id for item in selected_items))
        source_run_ids = list(dict.fromkeys(item.run_id for item in selected_items))
        brief_lines = [f"[{item.namespace_id}] {item.title}: {item.summary}" for item in selected_items]

        return MemoryRetrievalPreview(
            run_id=run_id,
            preset_id=preset_id,
            namespace_ids=namespace_ids,
            selected_memory_item_ids=[item.memory_item_id for item in selected_items],
            source_run_ids=source_run_ids,
            item_count=len(selected_items),
            brief_lines=brief_lines,
            items=selected_items,
        )

    def get_run_simulation(self, run_id: str) -> SimulationReport:
        detail = self.get_status_detail(run_id)
        inspection = self.inspect_run_state(run_id)
        return self._simulation_report_for(detail, inspection)

    def _persist_simulation_record(
        self,
        run_id: str,
        report: SimulationReport,
        *,
        recorded_from: SimulationRecordSource,
        connection,
    ) -> SimulationRecord:
        record = SimulationRecord(
            run_id=run_id,
            policy_id=report.policy_id,
            status=report.status,
            triggered=report.triggered,
            summary=report.summary,
            recorded_from=recorded_from,
            report=report,
        )
        self.simulation_record_repo.create(record, connection=connection)
        self.event_repo.append(
            RunEvent(
                run_id=run_id,
                event_type=RunEventType.simulation_recorded,
                object_type="simulation_record",
                object_id=record.record_id,
                summary=f"Simulation record persisted ({record.recorded_from})",
                payload_json={
                    "run_id": run_id,
                    "record_id": record.record_id,
                    "policy_id": record.policy_id,
                    "status": record.status,
                    "triggered": record.triggered,
                    "recorded_from": record.recorded_from,
                },
            ),
            connection=connection,
        )
        return record

    def _record_lifecycle_simulation_if_triggered(
        self,
        run_id: str,
        recorded_from: SimulationRecordSource,
    ) -> SimulationRecord | None:
        self.get_run(run_id)
        report = self.get_run_simulation(run_id)
        if not report.triggered:
            return None
        with unit_of_work(self.db_path) as connection:
            return self._persist_simulation_record(
                run_id,
                report,
                recorded_from=recorded_from,
                connection=connection,
            )

    def record_run_simulation(
        self,
        run_id: str,
        recorded_from: SimulationRecordSource = SimulationRecordSource.manual_request,
    ) -> SimulationRecord:
        self.get_run(run_id)
        report = self.get_run_simulation(run_id)
        with unit_of_work(self.db_path) as connection:
            return self._persist_simulation_record(
                run_id,
                report,
                recorded_from=recorded_from,
                connection=connection,
            )

    def list_simulation_records(self, run_id: str) -> list[SimulationRecord]:
        self.get_run(run_id)
        return self.simulation_record_repo.list_for_run(run_id)

    def export_domain_pack_skill(
        self,
        domain_pack_id: str,
        *,
        output_root: str | Path = "state/skills",
    ) -> dict[str, Any]:
        if not is_skill_export_enabled():
            raise WorkflowError(
                "skill export is disabled; enable UAWO_ENABLE_SKILL_EXPORT to use this path",
                {"domain_pack_id": domain_pack_id},
            )
        domain_pack = self.domain_pack_registry.get(domain_pack_id)
        if domain_pack is None:
            raise EntityNotFoundError("domain_pack", domain_pack_id)
        bundle_path = export_domain_pack_skill_bundle(domain_pack, output_root=output_root)
        return {
            "domain_pack_id": domain_pack_id,
            "bundle_path": bundle_path.as_posix(),
            "exported": True,
        }
