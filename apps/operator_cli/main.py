from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, Optional, TypeVar

import typer

from apps.operator_tui.dashboard import run_dashboard
from packages.core_domain.config import build_effective_config
from packages.core_domain.db import DEFAULT_DB_PATH, get_migration_status, migrate, reset_db, workspace_scoped_db_path
from packages.core_domain.errors import WorkflowError
from packages.core_domain.governance import (
    build_domain_pack_platform_report,
    build_governance_alert_report,
    build_governance_metrics_report,
    build_release_readiness_report,
    build_review_policy_report,
    build_tech_debt_report,
)
from packages.core_domain.repositories import PresetRepository, TaskRepository
from packages.core_domain.services import OrchestratorService

app = typer.Typer(help="Workflow operator CLI.")
run_app = typer.Typer(help="Run lifecycle commands.")
interaction_app = typer.Typer(help="Interaction-plane session, profile, and cluster commands.")
task_app = typer.Typer(help="Task inspection commands.")
preset_app = typer.Typer(help="Preset inspection commands.")
domain_pack_app = typer.Typer(help="Domain pack inspection commands.")
capability_app = typer.Typer(help="Capability registry inspection commands.")
simulation_app = typer.Typer(help="Simulation policy commands.")
simulation_policy_app = typer.Typer(help="Simulation policy catalog commands.")
memory_app = typer.Typer(help="Memory-plane inspection commands.")
memory_namespace_app = typer.Typer(help="Memory namespace inspection commands.")
memory_item_app = typer.Typer(help="Persistent memory item commands.")
scheduler_app = typer.Typer(help="Scheduler authority and cluster inspection commands.")
db_app = typer.Typer(help="Development database commands.")
governance_app = typer.Typer(help="Governance and debt visibility commands.")
config_app = typer.Typer(help="Unified configuration inspection commands.")

app.add_typer(run_app, name="run")
app.add_typer(interaction_app, name="interaction")
app.add_typer(task_app, name="task")
app.add_typer(preset_app, name="preset")
app.add_typer(domain_pack_app, name="domain-pack")
app.add_typer(capability_app, name="capability")
app.add_typer(simulation_app, name="simulation")
app.add_typer(memory_app, name="memory")
app.add_typer(scheduler_app, name="scheduler")
app.add_typer(db_app, name="db")
app.add_typer(governance_app, name="governance")
app.add_typer(config_app, name="config")
memory_app.add_typer(memory_namespace_app, name="namespace")
memory_app.add_typer(memory_item_app, name="item")
simulation_app.add_typer(simulation_policy_app, name="policy")

T = TypeVar("T")


def _db_path_from_context(ctx: typer.Context) -> Path:
    return Path(ctx.obj["db_path"])


def _service(ctx: typer.Context) -> OrchestratorService:
    db_path = _db_path_from_context(ctx)
    migrate(db_path)
    return OrchestratorService(db_path)


def _emit_json(payload: dict | list) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


def _workflow_error_payload(exc: WorkflowError) -> dict:
    return {"error": {"code": exc.code, "message": exc.message, "details": exc.details}}


def _run_workflow_action(action: Callable[[], T]) -> T:
    try:
        return action()
    except WorkflowError as exc:
        _emit_json(_workflow_error_payload(exc))
        raise typer.Exit(code=1) from exc


def _parse_key_value_pairs(values: Optional[list[str]]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw in values or []:
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and value:
            parsed[key] = value
    return parsed


@app.callback()
def main(
    ctx: typer.Context,
    db_path: Optional[str] = typer.Option(None, "--db-path", help="SQLite database path."),
) -> None:
    effective = build_effective_config(explicit_db_path=db_path)
    ctx.obj = {"db_path": effective["db"]["path"], "effective_config": effective}


@app.command("tui")
def launch_tui(
    ctx: typer.Context,
    run_id: Optional[str] = typer.Option(None, "--run-id", help="Focus a specific run in the dashboard."),
    limit: int = typer.Option(8, "--limit", min=1, help="Maximum number of recent runs to render."),
    refresh_seconds: float = typer.Option(2.0, "--refresh-seconds", min=0.2, help="Refresh interval in watch mode."),
    once: bool = typer.Option(False, "--once", help="Render one snapshot instead of entering watch mode."),
    cycles: Optional[int] = typer.Option(
        None,
        "--cycles",
        min=1,
        help="Maximum refresh cycles in watch mode. Useful for tests.",
    ),
) -> None:
    service = _service(ctx)
    run_dashboard(
        service,
        run_id=run_id,
        limit=limit,
        refresh_seconds=refresh_seconds,
        once=once,
        cycles=cycles,
    )


@preset_app.command("list")
def preset_list(ctx: typer.Context, as_json: bool = typer.Option(False, "--json")) -> None:
    presets = _run_workflow_action(lambda: _service(ctx).list_presets())
    if as_json:
        _emit_json([preset.model_dump(mode="json") for preset in presets])
        return
    for preset in presets:
        typer.echo(
            f"{preset.preset_id} | review={preset.default_review_policy} | task_kinds={','.join(preset.allowed_task_kinds)}"
        )


@domain_pack_app.command("list")
def domain_pack_list(ctx: typer.Context, as_json: bool = typer.Option(False, "--json")) -> None:
    domain_packs = _run_workflow_action(lambda: _service(ctx).list_domain_packs())
    if as_json:
        _emit_json([domain_pack.model_dump(mode="json") for domain_pack in domain_packs])
        return
    for domain_pack in domain_packs:
        typer.echo(
            f"{domain_pack.domain_pack_id} | enabled={domain_pack.enabled} | presets={','.join(domain_pack.preset_ids)}"
        )


@domain_pack_app.command("resolve")
def domain_pack_resolve(
    ctx: typer.Context,
    preset: str = typer.Option(..., "--preset"),
    task_kind: Optional[str] = typer.Option(None, "--task-kind"),
    adapter: Optional[str] = typer.Option(None, "--adapter"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).preview_domain_pack_resolution(
                preset_id=preset,
                task_kind=task_kind,
                adapter_name=adapter,
            )
        )
    )


