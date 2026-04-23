from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from packages.contracts import (
    AgentRoleType,
    ExecutionClusterTemplate,
    MutationContract,
    MutationMode,
    OrchestrationBarrier,
    OrchestrationPlan,
    OrchestrationStep,
    ReviewPolicy,
    RoleAssignment,
    RunStatus,
    TaskPacket,
)
from packages.core_domain.cluster_router import ClusterRouter
from packages.core_domain.errors import (
    CapabilityAdapterNotFoundError,
    ExecutionLaneNotAllowedError,
    TaskKindNotAllowedError,
    UnsupportedTaskKindError,
)
from packages.core_domain.interaction_catalog import (
    cluster_template_ids_for_preset,
    default_preset_id_for_cluster_template,
    fallback_adapter_for_cluster_member,
    list_default_cluster_templates,
    member_preset_id,
    preferred_adapter_for_cluster_member,
    sequence_no_for_cluster_member,
)
from packages.core_domain.service_types import PreparedRunBundle
from packages.worker_adapters.base import ExecutionResult, utc_now

if TYPE_CHECKING:
    from packages.core_domain.services import OrchestratorService


class OrchestrationExecutionService:
    """Shared orchestration-plan construction and execution service."""

    SUPPORTED_PRESET_DEFAULTS = {"project_delivery", "guarded_project_delivery"}

    def __init__(self, facade: "OrchestratorService") -> None:
        self._facade = facade
        self._cluster_router = ClusterRouter(list_default_cluster_templates())

    def _template_for_preset(self, preset_id: str) -> ExecutionClusterTemplate | None:
        if preset_id not in self.SUPPORTED_PRESET_DEFAULTS:
            return None
        template_ids = cluster_template_ids_for_preset(preset_id)
        if not template_ids:
            return None
        return self._cluster_router.get_template(template_ids[0])

    def _plan_review_policy(
        self,
        template: ExecutionClusterTemplate,
        selected_preset_id: str | None,
    ) -> ReviewPolicy:
        if template.template_id == "dev_cluster" and selected_preset_id == "guarded_project_delivery":
            return ReviewPolicy.mandatory
        return template.default_review_policy

    def _member_preset_id(
        self,
        template: ExecutionClusterTemplate,
        member_role_label: str,
        public_role: AgentRoleType,
        selected_preset_id: str | None,
    ) -> str:
        if template.template_id == "dev_cluster" and selected_preset_id == "guarded_project_delivery":
            if member_role_label == "quality_gate":
                return "guarded_delivery"
        return member_preset_id(template.template_id, member_role_label, public_role)

    def build_cluster_orchestration_plan(
        self,
        *,
        template: ExecutionClusterTemplate,
        selected_preset_id: str | None = None,
        run_id: str | None = None,
        include_operator_step: bool = False,
    ) -> OrchestrationPlan:
        selected_preset = selected_preset_id or default_preset_id_for_cluster_template(template.template_id) or template.template_id
        review_policy = self._plan_review_policy(template, selected_preset_id)

        barriers: list[OrchestrationBarrier] = []
        barrier_id_by_group: dict[str, str] = {}
        for member in template.member_specs:
            if member.parallel_group and member.parallel_group not in barrier_id_by_group:
                grouped = [item for item in template.member_specs if item.parallel_group == member.parallel_group]
                executable_grouped = [item for item in grouped if include_operator_step or item.public_role != AgentRoleType.operator]
                if len(executable_grouped) > 1:
                    barrier = OrchestrationBarrier(
                        barrier_id=f"{template.template_id}_{member.parallel_group}",
                        label=member.parallel_group,
                        role_ids=[item.public_role for item in executable_grouped],
                        status="pending",
                        member_count=len(executable_grouped),
                    )
                    barriers.append(barrier)
                    barrier_id_by_group[member.parallel_group] = barrier.barrier_id

        roles: list[RoleAssignment] = []
        steps: list[OrchestrationStep] = []
        for member in template.member_specs:
            preset_id = self._member_preset_id(
                template,
                member.role_label,
                member.public_role,
                selected_preset_id,
            )
            preset = self._facade.preset_repo.get(preset_id)
            if preset is None:
                raise ValueError(f"preset `{preset_id}` is not available for orchestration member `{member.member_id}`")
            resolved_execution = self._facade._resolve_execution_profile_for_run(
                preset=preset,
                task_kind=preset.allowed_task_kinds[0],
                domain_pack=self._facade._resolve_domain_pack(preset, preset.allowed_task_kinds[0]),
                agent_profile_id=member.agent_profile_id,
                cluster_template_id=template.template_id,
                cluster_member_id=member.member_id,
                public_role=member.public_role,
                role_label=member.role_label,
            )
            execution_profile_payload = resolved_execution.model_dump(mode="json")
            preferred_adapter = resolved_execution.adapter_name or preferred_adapter_for_cluster_member(member.public_role)
            fallback_adapter = fallback_adapter_for_cluster_member(member.public_role)
            roles.append(
                RoleAssignment(
                    role=member.public_role,
                    preset_id=preset_id,
                    agent_profile_id=member.agent_profile_id,
                    cluster_template_id=template.template_id,
                    cluster_member_id=member.member_id,
                    role_label=member.role_label,
                    preferred_adapter=preferred_adapter,
                    fallback_adapter=fallback_adapter,
                    review_policy=review_policy,
                    execution_profile=execution_profile_payload,
                )
            )
            if member.public_role == AgentRoleType.operator and not include_operator_step:
                continue
            steps.append(
                OrchestrationStep(
                    step_id=f"{template.template_id}_{member.member_id}",
                    role=member.public_role,
                    title=f"{member.role_label.replace('_', ' ').title()} lane",
                    run_id=None,
                    preset_id=preset_id,
                    agent_profile_id=member.agent_profile_id,
                    cluster_template_id=template.template_id,
                    cluster_member_id=member.member_id,
                    role_label=member.role_label,
                    preferred_adapter=preferred_adapter,
                    fallback_adapter=fallback_adapter,
                    barrier_id=barrier_id_by_group.get(member.parallel_group or ""),
                    sequence_no=sequence_no_for_cluster_member(
                        template.template_id,
                        member.role_label,
                        member.public_role,
                    ),
                    status="pending",
                    execution_profile=execution_profile_payload,
                )
            )

        return OrchestrationPlan(
            orchestration_id=f"{template.template_id}_{run_id or selected_preset}_orchestration",
            run_id=run_id,
            preset_id=selected_preset,
            review_policy=review_policy,
            cluster_template_ids=[template.template_id],
            roles=roles,
            steps=steps,
            barriers=barriers,
            execution_mode=f"cluster_{template.execution_mode}",
        )

    def default_orchestration_plan_for_preset(
        self,
        preset_id: str,
        run_id: str,
    ) -> OrchestrationPlan | None:
        template = self._template_for_preset(preset_id)
        if template is None:
            return None
        return self.build_cluster_orchestration_plan(
            template=template,
            selected_preset_id=preset_id,
            run_id=run_id,
            include_operator_step=False,
        )

    def compile_child_run_with_fallback(
        self,
        run_id: str,
        *,
        preferred_adapter: str | None,
        fallback_adapter: str | None,
        mutation_contract: MutationContract | None = None,
        execution_profile: ExecutionProfileDefinition | None = None,
        agent_profile_id: str | None = None,
        cluster_template_id: str | None = None,
        cluster_member_id: str | None = None,
        public_role: str | None = None,
        role_label: str | None = None,
    ) -> PreparedRunBundle:
        adapter_candidates = [preferred_adapter, fallback_adapter, None]
        seen: set[str | None] = set()
        for adapter_name in adapter_candidates:
            if adapter_name in seen:
                continue
            seen.add(adapter_name)
            try:
                return self._facade.compile_run(
                    run_id,
                    adapter_name=adapter_name,
                    task_card_ref=mutation_contract.task_card_ref if mutation_contract is not None else None,
                    task_card_path=mutation_contract.task_card_path if mutation_contract is not None else None,
                    write_set=mutation_contract.write_set if mutation_contract is not None else None,
                    read_set=mutation_contract.read_set if mutation_contract is not None else None,
                    test_commands=mutation_contract.test_commands if mutation_contract is not None else None,
                    max_fix_iterations=mutation_contract.max_fix_iterations if mutation_contract is not None else 0,
                    mutation_mode=mutation_contract.mutation_mode if mutation_contract is not None else None,
                    agent_profile_id=agent_profile_id,
                    cluster_template_id=cluster_template_id,
                    cluster_member_id=cluster_member_id,
                    public_role=public_role,
                    role_label=role_label,
                )
            except (
                CapabilityAdapterNotFoundError,
                ExecutionLaneNotAllowedError,
                TaskKindNotAllowedError,
                UnsupportedTaskKindError,
            ):
                continue
        return self._facade.compile_run(
            run_id,
            agent_profile_id=agent_profile_id,
            cluster_template_id=cluster_template_id,
            cluster_member_id=cluster_member_id,
            public_role=public_role,
            role_label=role_label,
        )

    def finalize_child_run_if_waiting(self, run_id: str):
        run = self._facade.get_run(run_id)
        if str(run.status) != RunStatus.awaiting_review:
            return run
        return self._facade.approve_run_review(run_id).run

    def _goal_for_step(
        self,
        parent_goal: str,
        step: OrchestrationStep,
        *,
        prior_run_ids: list[str] | None = None,
    ) -> str:
        role_label = step.role_label or ""
        child_line = ", ".join(prior_run_ids or [])
        role_map = {
            "architect": f"Design the work breakdown and integration handoffs for: {parent_goal}",
            "implementer": f"Implement the primary delivery slice for: {parent_goal}",
            "risk_mapper": f"Research risks, supporting evidence, and open questions for: {parent_goal}",
            "quality_gate": (
                f"Review orchestration evidence for this project goal: {parent_goal}. Parallel child runs: {child_line}"
                if child_line
                else f"Review the implementation and supporting evidence for: {parent_goal}"
            ),
            "launch_guard": f"Prepare the operator-facing launch and follow-up checkpoint for: {parent_goal}",
            "research_analyst": f"Investigate and summarize findings for: {parent_goal}",
            "citation_checker": (
                f"Verify citations, claims, confidence posture, and the prior run evidence for: {parent_goal}. Prior child runs: {child_line}"
                if child_line
                else f"Verify citations, claims, and confidence posture for: {parent_goal}"
            ),
        }
        if role_label in role_map:
            return role_map[role_label]
        if step.role == AgentRoleType.planner:
            return f"Plan the work for: {parent_goal}"
        if step.role == AgentRoleType.coder:
            return f"Implement the requested change for: {parent_goal}"
        if step.role == AgentRoleType.researcher:
            return f"Research and summarize evidence for: {parent_goal}"
        if step.role == AgentRoleType.reviewer:
            return (
                f"Review orchestration evidence for this project goal: {parent_goal}. Parallel child runs: {child_line}"
                if child_line
                else f"Review the output for: {parent_goal}"
            )
        return f"Keep operator control visible for: {parent_goal}"

    def write_orchestration_artifact(
        self,
        packet: TaskPacket,
        content: str,
        *,
        plan: OrchestrationPlan | None = None,
    ) -> list[str]:
        if packet.expected_artifacts:
            artifact = packet.expected_artifacts[0]
        else:
            artifact_stem = (
                plan.cluster_template_ids[0]
                if plan is not None and plan.cluster_template_ids
                else (plan.preset_id if plan is not None else "orchestration")
            )
            artifact = f"state/artifacts/{artifact_stem}_orchestration.md"
        path = Path(artifact)
        if not path.is_absolute():
            path = Path(packet.working_directory) / path
        resolved = path.resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return [resolved.as_posix()]

    def _group_steps(self, plan: OrchestrationPlan) -> list[list[OrchestrationStep]]:
        grouped: dict[int, list[OrchestrationStep]] = {}
        for step in sorted(plan.steps, key=lambda item: (item.sequence_no, str(item.role), item.step_id)):
            grouped.setdefault(step.sequence_no, []).append(step)
        return [grouped[sequence_no] for sequence_no in sorted(grouped)]

    def execute_orchestration_packet(self, packet: TaskPacket) -> ExecutionResult:
        started_at = utc_now()
        orchestration_payload = packet.env.get("WORKFLOW_ORCHESTRATION_PLAN")
        preset_id = str(packet.env.get("WORKFLOW_PRESET_ID") or "project_delivery")
        orchestration = (
            OrchestrationPlan.model_validate(json.loads(orchestration_payload))
            if orchestration_payload
            else (
                self.default_orchestration_plan_for_preset(preset_id, packet.run_id)
                or self.default_orchestration_plan_for_preset("project_delivery", packet.run_id)
            )
        )
        if orchestration is None:
            raise ValueError("orchestration plan was not available for execution")

        parent_goal = packet.env.get("WORKFLOW_RUN_GOAL", "")
        parent_mutation_contract = packet.mutation_contract
        child_runs: list[dict[str, Any]] = []
        role_progress: dict[str, dict[str, Any]] = {}
        prior_run_ids: list[str] = []
        step_mutation_contracts: dict[str, MutationContract | None] = {}
        parallel_batches: list[dict[str, Any]] = []

        for group in self._group_steps(orchestration):
            resumed_run_ids: list[str] = []
            for step in group:
                mutation_contract = (
                    parent_mutation_contract
                    if step.role == AgentRoleType.coder
                    and parent_mutation_contract is not None
                    and parent_mutation_contract.mutation_mode == MutationMode.patch_apply
                    else None
                )
                step_mutation_contracts[step.step_id] = mutation_contract
                child_run = self._facade.create_run(
                    self._goal_for_step(parent_goal, step, prior_run_ids=prior_run_ids),
                    step.preset_id,
                )
                prepared = self.compile_child_run_with_fallback(
                    child_run.run_id,
                    preferred_adapter=step.preferred_adapter,
                    fallback_adapter=step.fallback_adapter,
                    mutation_contract=mutation_contract,
                    execution_profile=step.execution_profile,
                    agent_profile_id=step.agent_profile_id,
                    cluster_template_id=step.cluster_template_id,
                    cluster_member_id=step.cluster_member_id,
                    public_role=str(step.role),
                    role_label=step.role_label,
                )
                step.run_id = child_run.run_id
                step.status = "prepared"
                resumed_run_ids.append(child_run.run_id)
                child_runs.append(
                    {
                        "step_id": step.step_id,
                        "role": str(step.role),
                        "role_label": step.role_label,
                        "run_id": child_run.run_id,
                        "status": "prepared",
                        "runtime_task_id": prepared.task_packet.runtime_task_id,
                        "barrier_id": step.barrier_id,
                        "mutation_contract": (
                            prepared.task_packet.mutation_contract.model_dump(mode="json")
                            if prepared.task_packet.mutation_contract is not None
                            else None
                        ),
                    }
                )

            if len(resumed_run_ids) > 1:
                parallel_result = self._facade.resume_runs_parallel(resumed_run_ids, max_workers=len(resumed_run_ids))
            elif resumed_run_ids:
                self._facade.resume_run(resumed_run_ids[0])
                parallel_result = {"results": []}
            else:
                parallel_result = {"results": []}

            group_barrier_ids = {step.barrier_id for step in group if step.barrier_id}
            for step in group:
                finalized = self.finalize_child_run_if_waiting(step.run_id or "")
                if (
                    str(finalized.status) != "completed"
                    and step.fallback_adapter
                    and step.fallback_adapter != step.preferred_adapter
                ):
                    recovered_run = self._facade.create_run(
                        self._goal_for_step(parent_goal, step, prior_run_ids=prior_run_ids),
                        step.preset_id,
                    )
                    recovered_bundle = self.compile_child_run_with_fallback(
                        recovered_run.run_id,
                        preferred_adapter=step.fallback_adapter,
                        fallback_adapter=None,
                        mutation_contract=step_mutation_contracts.get(step.step_id),
                        execution_profile=step.execution_profile,
                        agent_profile_id=step.agent_profile_id,
                        cluster_template_id=step.cluster_template_id,
                        cluster_member_id=step.cluster_member_id,
                        public_role=str(step.role),
                        role_label=step.role_label,
                    )
                    self._facade.resume_run(recovered_run.run_id)
                    finalized = self.finalize_child_run_if_waiting(recovered_run.run_id)
                    step.run_id = recovered_run.run_id
                    for child in child_runs:
                        if child["step_id"] == step.step_id:
                            child["run_id"] = recovered_run.run_id
                            child["runtime_task_id"] = recovered_bundle.task_packet.runtime_task_id
                step.status = str(finalized.status)
                mutation_report = (
                    self._facade.get_run_mutation_report(step.run_id)
                    if step.role == AgentRoleType.coder and step.run_id is not None
                    else None
                )
                role_progress[str(step.role)] = {
                    "status": str(finalized.status),
                    "run_id": step.run_id,
                    "barrier_id": step.barrier_id,
                    "role_label": step.role_label,
                }
                if mutation_report is not None:
                    role_progress[str(step.role)]["mutation_report"] = mutation_report
                for child in child_runs:
                    if child["step_id"] == step.step_id:
                        child["status"] = str(finalized.status)
                        if mutation_report is not None:
                            child["mutation_report"] = mutation_report
                if step.run_id:
                    prior_run_ids.append(step.run_id)

            for barrier in orchestration.barriers:
                if barrier.barrier_id in group_barrier_ids:
                    barrier.status = "released" if resumed_run_ids else "skipped"
                    parallel_batches.append(
                        {
                            "barrier_id": barrier.barrier_id,
                            "member_count": barrier.member_count,
                            "status": barrier.status,
                            "results": parallel_result.get("results", []),
                        }
                    )

        primary_parallel_batch = (
            parallel_batches[0]
            if parallel_batches
            else {"barrier_id": None, "member_count": 0, "status": "skipped", "results": []}
        )
        orchestration_summary = {
            "orchestration_id": orchestration.orchestration_id,
            "execution_mode": orchestration.execution_mode,
            "preset_id": orchestration.preset_id,
            "cluster_template_ids": list(orchestration.cluster_template_ids),
            "plan": orchestration.model_dump(mode="json"),
            "child_runs": child_runs,
            "parallel_batch": primary_parallel_batch,
            "parallel_batches": parallel_batches,
            "role_progress": role_progress,
        }
        content_lines = [
            "# Orchestration Execution Summary",
            "",
            f"goal: {parent_goal}",
            f"orchestration_id: {orchestration.orchestration_id}",
            f"preset_id: {orchestration.preset_id}",
            "roles:",
        ]
        for item in child_runs:
            role_label = f" ({item['role_label']})" if item.get("role_label") else ""
            content_lines.append(f"- {item['role']}{role_label}: {item['run_id']} status={item['status']}")
        artifact_paths = self.write_orchestration_artifact(
            packet,
            "\n".join(content_lines) + "\n",
            plan=orchestration,
        )
        finished_at = utc_now()
        return_code = 0 if all(item["status"] == "completed" for item in child_runs) else 1
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=return_code,
            stdout=json.dumps(orchestration_summary, ensure_ascii=False),
            stderr="" if return_code == 0 else "one or more orchestration child runs did not complete successfully",
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
            artifact_paths=artifact_paths,
            adapter_name="shell",
            metadata={"orchestration": orchestration_summary},
        )
