from __future__ import annotations

from pathlib import Path
from typing import Any


COCOS_CAPABILITY_SCHEMA = "m96_cocos_capability_contract_v2"
COCOS_CAPABILITIES = [
    "CocosProjectScaffold",
    "CocosSceneGraphBuilder",
    "CocosPrefabGenerator",
    "CocosComponentScriptGenerator",
    "CocosAssetImporter",
    "CocosBuildPackager",
    "CocosProjectInspector",
    "CocosPlaytestHarness",
    "CommercialReadinessJudge",
]


def cocos_capability_contracts(project_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_path).resolve().as_posix() if project_path is not None else None
    return {
        "schema_version": COCOS_CAPABILITY_SCHEMA,
        "project_path": root,
        "capabilities": [
            {
                "capability": name,
                "side_effect_boundary": "workspace_write" if name != "CommercialReadinessJudge" else "none",
                "authority": "workflow_gate_required_for_writes",
                "write_set": [root] if root and name != "CommercialReadinessJudge" else [],
                "evidence_required": True,
                "failure_class_prefix": name.lower(),
            }
            for name in COCOS_CAPABILITIES
        ],
    }


def judge_commercial_readiness_layers(
    *,
    technical_smoke: bool,
    production_scaffold: bool,
    player_visible_checks: dict[str, bool] | None = None,
    manual_player_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks = dict(player_visible_checks or {})
    manual = dict(manual_player_evidence or {})
    manual_go = bool(manual.get("accepted_by_human") and manual.get("evidence_path"))
    automatic_go = bool(checks) and all(bool(value) for value in checks.values())
    commercial_playable_go = bool(technical_smoke and production_scaffold and (automatic_go or manual_go))
    blockers = [
        key
        for key, value in {
            "technical_smoke": technical_smoke,
            "production_scaffold": production_scaffold,
            "player_visible_evidence": automatic_go or manual_go,
        }.items()
        if not value
    ]
    return {
        "schema_version": "m98_cocos_commercial_readiness_layers_v1",
        "technical_smoke_go": bool(technical_smoke),
        "production_scaffold_go": bool(production_scaffold),
        "commercial_playable_go": commercial_playable_go,
        "player_visible_checks": checks,
        "manual_player_evidence": manual,
        "judge_priority": "automatic_playwright_then_manual_fallback_default_no_go",
        "commercial_playable_blockers": blockers,
    }