@domain_pack_app.command("validate")
def domain_pack_validate(ctx: typer.Context) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).validate_domain_pack_catalog()))


@domain_pack_app.command("export-skill")
def domain_pack_export_skill(
    ctx: typer.Context,
    domain_pack_id: str = typer.Option(..., "--domain-pack-id"),
    output_root: str = typer.Option("state/skills", "--output-root"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).export_domain_pack_skill(
                domain_pack_id,
                output_root=output_root,
            )
        )
    )


@capability_app.command("list")
def capability_list(ctx: typer.Context) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).list_capability_routes()))


@capability_app.command("sources")
def capability_sources(ctx: typer.Context) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).list_capability_sources()))


@capability_app.command("descriptors")
def capability_descriptors(ctx: typer.Context) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).list_capability_descriptors()))


@capability_app.command("health")
def capability_health(ctx: typer.Context) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).list_capability_health()))


@capability_app.command("mcp-profiles")
def capability_mcp_profiles(ctx: typer.Context) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).list_mcp_server_profiles()))


@capability_app.command("worker-pools")
def capability_worker_pools(ctx: typer.Context) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).list_worker_pool_profiles()))


@capability_app.command("projection")
def capability_projection(
    ctx: typer.Context,
    preset: str = typer.Option(..., "--preset"),
    task_kind: Optional[str] = typer.Option(None, "--task-kind"),
    adapter: Optional[str] = typer.Option(None, "--adapter"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).preview_tool_projection(
                preset_id=preset,
                task_kind=task_kind,
                adapter_name=adapter,
            )
        )
    )


@simulation_policy_app.command("list")
def simulation_policy_list(ctx: typer.Context) -> None:
    policies = _run_workflow_action(lambda: _service(ctx).list_simulation_policies())
    _emit_json([policy.model_dump(mode="json") for policy in policies])


@memory_namespace_app.command("list")
def memory_namespace_list(ctx: typer.Context) -> None:
    namespaces = _run_workflow_action(lambda: _service(ctx).list_memory_namespaces())
    _emit_json([namespace.model_dump(mode="json") for namespace in namespaces])


@memory_item_app.command("list")
def memory_item_list(
    ctx: typer.Context,
    run_id: Optional[str] = typer.Option(None, "--run-id"),
    namespace: Optional[str] = typer.Option(None, "--namespace"),
) -> None:
    items = _run_workflow_action(lambda: _service(ctx).list_memory_items(run_id=run_id, namespace_id=namespace))
    _emit_json([item.model_dump(mode="json") for item in items])


@memory_app.command("retrieve-preview")
def memory_retrieve_preview(
    ctx: typer.Context,
    preset: Optional[str] = typer.Option(None, "--preset"),
    run_id: Optional[str] = typer.Option(None, "--run-id"),
    namespace: Optional[str] = typer.Option(None, "--namespace"),
    memory_item_id: Optional[list[str]] = typer.Option(None, "--memory-item-id"),
    limit: int = typer.Option(5, "--limit", min=1),
) -> None:
    preview = _run_workflow_action(
        lambda: _service(ctx).preview_memory_retrieval(
            preset_id=preset,
            run_id=run_id,
            namespace_id=namespace,
            memory_item_ids=memory_item_id,
            limit=limit,
        )
    )
    _emit_json(preview.model_dump(mode="json"))


