from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contributions.games.cocos.e2e import run_cocos_game_e2e
from packages.contributions.games.cocos.graph_bridge import build_cocos_graph_evidence_bridge
from packages.contributions.games.cocos.inspector import describe_cocos_delivery_modes, inspect_cocos_project_v2
from packages.contributions.games.cocos.player_validation import validate_cocos_player_visible_evidence


COCOS_SAMPLE_CLOSEOUT_SCHEMA = "m108_cocos_sample_closeout_v1"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def run_cocos_small_goal_sample_closeout(
    *,
    workspace_root: str | Path,
    output_dir: str | Path,
    creator_exe: str | Path,
    evidence_dir: str | Path | None = None,
    require_build: bool = False,
    require_playtest: bool = True,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    evidence_root = Path(evidence_dir).resolve() if evidence_dir else workspace / "state" / "m108_cocos_sample_closeout"
    evidence_root.mkdir(parents=True, exist_ok=True)
    project_dir = Path(output_dir).resolve()
    brief_path = evidence_root / "m108_small_goal_brief.pdf"
    brief_path.write_bytes(b"%PDF-1.4\n% M108 small goal: local stable 1010 block puzzle sample\n")
    e2e = run_cocos_game_e2e(
        pdf_path=brief_path,
        output_dir=project_dir,
        creator_exe=creator_exe,
        require_build=require_build,
        require_playtest=require_playtest,
        require_commercial=True,
        use_local_stable_assets=True,
    )
    inspection = inspect_cocos_project_v2(project_dir, evidence_dir=evidence_root / "inspection")
    delivery = describe_cocos_delivery_modes(project_dir, evidence_dir=evidence_root / "delivery")
    player_validation = validate_cocos_player_visible_evidence(
        playtest=e2e.get("playtest"),
        inspection=inspection,
        technical_smoke=bool(e2e.get("technical_smoke_go")),
        production_scaffold=bool(e2e.get("production_scaffold_go")),
        evidence_dir=evidence_root / "player_validation",
    )
    graph_bridge = build_cocos_graph_evidence_bridge(
        workspace_root=workspace,
        project_path=project_dir,
        evidence_dir=evidence_root / "graph_bridge",
    )
    claims = {
        "technical_smoke_go": bool(e2e.get("technical_smoke_go")),
        "production_scaffold_go": bool(e2e.get("production_scaffold_go")),
        "commercial_playable_go": bool(player_validation.get("commercial_playable_go")),
        "local_stable_assets_go": bool((e2e.get("commercial_assets") or {}).get("go_no_go") == "GO"),
        "web_mobile_build_go": bool((e2e.get("build") or {}).get("artifact_success")) if require_build else False,
        "browser_playtest_go": bool((e2e.get("playtest") or {}).get("passed")) if require_build and require_playtest else False,
    }
    honest_limits = []
    if not claims["commercial_playable_go"]:
        honest_limits.append("commercial_playable_go is false; this is a sample scaffold, not a commercial playable claim")
    if not claims["web_mobile_build_go"]:
        honest_limits.append("Web Mobile build was not proven in this closeout")
    if not claims["browser_playtest_go"]:
        honest_limits.append("browser player playtest was not proven in this closeout")
    payload = {
        "schema_version": COCOS_SAMPLE_CLOSEOUT_SCHEMA,
        "created_at": _utc_now(),
        "workspace_root": workspace.as_posix(),
        "project_path": project_dir.as_posix(),
        "brief_path": brief_path.as_posix(),
        "status": "completed",
        "go_no_go": "GO" if claims["commercial_playable_go"] else "NO-GO",
        "claims": claims,
        "honest_limits": honest_limits,
        "budget_review": {
            "cocos_budget_milestones": ["M105", "M106", "M107", "M108"],
            "auto_continue_to_m109": False,
            "requires_review_before_more_cocos_milestones": True,
        },
        "artifacts": {
            "e2e_manifest_path": e2e.get("manifest_path"),
            "runtime_config_path": e2e.get("runtime_config_path"),
            "inspection_evidence_path": inspection.get("evidence_path"),
            "delivery_evidence_path": delivery.get("evidence_path"),
            "player_validation_evidence_path": player_validation.get("evidence_path"),
            "graph_bridge_evidence_path": graph_bridge.get("evidence_path"),
        },
        "e2e": e2e,
        "inspection": inspection,
        "delivery": delivery,
        "player_validation": player_validation,
        "graph_bridge": graph_bridge,
    }
    output = evidence_root / "m108_cocos_sample_closeout.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["evidence_path"] = output.as_posix()
    return payload
