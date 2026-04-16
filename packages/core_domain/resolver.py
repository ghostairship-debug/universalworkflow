from __future__ import annotations

from packages.contracts.models import PresetDefinition
from packages.core_domain.errors import PresetNotFoundError, PresetRequiredError
from packages.core_domain.presets import load_seed_presets


class PresetResolver:
    def __init__(self, presets: list[PresetDefinition] | None = None):
        self._presets = {preset.preset_id: preset for preset in (presets or load_seed_presets())}

    def list_presets(self) -> list[PresetDefinition]:
        return list(self._presets.values())

    def manual_select(self, preset_id: str | None) -> PresetDefinition:
        if not preset_id:
            raise PresetRequiredError("preset required")
        preset = self._presets.get(preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {preset_id}")
        return preset
