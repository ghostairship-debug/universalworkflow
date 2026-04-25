from __future__ import annotations

import os

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
        architecture_markers = {
            "architecture",
            "architect",
            "claude",
            "dogfood",
            "m41",
            "架构",
            "能力层",
            "自开发",
        }
        multimodal_markers = {
            "multimodal",
            "pdf",
            "image",
            "screenshot",
            "picture",
            "mmx",
            "vertex",
            "多模态",
            "图片",
            "截图",
            "设计稿",
            "文档图片",
        }
        search_markers = {
            "search",
            "web",
            "source",
            "citation",
            "evidence",
            "retrieval",
            "搜索",
            "检索",
            "资料",
            "来源",
            "引用",
            "信息检索",
        }
        design_markers = {
            "design",
            "ui",
            "ux",
            "frontend",
            "interface",
            "interaction",
            "设计",
            "界面",
            "交互",
            "视觉",
            "前端",
        }
        review_markers = {
            "review",
            "qa",
            "test",
            "regression",
            "quality",
            "验收",
            "审查",
            "测试",
            "回归",
            "质量",
        }
        management_markers = {
            "roadmap",
            "phase",
            "task",
            "milestone",
            "closeout",
            "管理",
            "计划",
            "任务卡",
            "收口",
            "里程碑",
        }
        research_markers = {"research", "investigate", "compare", "evaluate", "analyze", "研究", "调研", "评估", "分析"}
        delivery_markers = {
            "project",
            "delivery",
            "implement",
            "build",
            "integration",
            "feature",
            "refactor",
            "cluster",
            "game",
            "develop",
            "实现",
            "开发",
            "交付",
            "小游戏",
        }
        dynamic_enabled = str(os.getenv("WORKFLOW_DYNAMIC_CLUSTER_ROUTING_ENABLED") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
            "enabled",
        }
        if dynamic_enabled:
            dynamic_candidates: list[str] = []
            marker_map = [
                (multimodal_markers, "multimodal_cluster"),
                (search_markers, "search_cluster"),
                (design_markers, "design_cluster"),
                (architecture_markers, "architecture_delivery_cluster"),
                (delivery_markers, "dev_cluster"),
                (review_markers, "review_cluster"),
                (management_markers, "management_cluster"),
            ]
            for markers, template_id in marker_map:
                if template_id not in self._template_index:
                    continue
                if any(marker in normalized_goal for marker in markers):
                    dynamic_candidates.append(template_id)
            if not dynamic_candidates and "research_cluster" in self._template_index:
                if any(marker in normalized_goal for marker in research_markers):
                    dynamic_candidates.append("research_cluster")
            if dynamic_candidates:
                unique_candidates: list[str] = []
                for template_id in dynamic_candidates:
                    if template_id not in unique_candidates:
                        unique_candidates.append(template_id)
                return unique_candidates
        if any(marker in normalized_goal for marker in architecture_markers):
            return ["architecture_delivery_cluster"] if "architecture_delivery_cluster" in self._template_index else []
        if any(marker in normalized_goal for marker in multimodal_markers):
            return ["multimodal_cluster"] if "multimodal_cluster" in self._template_index else []
        if any(marker in normalized_goal for marker in search_markers):
            return ["search_cluster"] if "search_cluster" in self._template_index else []
        if any(marker in normalized_goal for marker in design_markers):
            return ["design_cluster"] if "design_cluster" in self._template_index else []
        if any(marker in normalized_goal for marker in review_markers):
            return ["review_cluster"] if "review_cluster" in self._template_index else []
        if any(marker in normalized_goal for marker in management_markers):
            return ["management_cluster"] if "management_cluster" in self._template_index else []
        if any(marker in normalized_goal for marker in research_markers):
            return ["research_cluster"] if "research_cluster" in self._template_index else []
        if any(marker in normalized_goal for marker in delivery_markers):
            return ["dev_cluster"] if "dev_cluster" in self._template_index else []
        return []

    def get_template(self, template_id: str) -> ExecutionClusterTemplate | None:
        return self._template_index.get(template_id)
