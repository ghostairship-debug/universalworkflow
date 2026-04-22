from __future__ import annotations

from packages.contracts import PresetSuggestion
from packages.contracts.models import PresetDefinition
from packages.core_domain.errors import PresetNotFoundError, PresetRequiredError
from packages.core_domain.presets import load_seed_presets


class PresetResolver:
    def __init__(self, presets: list[PresetDefinition] | None = None):
        self._presets = {preset.preset_id: preset for preset in (presets or load_seed_presets())}
        self._keyword_rules = {
            "feature_delivery": {
                "feature",
                "implement",
                "build",
                "deliver",
                "ship",
                "code",
                "artifact",
                "fix",
            },
            "optional_delivery": {
                "optional",
                "advisory",
                "non_blocking",
                "best_effort",
            },
            "research_spike": {
                "research",
                "investigate",
                "spike",
                "analyze",
                "explore",
                "compare",
                "evaluate",
                "study",
            },
            "advisory_delivery": {
                "advisory",
                "recommend",
                "quality",
                "check",
                "guardrail",
                "warn",
            },
            "guarded_delivery": {
                "approval",
                "approve",
                "guarded",
                "sensitive",
                "risk",
                "compliance",
            },
            "guarded_project_delivery": {
                "guarded",
                "project",
                "approval",
                "multi-role",
                "orchestration",
            },
        }

    def list_presets(self) -> list[PresetDefinition]:
        return list(self._presets.values())

    def suggest(self, goal_text: str) -> list[PresetSuggestion]:
        normalized = goal_text.lower()
        ranked: list[tuple[int, int, PresetSuggestion]] = []
        for index, preset in enumerate(self.list_presets()):
            matched_keywords = sorted(keyword for keyword in self._keyword_rules.get(preset.preset_id, set()) if keyword in normalized)
            if matched_keywords:
                score = len(matched_keywords) * 10
                reason = f"matched keywords: {', '.join(matched_keywords)}"
            else:
                score = 0
                reason = "default fallback ordering"
            ranked.append((score, index, PresetSuggestion(preset_id=preset.preset_id, score=score, reason=reason)))
        return [item for _, _, item in sorted(ranked, key=lambda item: (-item[0], item[1]))]

    def manual_select(self, preset_id: str | None) -> PresetDefinition:
        if not preset_id:
            raise PresetRequiredError("preset required")
        preset = self._presets.get(preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {preset_id}")
        return preset
