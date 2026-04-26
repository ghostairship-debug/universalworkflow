from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, status

from packages.core_domain.services import OrchestratorService


def build_catalog_router(service: OrchestratorService, effective_config: dict[str, Any]) -> APIRouter:
    router = APIRouter()

    @router.get("/presets")
    def list_presets() -> list[dict]:
        return [preset.model_dump(mode="json") for preset in service.list_presets()]

    @router.get("/domain-packs")
    def list_domain_packs() -> list[dict]:
        return [domain_pack.model_dump(mode="json") for domain_pack in service.list_domain_packs()]

    @router.get("/domain-packs/resolve")
    def resolve_domain_pack(preset_id: str, task_kind: str | None = None, adapter_name: str | None = None) -> dict:
        return service.preview_domain_pack_resolution(
            preset_id=preset_id,
            task_kind=task_kind,
            adapter_name=adapter_name,
        )

    @router.get("/domain-packs/validate")
    def validate_domain_packs() -> dict:
        return service.validate_domain_pack_catalog()

    @router.post("/domain-packs/{domain_pack_id}/skill-export", status_code=status.HTTP_201_CREATED)
    def export_domain_pack_skill(domain_pack_id: str, output_root: str = "state/skills") -> dict:
        return service.export_domain_pack_skill(domain_pack_id, output_root=output_root)

    @router.get("/capability-routes")
    def list_capability_routes() -> list[dict]:
        return service.list_capability_routes()

    @router.get("/capability-sources")
    def list_capability_sources() -> list[dict]:
        return service.list_capability_sources()

    @router.get("/capability-descriptors")
    def list_capability_descriptors() -> list[dict]:
        return service.list_capability_descriptors()

    @router.get("/capability-health")
    def list_capability_health(verified_only: bool = False) -> list[dict]:
        return service.list_capability_health(verified_only=verified_only)

    @router.get("/capability-routes/stats")
    def capability_route_stats(days: int = 30) -> dict:
        return service.get_capability_route_stats(days=days)

    @router.get("/cluster-routes/stats")
    def cluster_route_stats(days: int = 30) -> dict:
        return service.get_cluster_route_stats(days=days)

    @router.get("/capability-sources/mcp-profiles")
    def list_mcp_server_profiles() -> list[dict]:
        return service.list_mcp_server_profiles()

    @router.get("/worker-pools")
    def list_worker_pools() -> list[dict]:
        return service.list_worker_pool_profiles()

    @router.get("/capability-projections/preview")
    def preview_tool_projection(
        preset_id: str,
        task_kind: str | None = None,
        adapter_name: str | None = None,
        mcp_profile_id: list[str] | None = Query(default=None),
        mcp_tool_id: list[str] | None = Query(default=None),
    ) -> dict:
        return service.preview_tool_projection(
            preset_id=preset_id,
            task_kind=task_kind,
            adapter_name=adapter_name,
            mcp_profile_ids=mcp_profile_id,
            mcp_tool_ids=mcp_tool_id,
        )

    @router.get("/simulation/policies")
    def list_simulation_policies() -> list[dict]:
        return [policy.model_dump(mode="json") for policy in service.list_simulation_policies()]

    @router.get("/memory/namespaces")
    def list_memory_namespaces() -> list[dict]:
        return [namespace.model_dump(mode="json") for namespace in service.list_memory_namespaces()]

    @router.get("/memory/items")
    def list_memory_items(run_id: str | None = None, namespace_id: str | None = None) -> list[dict]:
        return [
            item.model_dump(mode="json")
            for item in service.list_memory_items(run_id=run_id, namespace_id=namespace_id)
        ]

    @router.get("/memory/retrieval-preview")
    def preview_memory_retrieval(
        preset_id: str | None = None,
        run_id: str | None = None,
        namespace_id: str | None = None,
        memory_item_id: list[str] = Query(default_factory=list),
        limit: int = 5,
    ) -> dict:
        return service.preview_memory_retrieval(
            preset_id=preset_id,
            run_id=run_id,
            namespace_id=namespace_id,
            memory_item_ids=memory_item_id or None,
            limit=limit,
        ).model_dump(mode="json")

    @router.get("/config/effective")
    def get_effective_config() -> dict[str, Any]:
        return effective_config

    return router