@run_app.command("create")
def run_create(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    preset: str = typer.Option(..., "--preset"),
    task_kind: Optional[str] = typer.Option(None, "--task-kind", help="Requested task kind when compiling."),
    adapter: Optional[str] = typer.Option(None, "--adapter", help="Requested adapter override when compiling."),
    memory_item_id: Optional[list[str]] = typer.Option(None, "--memory-item-id", help="Explicit memory item ids."),
    task_card_ref: Optional[str] = typer.Option(None, "--task-card-ref", help="Detailed task card reference for repo mutation."),
    task_card_path: Optional[str] = typer.Option(None, "--task-card-path", help="Detailed task card path for repo mutation."),
    write_set: Optional[list[str]] = typer.Option(None, "--write-set", help="Explicit writable paths for repo mutation."),
    read_set: Optional[list[str]] = typer.Option(None, "--read-set", help="Explicit read-only context paths for repo mutation."),
    test_command: Optional[list[str]] = typer.Option(None, "--test-command", help="Explicit test commands to run after applying a patch."),
    max_fix_iterations: int = typer.Option(0, "--max-fix-iterations", min=0, help="Maximum bounded repair iterations."),
    mutation_mode: Optional[str] = typer.Option(None, "--mutation-mode", help="artifact_only or patch_apply."),
    prepare: bool = typer.Option(False, "--prepare", help="Prepare the run internally after creation."),
    execute: bool = typer.Option(False, "--execute", help="Execute the prepared run internally."),
) -> None:
    service = _service(ctx)
    run = _run_workflow_action(lambda: service.create_run(goal=goal, preset_id=preset))
    current_run = run
    payload: dict = {}
    if prepare or execute:
        prepared = _run_workflow_action(
            lambda: service.compile_run(
                run.run_id,
                task_kind=task_kind,
                adapter_name=adapter,
                memory_item_ids=memory_item_id,
                task_card_ref=task_card_ref,
                task_card_path=task_card_path,
                write_set=write_set,
                read_set=read_set,
                test_commands=test_command,
                max_fix_iterations=max_fix_iterations,
                mutation_mode=mutation_mode,
            )
        )
        current_run = prepared.run
        payload["prepared_task_id"] = prepared.task_packet.runtime_task_id
        payload["expected_artifacts"] = prepared.task_packet.expected_artifacts
        payload["handoff_id"] = prepared.handoff.handoff_id
        payload["state_ref_id"] = prepared.state_ref.state_ref_id
        payload["domain_pack_id"] = prepared.domain_pack.domain_pack_id if prepared.domain_pack is not None else None
        payload["capability_adapter"] = (
            prepared.capability_route.adapter_name if prepared.capability_route is not None else None
        )
        payload["execution_lane"] = str(prepared.execution_lane)
        payload["mutation_contract"] = (
            prepared.task_packet.mutation_contract.model_dump(mode="json")
            if prepared.task_packet.mutation_contract is not None
            else None
        )
        payload["tool_projection_manifest"] = (
            prepared.tool_projection_manifest.model_dump(mode="json")
            if prepared.tool_projection_manifest is not None
            else None
        )
        payload["mcp_server_profiles"] = [profile.model_dump(mode="json") for profile in prepared.mcp_server_profiles]
        payload["memory_preview"] = (
            prepared.memory_preview.model_dump(mode="json") if prepared.memory_preview is not None else None
        )
    if execute:
        executed = _run_workflow_action(lambda: service.resume_run(run.run_id))
        current_run = executed.run
        payload["review_decision"] = executed.review_verdict.decision if executed.review_verdict is not None else None
        payload["evidence_id"] = executed.evidence.evidence_id
    payload["run"] = current_run.model_dump(mode="json")
    _emit_json(payload)


@run_app.command("suggest-presets")
def run_suggest_presets(ctx: typer.Context, goal: str = typer.Option(..., "--goal")) -> None:
    suggestions = _run_workflow_action(lambda: _service(ctx).suggest_presets(goal))
    _emit_json([item.model_dump(mode="json") for item in suggestions])


@run_app.command("plan-graph")
def run_plan_graph(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    preset: Optional[str] = typer.Option(None, "--preset"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).preview_orchestration_plan_graph(
                goal=goal,
                preset_id=preset,
            )
        )
    )


@run_app.command("policy-preview")
def run_policy_preview(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    preset: Optional[str] = typer.Option(None, "--preset"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).preview_capability_policy(
                goal=goal,
                preset_id=preset,
            )
        )
    )


@run_app.command("goal-packet")
def run_goal_packet(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    preset: Optional[str] = typer.Option(None, "--preset"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).preview_goal_packet(
                goal=goal,
                preset_id=preset,
            )
        )
    )


@run_app.command("launch")
def run_launch(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    preset: Optional[str] = typer.Option(None, "--preset"),
    execute: bool = typer.Option(False, "--execute", help="Execute after compile."),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).launch_goal(
                goal=goal,
                preset_id=preset,
                execute=execute,
            )
        )
    )


@interaction_app.command("profiles")
def interaction_profiles(ctx: typer.Context) -> None:
    registry = _run_workflow_action(lambda: _service(ctx).get_agent_profile_registry())
    _emit_json(registry.model_dump(mode="json"))


@interaction_app.command("clusters")
def interaction_clusters(ctx: typer.Context) -> None:
    templates = _run_workflow_action(lambda: _service(ctx).list_cluster_templates())
    _emit_json([template.model_dump(mode="json") for template in templates])


@interaction_app.command("create-session")
def interaction_create_session(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    preset: Optional[str] = typer.Option(None, "--preset"),
    cluster: Optional[str] = typer.Option(None, "--cluster"),
    constraint: Optional[list[str]] = typer.Option(None, "--constraint"),
    assumption: Optional[list[str]] = typer.Option(None, "--assumption"),
    artifact: Optional[list[str]] = typer.Option(None, "--artifact"),
    followup_context: Optional[list[str]] = typer.Option(None, "--followup-context"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).create_intent_session(
                goal=goal,
                preferred_preset_id=preset,
                preferred_cluster_template_ids=[cluster] if cluster else None,
                constraints=constraint,
                assumptions=assumption,
                referenced_artifact_paths=artifact,
                followup_context=followup_context,
            )
        )
    )


@interaction_app.command("sessions")
def interaction_sessions(
    ctx: typer.Context,
    limit: int = typer.Option(10, "--limit", min=1),
    status: Optional[str] = typer.Option(None, "--status"),
) -> None:
    sessions = _run_workflow_action(lambda: _service(ctx).list_intent_sessions(limit=limit, status=status))
    _emit_json([session.model_dump(mode="json") for session in sessions])


