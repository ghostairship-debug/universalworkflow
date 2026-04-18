from __future__ import annotations

import json
from pathlib import Path

from packages.contracts import DomainPackDefinition, DomainPackResolution, PresetDefinition, TaskKind


DEFAULT_DOMAIN_PACK_SEED_PATH = Path("infra/seeds/domain_packs.json")
DOMAIN_PACK_RESOLUTION_ENV_KEY = "WORKFLOW_DOMAIN_PACK_RESOLUTION"


def load_seed_domain_packs(seed_path: Path | str = DEFAULT_DOMAIN_PACK_SEED_PATH) -> list[DomainPackDefinition]:
    path = Path(seed_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return [DomainPackDefinition.model_validate(item) for item in data]


class DomainPackRegistry:
    def __init__(self, domain_packs: list[DomainPackDefinition] | None = None):
        self._domain_packs = {
            domain_pack.domain_pack_id: domain_pack for domain_pack in (domain_packs or load_seed_domain_packs())
        }

    def list(self, *, enabled_only: bool = False) -> list[DomainPackDefinition]:
        domain_packs = list(self._domain_packs.values())
        if enabled_only:
            domain_packs = [domain_pack for domain_pack in domain_packs if domain_pack.enabled]
        return sorted(domain_packs, key=lambda item: item.domain_pack_id)

    def get(self, domain_pack_id: str) -> DomainPackDefinition | None:
        return self._domain_packs.get(domain_pack_id)

    def match(
        self,
        preset_id: str,
        *,
        task_kind: TaskKind | str | None = None,
    ) -> DomainPackDefinition | None:
        normalized_task_kind = TaskKind(task_kind) if task_kind is not None else None
        for domain_pack in self.list(enabled_only=True):
            if preset_id not in domain_pack.preset_ids:
                continue
            if normalized_task_kind is not None and domain_pack.task_kinds:
                if normalized_task_kind not in [TaskKind(task_kind_item) for task_kind_item in domain_pack.task_kinds]:
                    continue
            return domain_pack
        return None

    def resolve(
        self,
        preset_id: str,
        *,
        task_kind: TaskKind | str | None = None,
    ) -> DomainPackResolution | None:
        domain_pack = self.match(preset_id, task_kind=task_kind)
        if domain_pack is None:
            return None
        if task_kind is not None:
            matched_task_kind = TaskKind(task_kind)
        elif domain_pack.task_kinds:
            matched_task_kind = TaskKind(domain_pack.task_kinds[0])
        else:
            matched_task_kind = TaskKind.shell_exec
        return DomainPackResolution(
            domain_pack_id=domain_pack.domain_pack_id,
            name=domain_pack.name,
            description=domain_pack.description,
            matched_preset_id=preset_id,
            matched_task_kind=matched_task_kind,
            capability_exposure=domain_pack.capability_exposure,
            compile_projection=domain_pack.compile_projection,
            runtime_projection=domain_pack.runtime_projection,
        )

    def validate_catalog(
        self,
        presets: list[PresetDefinition],
        capability_routes: list[dict[str, str]],
    ) -> dict[str, object]:
        known_presets = {preset.preset_id: preset for preset in presets}
        available_routes = {(route["capability"], route["adapter_name"]) for route in capability_routes}
        issues: list[dict[str, object]] = []
        claimed_pairs: dict[tuple[str, str], str] = {}

        for domain_pack in self.list(enabled_only=True):
            if not domain_pack.match.preset_ids:
                issues.append(
                    {
                        "issue_code": "missing_preset_match",
                        "domain_pack_id": domain_pack.domain_pack_id,
                        "detail": "enabled domain pack has no matched presets",
                    }
                )
            for preset_id in domain_pack.match.preset_ids:
                preset = known_presets.get(preset_id)
                if preset is None:
                    issues.append(
                        {
                            "issue_code": "unknown_preset",
                            "domain_pack_id": domain_pack.domain_pack_id,
                            "preset_id": preset_id,
                            "detail": "matched preset does not exist in the known preset catalog",
                        }
                    )
                    continue
                allowed_task_kinds = {str(task_kind) for task_kind in preset.allowed_task_kinds}
                matched_task_kinds = (
                    [str(task_kind) for task_kind in domain_pack.match.task_kinds]
                    if domain_pack.match.task_kinds
                    else sorted(allowed_task_kinds)
                )
                for task_kind in matched_task_kinds:
                    if task_kind not in allowed_task_kinds:
                        issues.append(
                            {
                                "issue_code": "preset_task_kind_mismatch",
                                "domain_pack_id": domain_pack.domain_pack_id,
                                "preset_id": preset_id,
                                "task_kind": task_kind,
                                "detail": "domain pack matches a task kind that the preset does not allow",
                            }
                        )
                        continue
                    pair = (preset_id, task_kind)
                    conflicting_pack = claimed_pairs.get(pair)
                    if conflicting_pack is not None and conflicting_pack != domain_pack.domain_pack_id:
                        issues.append(
                            {
                                "issue_code": "enabled_overlap_conflict",
                                "domain_pack_id": domain_pack.domain_pack_id,
                                "conflicting_domain_pack_id": conflicting_pack,
                                "preset_id": preset_id,
                                "task_kind": task_kind,
                                "detail": "two enabled domain packs claim the same preset/task-kind pair",
                            }
                        )
                    else:
                        claimed_pairs[pair] = domain_pack.domain_pack_id
                    preferred_adapter = domain_pack.capability_exposure.preferred_adapter_name
                    if preferred_adapter is not None and (task_kind, preferred_adapter) not in available_routes:
                        issues.append(
                            {
                                "issue_code": "preferred_adapter_unavailable",
                                "domain_pack_id": domain_pack.domain_pack_id,
                                "preset_id": preset_id,
                                "task_kind": task_kind,
                                "adapter_name": preferred_adapter,
                                "detail": "preferred adapter is not available for the matched task kind",
                            }
                        )

        return {
            "passed": not issues,
            "issue_count": len(issues),
            "validated_pack_count": len(self.list()),
            "enabled_pack_count": len(self.list(enabled_only=True)),
            "issues": issues,
            "claimed_pairs": [
                {"preset_id": preset_id, "task_kind": task_kind, "domain_pack_id": domain_pack_id}
                for (preset_id, task_kind), domain_pack_id in sorted(claimed_pairs.items())
            ],
        }


def dump_domain_pack_resolution(resolution: DomainPackResolution | None) -> str:
    return json.dumps(resolution.model_dump(mode="json"), ensure_ascii=False) if resolution is not None else ""


def load_domain_pack_resolution(payload: str | None) -> DomainPackResolution | None:
    if payload is None or not payload.strip():
        return None
    return DomainPackResolution.model_validate(json.loads(payload))
