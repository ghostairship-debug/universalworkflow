from __future__ import annotations

import json
import os
from pathlib import Path

from packages.contracts import ExecutionClusterTemplate
from packages.core_domain.interaction_catalog import cluster_template_ids_for_preset


CLUSTER_ROUTE_MARKERS_PATH = Path(__file__).resolve().parents[2] / "infra" / "seeds" / "cluster_route_markers.json"
DEFAULT_DYNAMIC_CLUSTER_ORDER = [
    "multimodal_cluster",
    "search_cluster",
    "design_cluster",
    "architecture_delivery_cluster",
    "dev_cluster",
    "review_cluster",
    "management_cluster",
]
DEFAULT_STATIC_CLUSTER_ORDER = [
    "architecture_delivery_cluster",
    "multimodal_cluster",
    "search_cluster",
    "design_cluster",
    "review_cluster",
    "management_cluster",
    "research_cluster",
    "dev_cluster",
]


def load_cluster_route_markers(path: Path | None = None) -> dict[str, set[str]]:
    marker_path = path or CLUSTER_ROUTE_MARKERS_PATH
    with marker_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return {
        str(template_id): {str(marker).lower() for marker in markers if str(marker).strip()}
        for template_id, markers in payload.items()
        if isinstance(markers, list)
    }


class ClusterRouter:
    def __init__(
        self,
        templates: list[ExecutionClusterTemplate],
        marker_catalog: dict[str, set[str]] | None = None,
    ):
        self._template_index = {template.template_id: template for template in templates}
        self._marker_catalog = marker_catalog or load_cluster_route_markers()

    def suggest_template_ids(
        self,
        *,
        goal: str,
        preset_id: str | None = None,
        preferred_template_ids: list[str] | None = None,
    ) -> list[str]:
        requested = [
            template_id
            for template_id in list(preferred_template_ids or [])
            if template_id in self._template_index
        ]
        if requested:
            return requested

        mapped_from_preset = [
            template_id
            for template_id in cluster_template_ids_for_preset(preset_id)
            if template_id in self._template_index
        ]
        if mapped_from_preset:
            return mapped_from_preset

        normalized_goal = goal.lower()
        if self._dynamic_routing_enabled():
            dynamic_candidates = self._matching_template_ids(normalized_goal, DEFAULT_DYNAMIC_CLUSTER_ORDER)
            if not dynamic_candidates and "research_cluster" in self._template_index:
                dynamic_candidates = self._matching_template_ids(normalized_goal, ["research_cluster"])
            if dynamic_candidates:
                return dynamic_candidates

        static_candidates = self._matching_template_ids(normalized_goal, DEFAULT_STATIC_CLUSTER_ORDER)
        return static_candidates[:1]

    def _matching_template_ids(self, normalized_goal: str, template_order: list[str]) -> list[str]:
        dynamic_candidates: list[str] = []
        for template_id in template_order:
            if template_id not in self._template_index:
                continue
            if any(marker in normalized_goal for marker in self._marker_catalog.get(template_id, set())):
                dynamic_candidates.append(template_id)
        unique_candidates: list[str] = []
        for template_id in dynamic_candidates:
            if template_id not in unique_candidates:
                unique_candidates.append(template_id)
        return unique_candidates

    def _dynamic_routing_enabled(self) -> bool:
        return str(os.getenv("WORKFLOW_DYNAMIC_CLUSTER_ROUTING_ENABLED") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
            "enabled",
        }

    def get_template(self, template_id: str) -> ExecutionClusterTemplate | None:
        return self._template_index.get(template_id)