@interaction_app.command("generated-profiles")
def interaction_generated_profiles(
    ctx: typer.Context,
    session_id: Optional[str] = typer.Option(None, "--session-id"),
    run_id: Optional[str] = typer.Option(None, "--run-id"),
    limit: int = typer.Option(20, "--limit", min=1),
) -> None:
    profiles = _run_workflow_action(
        lambda: _service(ctx).list_generated_agent_profiles(session_id=session_id, run_id=run_id, limit=limit)
    )
    _emit_json([profile.model_dump(mode="json") for profile in profiles])


@interaction_app.command("generate-profiles")
def interaction_generate_profiles(ctx: typer.Context, session_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).generate_session_profiles(session_id)))


@interaction_app.command("get-session")
def interaction_get_session(ctx: typer.Context, session_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_intent_session_payload(session_id)))


@interaction_app.command("clarify")
def interaction_clarify(
    ctx: typer.Context,
    session_id: str,
    answer: Optional[list[str]] = typer.Option(None, "--answer", help="prompt_id=value"),
    preset: Optional[str] = typer.Option(None, "--preset"),
    cluster: Optional[str] = typer.Option(None, "--cluster"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).continue_intent_session(
                session_id,
                answers=_parse_key_value_pairs(answer),
                preferred_preset_id=preset,
                preferred_cluster_template_ids=[cluster] if cluster else None,
            )
        )
    )


@interaction_app.command("plan-draft")
def interaction_plan_draft(
    ctx: typer.Context,
    session_id: str,
    preset: Optional[str] = typer.Option(None, "--preset"),
    cluster: Optional[str] = typer.Option(None, "--cluster"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).create_intent_plan_draft(
                session_id,
                preferred_preset_id=preset,
                preferred_cluster_template_ids=[cluster] if cluster else None,
            )
        )
    )


@interaction_app.command("launch")
def interaction_launch(
    ctx: typer.Context,
    session_id: str,
    execute: bool = typer.Option(False, "--execute"),
    preset: Optional[str] = typer.Option(None, "--preset"),
    cluster: Optional[str] = typer.Option(None, "--cluster"),
    rationale: Optional[str] = typer.Option(None, "--rationale"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).launch_intent_session(
                session_id,
                execute=execute,
                rationale=rationale,
                selected_preset_id=preset,
                selected_cluster_template_ids=[cluster] if cluster else None,
            )
        )
    )


@interaction_app.command("followup")
def interaction_followup(
    ctx: typer.Context,
    session_id: str,
    instruction: str = typer.Option(..., "--instruction"),
    intent: str = typer.Option("continue", "--intent"),
    blocking: bool = typer.Option(False, "--blocking"),
    run_id: Optional[str] = typer.Option(None, "--run-id"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).create_followup_request(
                session_id,
                instruction=instruction,
                intent=intent,
                blocking=blocking,
                run_id=run_id,
            )
        )
    )


@interaction_app.command("followups")
def interaction_followups(
    ctx: typer.Context,
    session_id: str,
    limit: int = typer.Option(20, "--limit", min=1),
) -> None:
    followups = _run_workflow_action(lambda: _service(ctx).list_followup_requests(session_id, limit=limit))
    _emit_json([item.model_dump(mode="json") for item in followups])


@interaction_app.command("watchdogs")
def interaction_watchdogs(
    ctx: typer.Context,
    session_id: Optional[str] = typer.Option(None, "--session-id"),
    run_id: Optional[str] = typer.Option(None, "--run-id"),
    status: Optional[str] = typer.Option(None, "--status"),
    limit: int = typer.Option(20, "--limit", min=1),
) -> None:
    watchdogs = _run_workflow_action(
        lambda: _service(ctx).list_automation_watchdogs(
            session_id=session_id,
            run_id=run_id,
            status=status,
            limit=limit,
        )
    )
    _emit_json([item.model_dump(mode="json") for item in watchdogs])


@interaction_app.command("evaluate-watchdogs")
def interaction_evaluate_watchdogs(
    ctx: typer.Context,
    session_id: Optional[str] = typer.Option(None, "--session-id"),
    run_id: Optional[str] = typer.Option(None, "--run-id"),
    auto_apply: bool = typer.Option(False, "--auto-apply"),
    limit: int = typer.Option(20, "--limit", min=1),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).evaluate_watchdogs(
                session_id=session_id,
                run_id=run_id,
                auto_apply=auto_apply,
                limit=limit,
            )
        )
    )


