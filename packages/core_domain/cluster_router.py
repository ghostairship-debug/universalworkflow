from __future__ import annotations

from packages.contracts import ExecutionClusterTemplate
from packages.core_domain.interaction_catalog import cluster_template_ids_for_preset


class ClusterRouter:
    def __init__(self, templates: list[ExecutionClusterTemplate]):
        self._template_index = {template.template_id: template for template in templates}

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
        research_markers = {"research", "investigate", "compare", "evaluate", "citation", "evidence", "analyze"}
        delivery_markers = {"project", "delivery", "implement", "integration", "feature", "refactor", "cluster"}
        if any(marker in normalized_goal for marker in research_markers):
            return ["research_cluster"] if "research_cluster" in self._template_index else []
        if any(marker in normalized_goal for marker in delivery_markers):
            return ["dev_cluster"] if "dev_cluster" in self._template_index else []
        return []

    def get_template(self, template_id: str) -> ExecutionClusterTemplate | None:
        return self._template_index.get(template_id)
