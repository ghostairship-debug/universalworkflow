from __future__ import annotations

import json
from pathlib import Path

from packages.contracts.models import PresetDefinition


DEFAULT_PRESET_SEED_PATH = Path("infra/seeds/presets.json")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_seed_presets(seed_path: Path | str = DEFAULT_PRESET_SEED_PATH) -> list[PresetDefinition]:
    path = Path(seed_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    data = json.loads(path.read_text(encoding="utf-8"))
    return [PresetDefinition.model_validate(item) for item in data]