@run_app.command("compile")
def run_compile(
    ctx: typer.Context,
    run_id: str,
    task_kind: Optional[str] = typer.Option(None, "--task-kind", help="Requested task kind override."),
    adapter: Optional[str] = typer.Option(None, "--adapter", help="Requested adapter override."),
    agent_model: Optional[str] = typer.Option(None, "--agent-model", help="Requested agent model override."),
    codex_model: Optional[str] = typer.Option(None, "--codex-model", help="Requested codex model override."),
    opencode_model: Optional[str] = typer.Option(None, "--opencode-model", help="Requested opencode model override."),
    opencode_variant: Optional[str] = typer.Option(None, "--opencode-variant", help="Requested opencode variant override."),
    runtime_gateway_provider: Optional[str] = typer.Option(None, "--runtime-gateway-provider", help="Requested runtime gateway provider override."),
    runtime_gateway_model: Optional[str] = typer.Option(None, "--runtime-gateway-model", help="Requested runtime gateway model override."),
    runtime_reasoning_effort: Optional[str] = typer.Option(None, "--runtime-reasoning-effort", help="Requested runtime reasoning effort override."),
    worker_pool_id: Optional[str] = typer.Option(None, "--worker-pool-id", help="Requested worker pool override."),
    memory_item_id: Optional[list[str]] = typer.Option(None, "--memory-item-id", help="Explicit memory item ids."),
    task_card_ref: Optional[str] = typer.Option(None, "--task-card-ref", help="Detailed task card reference for repo mutation."),
    task_card_path: Optional[str] = typer.Option(None, "--task-card-path", help="Detailed task card path for repo mutation."),
    write_set: Optional[list[str]] = typer.Option(None, "--write-set", help="Explicit writable paths for repo mutation."),
    read_set: Optional[list[str]] = typer.Option(None, "--read-set", help="Explicit read-only context paths for repo mutation."),
    test_command: Optional[list[str]] = typer.Option(None, "--test-command", help="Explicit test commands to run after applying a patch."),
    max_fix_iterations: int = typer.Option(0, "--max-fix-iterations", min=0, help="Maximum bounded repair iterations."),
    mutation_mode: Optional[str] = typer.Option(None, "--mutation-mode", help="artifact_only or patch_apply."),
) -> None:
    prepared = _run_workflow_action(
        lambda: _service(ctx).compile_run(
            run_id,
            task_kind=task_kind,
            adapter_name=adapter,
            agent_model=agent_model,
            codex_model=codex_model,
            opencode_model=opencode_model,
            opencode_variant=opencode_variant,
            runtime_gateway_provider=runtime_gateway_provider,
            runtime_gateway_model=runtime_gateway_model,
            runtime_reasoning_effort=runtime_reasoning_effort,
            worker_pool_id=worker_pool_id,
            memory_item_ids=memory_item_id,
            task_card_ref=task_card_ref,
            task_card_path=task_card_path,
            write_set=write_set,
            read_set=read_set,
            test_commands=test_command,
            max_fix_iterations=max_fix_iterations,
            mutation_mode=mutation_mode,
        )
    )
    _emit_json(
        {
            "run": prepared.run.model_dump(mode="json"),
            "runtime_task_id": prepared.task_packet.runtime_task_id,
            "handoff_id": prepared.handoff.handoff_id,
            "state_ref_id": prepared.state_ref.state_ref_id,
            "domain_pack_id": prepared.domain_pack.domain_pack_id if prepared.domain_pack is not None else None,
            "capability_adapter": prepared.capability_route.adapter_name if prepared.capability_route is not None else None,
            "execution_lane": str(prepared.execution_lane),
            "resolved_execution": prepared.resolved_execution.model_dump(mode="json"),
            "mutation_contract": (
                prepared.task_packet.mutation_contract.model_dump(mode="json")
                if prepared.task_packet.mutation_contract is not None
                else None
            ),
            "tool_projection_manifest": (
                prepared.tool_projection_manifest.model_dump(mode="json")
                if prepared.tool_projection_manifest is not None
                else None
            ),
            "mcp_server_profiles": [profile.model_dump(mode="json") for profile in prepared.mcp_server_profiles],
            "memory_preview": prepared.memory_preview.model_dump(mode="json") if prepared.memory_preview is not None else None,
        }
    )


@run_app.command("recompile")
def run_recompile(
    ctx: typer.Context,
    run_id: str,
    task_kind: Optional[str] = typer.Option(None, "--task-kind", help="Requested task kind override."),
    adapter: Optional[str] = typer.Option(None, "--adapter", help="Requested adapter override."),
    agent_model: Optional[str] = typer.Option(None, "--agent-model", help="Requested agent model override."),
    codex_model: Optional[str] = typer.Option(None, "--codex-model", help="Requested codex model override."),
    opencode_model: Optional[str] = typer.Option(None, "--opencode-model", help="Requested opencode model override."),
    opencode_variant: Optional[str] = typer.Option(None, "--opencode-variant", help="Requested opencode variant override."),
    runtime_gateway_provider: Optional[str] = typer.Option(None, "--runtime-gateway-provider", help="Requested runtime gateway provider override."),
    runtime_gateway_model: Optional[str] = typer.Option(None, "--runtime-gateway-model", help="Requested runtime gateway model override."),
    runtime_reasoning_effort: Optional[str] = typer.Option(None, "--runtime-reasoning-effort", help="Requested runtime reasoning effort override."),
    worker_pool_id: Optional[str] = typer.Option(None, "--worker-pool-id", help="Requested worker pool override."),
    memory_item_id: Optional[list[str]] = typer.Option(None, "--memory-item-id", help="Explicit memory item ids."),
    task_card_ref: Optional[str] = typer.Option(None, "--task-card-ref", help="Detailed task card reference for repo mutation."),
    task_card_path: Optional[str] = typer.Option(None, "--task-card-path", help="Detailed task card path for repo mutation."),
    write_set: Optional[list[str]] = typer.Option(None, "--write-set", help="Explicit writable paths for repo mutation."),
    read_set: Optional[list[str]] = typer.Option(None, "--read-set", help="Explicit read-only context paths for repo mutation."),
    test_command: Optional[list[str]] = typer.Option(None, "--test-command", help="Explicit test commands to run after applying a patch."),
    max_fix_iterations: int = typer.Option(0, "--max-fix-iterations", min=0, help="Maximum bounded repair iterations."),
    mutation_mode: Optional[str] = typer.Option(None, "--mutation-mode", help="artifact_only or patch_apply."),
) -> None:
    prepared = _run_workflow_action(
        lambda: _service(ctx).recompile_run(
            run_id,
            task_kind=task_kind,
            adapter_name=adapter,
            agent_model=agent_model,
            codex_model=codex_model,
            opencode_model=opencode_model,
            opencode_variant=opencode_variant,
            runtime_gateway_provider=runtime_gateway_provider,
            runtime_gateway_model=runtime_gateway_model,
            runtime_reasoning_effort=runtime_reasoning_effort,
            worker_pool_id=worker_pool_id,
            memory_item_ids=memory_item_id,
            task_card_ref=task_card_ref,
            task_card_path=task_card_path,
            write_set=write_set,
            read_set=read_set,
            test_commands=test_command,
            max_fix_iterations=max_fix_iterations,
            mutation_mode=mutation_mode,
        )
    )
    _emit_json(
        {
            "run": prepared.run.model_dump(mode="json"),
            "runtime_task_id": prepared.task_packet.runtime_task_id,
            "handoff_id": prepared.handoff.handoff_id,
            "state_ref_id": prepared.state_ref.state_ref_id,
            "domain_pack_id": prepared.domain_pack.domain_pack_id if prepared.domain_pack is not None else None,
            "capability_adapter": prepared.capability_route.adapter_name if prepared.capability_route is not None else None,
            "execution_lane": str(prepared.execution_lane),
            "resolved_execution": prepared.resolved_execution.model_dump(mode="json"),
            "mutation_contract": (
                prepared.task_packet.mutation_contract.model_dump(mode="json")
                if prepared.task_packet.mutation_contract is not None
                else None
            ),
            "tool_projection_manifest": (
                prepared.tool_projection_manifest.model_dump(mode="json")
                if prepared.tool_projection_manifest is not None
                else None
            ),
            "mcp_server_profiles": [profile.model_dump(mode="json") for profile in prepared.mcp_server_profiles],
            "memory_preview": prepared.memory_preview.model_dump(mode="json") if prepared.memory_preview is not None else None,
        }
    )


