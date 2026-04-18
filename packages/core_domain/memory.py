from __future__ import annotations

import json
from pathlib import Path

from packages.contracts import MemoryNamespace, MemoryRetrievalPreview


DEFAULT_MEMORY_NAMESPACE_SEED_PATH = Path("infra/seeds/memory_namespaces.json")
MEMORY_RETRIEVAL_PREVIEW_ENV_KEY = "WORKFLOW_MEMORY_RETRIEVAL_PREVIEW"


def load_seed_memory_namespaces(
    seed_path: Path | str = DEFAULT_MEMORY_NAMESPACE_SEED_PATH,
) -> list[MemoryNamespace]:
    path = Path(seed_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return [MemoryNamespace.model_validate(item) for item in data]


def dump_memory_retrieval_preview(preview: MemoryRetrievalPreview | None) -> str:
    if preview is None:
        return ""
    return json.dumps(preview.model_dump(mode="json"), ensure_ascii=False)


def load_memory_retrieval_preview(payload: str | None) -> MemoryRetrievalPreview | None:
    if not payload:
        return None
    return MemoryRetrievalPreview.model_validate(json.loads(payload))
