from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from apps.operator_cli.shared import (
    _db_path_from_context,
    _emit_json,
    _goal_from_task_card,
    _parse_key_value_pairs,
    _run_workflow_action,
    _service,
    _workspace_root_from_context,
)
from packages.core_domain.db import get_migration_status, migrate, reset_db, workspace_scoped_db_path
from packages.core_domain.governance import (
    build_domain_pack_platform_report,
    build_governance_alert_report,
    build_governance_metrics_report,
    build_release_readiness_report,
    build_review_policy_report,
    build_tech_debt_report,
)
from packages.core_domain.repositories import PresetRepository

preset_app = typer.Typer(help="Preset inspection commands.")
domain_pack_app = typer.Typer(help="Domain pack inspection commands.")
capability_app = typer.Typer(help="Capability registry inspection commands.")
simulation_app = typer.Typer(help="Simulation policy commands.")
simulation_policy_app = typer.Typer(help="Simulation policy catalog commands.")
memory_app = typer.Typer(help="Memory-plane inspection commands.")
memory_namespace_app = typer.Typer(help="Memory namespace inspection commands.")
memory_item_app = typer.Typer(help="Persistent memory item commands.")

memory_app.add_typer(memory_namespace_app, name="namespace")
memory_app.add_typer(memory_item_app, name="item")
simulation_app.add_typer(simulation_policy_app, name="policy")

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


@capability_app.command("probe")
def capability_probe(
    ctx: typer.Context,
    provider: str = typer.Option("all", "--provider", help="Provider: all, shell, codex, opencode, mmx, vertex, claude, or langchain."),
    require_live: bool = typer.Option(False, "--require-live", help="Run real provider smoke tests instead of descriptor-only checks."),
    evidence_dir: Optional[Path] = typer.Option(None, "--evidence-dir", help="Directory for probe artifacts."),
) -> None:
    from packages.core_domain.capability_probe import run_capability_probes

    workspace_root = _workspace_root_from_context(ctx)
    resolved_evidence_dir = evidence_dir or workspace_root / "state" / "capability_probes"
    payload = run_capability_probes(
        provider=provider,
        workspace_root=workspace_root,
        evidence_dir=resolved_evidence_dir,
        require_live=require_live,
        db_path=_db_path_from_context(ctx),
    )
    _emit_json(payload)
    if require_live and payload["overall_status"] == "blocked":
        raise typer.Exit(code=1)


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