@run_app.command("resume")
def run_resume(ctx: typer.Context, run_id: str) -> None:
    executed = _run_workflow_action(lambda: _service(ctx).resume_run(run_id))
    _emit_json(
        {
            "run": executed.run.model_dump(mode="json"),
            "evidence_id": executed.evidence.evidence_id,
            "review_decision": executed.review_verdict.decision if executed.review_verdict is not None else None,
        }
    )


@run_app.command("batch-resume")
def run_batch_resume(
    ctx: typer.Context,
    run_id: list[str] = typer.Argument(..., help="Prepared run ids to resume behind one local batch barrier."),
    max_workers: Optional[int] = typer.Option(None, "--max-workers", min=1),
) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).resume_runs_parallel(run_id, max_workers=max_workers)))


@run_app.command("approve")
def run_approve(ctx: typer.Context, run_id: str) -> None:
    reviewed = _run_workflow_action(lambda: _service(ctx).approve_run_review(run_id))
    _emit_json(
        {
            "run": reviewed.run.model_dump(mode="json"),
            "evidence_id": reviewed.evidence.evidence_id,
            "review_decision": reviewed.review_verdict.decision,
        }
    )


@run_app.command("reject")
def run_reject(ctx: typer.Context, run_id: str) -> None:
    reviewed = _run_workflow_action(lambda: _service(ctx).reject_run_review(run_id))
    _emit_json(
        {
            "run": reviewed.run.model_dump(mode="json"),
            "evidence_id": reviewed.evidence.evidence_id,
            "review_decision": reviewed.review_verdict.decision,
        }
    )


@run_app.command("cancel")
def run_cancel(ctx: typer.Context, run_id: str) -> None:
    run = _run_workflow_action(lambda: _service(ctx).cancel_run(run_id))
    _emit_json(run.model_dump(mode="json"))


@run_app.command("status")
def run_status(ctx: typer.Context, run_id: str) -> None:
    service = _service(ctx)
    detail = _run_workflow_action(lambda: service.get_status_detail(run_id))
    payload = detail["run"]
    payload["runtime_gateway"] = detail["runtime_gateway"]
    payload["review_policy"] = detail["review_policy"]
    payload["runtime_task_ids"] = detail["runtime_task_ids"]
    payload["current_runtime_attempt"] = detail["current_runtime_attempt"]
    payload["latest_runtime_attempt"] = detail["latest_runtime_attempt"]
    payload["runtime_attempt_projection"] = detail["runtime_attempt_projection"]
    payload["active_claims"] = detail["active_claims"]
    payload["latest_claim"] = detail["latest_claim"]
    payload["active_worker_leases"] = detail["active_worker_leases"]
    payload["latest_worker_lease"] = detail["latest_worker_lease"]
    payload["ownership_topology"] = detail["ownership_topology"]
    payload["parallel_batch"] = detail["parallel_batch"]
    payload["worker_lease_projection"] = detail["worker_lease_projection"]
    payload["execution_target"] = detail["execution_target"]
    payload["lease_renewals"] = detail["lease_renewals"]
    payload["mutation_contract"] = detail["mutation_contract"]
    payload["mutation_result"] = detail["mutation_result"]
    payload["orchestration"] = detail["orchestration"]
    payload["orchestration_plan_graph"] = detail["orchestration_plan_graph"]
    payload["capability_policy_preview"] = detail["capability_policy_preview"]
    payload["operator_projection"] = detail["operator_projection"]
    payload["effective_review_state"] = detail["effective_review_state"]
    payload["domain_pack"] = detail["domain_pack"]
    payload["capability_resolution"] = detail["capability_resolution"]
    payload["latest_review_verdict"] = detail["latest_review_verdict"]
    payload["latest_simulation_record"] = detail["latest_simulation_record"]
    payload["next_action"] = detail["next_action"]
    payload["failure_reason"] = detail["failure_reason"]
    payload["waiting_reason"] = detail["waiting_reason"]
    payload["recoverability_hint"] = detail["recoverability_hint"]
    _emit_json(payload)


