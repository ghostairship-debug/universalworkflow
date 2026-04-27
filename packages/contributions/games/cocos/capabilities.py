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

REQUIRED_PLAYER_VISIBLE_CHECKS = [
    "first_screen_visible",
    "no_debug_panel_as_primary_ui",
    "mobile_viewport_no_overflow",
    "core_loop_playable_3_minutes",
    "at_least_one_level_completion_path",
    "input_controls_visible_and_responsive",
    "audio_not_blocking_or_abrupt",
    "browser_console_no_fatal_error",
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
    manual_go = _valid_player_evidence(manual) and bool(manual.get("accepted_by_human"))
    missing_required = [
        check_name
        for check_name in REQUIRED_PLAYER_VISIBLE_CHECKS
        if not _valid_player_evidence(checks.get(check_name))
    ]
    automatic_go = not missing_required
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
    if missing_required and not manual_go:
        blockers.append("missing_player_visible_commercial_playable_evidence")
        blockers.extend(f"missing_{item}" for item in missing_required)
    return {
        "schema_version": "m98_cocos_commercial_readiness_layers_v1",
        "technical_smoke_go": bool(technical_smoke),
        "production_scaffold_go": bool(production_scaffold),
        "commercial_playable_go": commercial_playable_go,
        "player_visible_checks": checks,
        "player_visible_required_checks": list(REQUIRED_PLAYER_VISIBLE_CHECKS),
        "player_visible_evidence_schema": {
            "required_fields": ["status", "method", "evidence_path", "evidence_hash", "validator_version"],
            "passing_status": "pass",
            "boolean_only_checks_allowed": False,
        },
        "manual_player_evidence": manual,
        "judge_priority": "automatic_playwright_then_manual_fallback_default_no_go",
        "commercial_playable_blockers": blockers,
    }


def _valid_player_evidence(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    evidence_hash = value.get("evidence_hash") or value.get("hash")
    return bool(
        value.get("status") == "pass"
        and value.get("method")
        and value.get("evidence_path")
        and evidence_hash
        and value.get("validator_version")
    )
