from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.contracts import DomainPackDefinition


def export_domain_pack_skill_bundle(
    domain_pack: DomainPackDefinition,
    *,
    output_root: str | Path,
) -> Path:
    root = Path(output_root).resolve()
    skill_dir = root / domain_pack.domain_pack_id
    skill_dir.mkdir(parents=True, exist_ok=True)

    frontmatter = {
        "name": domain_pack.name,
        "description": domain_pack.description,
        "version": domain_pack.schema_version,
        "compatibility": {
            "runtime": "uawo-m8",
            "task_kinds": [str(item) for item in domain_pack.task_kinds],
            "preset_ids": list(domain_pack.preset_ids),
        },
        "resources": [
            "README.md",
            "skill.json",
        ],
    }
    readme = (
        "---\n"
        f"{json.dumps(frontmatter, ensure_ascii=False, indent=2)}\n"
        "---\n\n"
        f"# {domain_pack.name}\n\n"
        f"{domain_pack.description}\n\n"
        "## Progressive Resources\n\n"
        "- `skill.json`: canonical exported metadata from the internal domain pack.\n"
        "- This bundle is portability-oriented and does not replace the repository-native domain pack contract.\n"
    )
    (skill_dir / "README.md").write_text(readme, encoding="utf-8")
    (skill_dir / "skill.json").write_text(
        json.dumps(domain_pack.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return skill_dir


def exported_skill_manifest(skill_dir: str | Path) -> dict[str, Any]:
    root = Path(skill_dir)
    return json.loads((root / "skill.json").read_text(encoding="utf-8"))