@run_app.command("status-detail")
def run_status_detail(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_status_detail(run_id)))


@run_app.command("summary")
def run_summary(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_summary(run_id)))


@run_app.command("simulation")
def run_simulation(ctx: typer.Context, run_id: str) -> None:
    report = _run_workflow_action(lambda: _service(ctx).get_run_simulation(run_id))
    _emit_json(report.model_dump(mode="json"))


@run_app.command("record-simulation")
def run_record_simulation(ctx: typer.Context, run_id: str) -> None:
    record = _run_workflow_action(lambda: _service(ctx).record_run_simulation(run_id))
    _emit_json(record.model_dump(mode="json"))


@run_app.command("simulations")
def run_simulations(ctx: typer.Context, run_id: str) -> None:
    records = _run_workflow_action(lambda: _service(ctx).list_simulation_records(run_id))
    _emit_json([record.model_dump(mode="json") for record in records])


@run_app.command("event-inspection")
def run_event_inspection(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_event_inspection(run_id)))


@run_app.command("audit-report")
def run_audit_report(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_audit_report(run_id)))


@run_app.command("replay-packet")
def run_replay_packet(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_replay_packet(run_id)))


@run_app.command("mutation-report")
def run_mutation_report(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_mutation_report(run_id)))


@run_app.command("orchestration")
def run_orchestration(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_orchestration(run_id)))


@run_app.command("plan-graph-status")
def run_plan_graph_status(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_orchestration_plan_graph(run_id)))


@run_app.command("policy-preview-status")
def run_policy_preview_status(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_capability_policy_preview(run_id)))


@run_app.command("operator-packet")
def run_operator_packet(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_operator_packet(run_id)))


@run_app.command("memory-candidates")
def run_memory_candidates(ctx: typer.Context, run_id: str) -> None:
    candidates = _run_workflow_action(lambda: _service(ctx).get_run_memory_candidates(run_id))
    _emit_json([candidate.model_dump(mode="json") for candidate in candidates])


@run_app.command("materialize-memory")
def run_materialize_memory(
    ctx: typer.Context,
    run_id: str,
    candidate_id: str = typer.Option(..., "--candidate-id"),
) -> None:
    memory_item = _run_workflow_action(lambda: _service(ctx).materialize_run_memory_candidate(run_id, candidate_id))
    _emit_json(memory_item.model_dump(mode="json"))


@run_app.command("memory-items")
def run_memory_items(ctx: typer.Context, run_id: str) -> None:
    items = _run_workflow_action(lambda: _service(ctx).list_memory_items(run_id=run_id))
    _emit_json([item.model_dump(mode="json") for item in items])


@run_app.command("claims")
def run_claims(ctx: typer.Context, run_id: str) -> None:
    claims = _run_workflow_action(lambda: _service(ctx).list_claims(run_id))
    _emit_json([claim.model_dump(mode="json") for claim in claims])


@run_app.command("leases")
def run_leases(ctx: typer.Context, run_id: str) -> None:
    leases = _run_workflow_action(lambda: _service(ctx).list_worker_leases(run_id))
    _emit_json([lease.model_dump(mode="json") for lease in leases])


@run_app.command("attempts")
def run_attempts(ctx: typer.Context, run_id: str) -> None:
    attempts = _run_workflow_action(lambda: _service(ctx).list_runtime_attempts(run_id))
    _emit_json([attempt.model_dump(mode="json") for attempt in attempts])


@run_app.command("snapshots")
def run_snapshots(ctx: typer.Context, run_id: str) -> None:
    snapshots = _run_workflow_action(lambda: _service(ctx).list_snapshots(run_id))
    _emit_json([snapshot.model_dump(mode="json") for snapshot in snapshots])


@run_app.command("budget")
def run_budget(ctx: typer.Context, run_id: str) -> None:
    detail = _run_workflow_action(lambda: _service(ctx).get_status_detail(run_id))
    _emit_json(
        {
            "run": detail["run"],
            "budget_ledger": detail["budget_ledger"],
            "budget_projection": detail["budget_projection"],
        }
    )


@run_app.command("inspect")
def run_inspect(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).inspect_run_state(run_id)))


@run_app.command("reconcile")
def run_reconcile(
    ctx: typer.Context,
    run_id: str,
    apply: bool = typer.Option(False, "--apply", help="Apply the selected repair action instead of only planning it."),
    action: Optional[str] = typer.Option(None, "--action", help="Explicit repair action override."),
) -> None:
    service = _service(ctx)
    if apply:
        _emit_json(_run_workflow_action(lambda: service.apply_run_repair(run_id, action=action)))
        return
    _emit_json(_run_workflow_action(lambda: service.reconcile_run(run_id)))


@run_app.command("timeline")
def run_timeline(ctx: typer.Context, run_id: str, as_json: bool = typer.Option(False, "--json")) -> None:
    timeline = _run_workflow_action(lambda: _service(ctx).get_timeline(run_id))
    if as_json:
        _emit_json([event.model_dump(mode="json") for event in timeline])
        return
    for event in timeline:
        typer.echo(f"{event.created_at.isoformat()} | {event.event_type} | {event.summary}")


@run_app.command("handoffs")
def run_handoffs(ctx: typer.Context, run_id: str) -> None:
    handoffs = _run_workflow_action(lambda: _service(ctx).list_handoffs(run_id))
    _emit_json([handoff.model_dump(mode="json") for handoff in handoffs])


@scheduler_app.command("cluster")
def scheduler_cluster(ctx: typer.Context) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).scheduler_authority_cluster.cluster_snapshot()))


@scheduler_app.command("lease")
def scheduler_lease(ctx: typer.Context, lease_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_scheduler_lease(lease_id)))


@task_app.command("evidence")
def task_evidence(ctx: typer.Context, runtime_task_id: str) -> None:
    evidence = _run_workflow_action(lambda: _service(ctx).get_task_evidence(runtime_task_id))
    _emit_json(evidence.model_dump(mode="json"))


@db_app.command("reset")
def db_reset(
    ctx: typer.Context,
    seed_presets: bool = typer.Option(True, "--seed-presets/--no-seed-presets", help="Seed bootstrap presets."),
) -> None:
    db_path = _db_path_from_context(ctx)
    _run_workflow_action(lambda: reset_db(db_path))
    migrate(db_path)
    seeded = []
    if seed_presets:
        seeded = [preset.preset_id for preset in PresetRepository(db_path).seed_defaults()]
    _emit_json({"db_path": db_path.as_posix(), "seeded_presets": seeded})


@db_app.command("migrate")
def db_migrate(ctx: typer.Context) -> None:
    db_path = _db_path_from_context(ctx)
    applied = migrate(db_path)
    status = get_migration_status(db_path)
    _emit_json(
        {
            "db_path": db_path.as_posix(),
            "applied": applied,
            "applied_count": len(applied),
            "available_count": status["available_count"],
            "pending_count": status["pending_count"],
            "up_to_date": status["up_to_date"],
        }
    )


@db_app.command("migration-status")
def db_migration_status(ctx: typer.Context) -> None:
    _emit_json(get_migration_status(_db_path_from_context(ctx)))


@db_app.command("workspace-path")
def db_workspace_path(
    label: str = typer.Option("workflow", "--label", help="Stable label for the workspace-scoped DB."),
) -> None:
    _emit_json({"db_path": workspace_scoped_db_path(label=label).resolve().as_posix(), "label": label})


@governance_app.command("tech-debt")
def governance_tech_debt(
    registry_path: Optional[str] = typer.Option(None, "--registry-path", help="Override tech-debt registry path."),
) -> None:
    _emit_json(build_tech_debt_report(registry_path))


@governance_app.command("review-policy")
def governance_review_policy(
    ctx: typer.Context,
    decision_table_path: Optional[str] = typer.Option(None, "--decision-table-path", help="Override decision table path."),
    registry_path: Optional[str] = typer.Option(None, "--registry-path", help="Override tech-debt registry path."),
) -> None:
    _emit_json(
        build_review_policy_report(
            db_path=_db_path_from_context(ctx),
            decision_table_path=decision_table_path,
            registry_path=registry_path,
        )
    )


@governance_app.command("metrics")
def governance_metrics(
    ctx: typer.Context,
    validation_report_path: Optional[str] = typer.Option(
        None,
        "--validation-report-path",
        help="Override offline validation report path.",
    ),
    decision_table_path: Optional[str] = typer.Option(None, "--decision-table-path", help="Override decision table path."),
    registry_path: Optional[str] = typer.Option(None, "--registry-path", help="Override tech-debt registry path."),
) -> None:
    _emit_json(
        build_governance_metrics_report(
            db_path=_db_path_from_context(ctx),
            validation_report_path=validation_report_path,
            decision_table_path=decision_table_path,
            registry_path=registry_path,
        )
    )


@governance_app.command("alerts")
def governance_alerts(
    ctx: typer.Context,
    validation_report_path: Optional[str] = typer.Option(
        None,
        "--validation-report-path",
        help="Override offline validation report path.",
    ),
    decision_table_path: Optional[str] = typer.Option(None, "--decision-table-path", help="Override decision table path."),
    registry_path: Optional[str] = typer.Option(None, "--registry-path", help="Override tech-debt registry path."),
) -> None:
    _emit_json(
        build_governance_alert_report(
            db_path=_db_path_from_context(ctx),
            validation_report_path=validation_report_path,
            decision_table_path=decision_table_path,
            registry_path=registry_path,
        )
    )


@governance_app.command("release-readiness")
def governance_release_readiness(
    ctx: typer.Context,
    validation_report_path: Optional[str] = typer.Option(
        None,
        "--validation-report-path",
        help="Override offline validation report path.",
    ),
    decision_table_path: Optional[str] = typer.Option(None, "--decision-table-path", help="Override decision table path."),
    registry_path: Optional[str] = typer.Option(None, "--registry-path", help="Override tech-debt registry path."),
) -> None:
    _emit_json(
        build_release_readiness_report(
            db_path=_db_path_from_context(ctx),
            validation_report_path=validation_report_path,
            decision_table_path=decision_table_path,
            registry_path=registry_path,
        )
    )


@governance_app.command("domain-pack")
def governance_domain_pack() -> None:
    _emit_json(build_domain_pack_platform_report())


@config_app.command("show")
def config_show(ctx: typer.Context) -> None:
    _emit_json(ctx.obj["effective_config"])


def run() -> None:
    app()


if __name__ == "__main__":
    run()
