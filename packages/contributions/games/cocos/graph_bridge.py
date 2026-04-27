from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contracts import GraphCheckpointRecord
from packages.runtime_langgraph.checkpoint_store import build_graph_repair_decision
from packages.runtime_langgraph.execution_kernel import run_artifact_only_graph
from packages.contributions.games.cocos.inspector import describe_cocos_delivery_modes, inspect_cocos_project_v2


COCOS_GRAPH_EVIDENCE_BRIDGE_SCHEMA = "m105_cocos_graph_evidence_bridge_v1"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def build_cocos_graph_evidence_bridge(
    *,
    workspace_root: str | Path,
    project_path: str | Path,
    evidence_dir: str | Path | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    project = Path(project_path).resolve()
    evidence_root = Path(evidence_dir).resolve() if evidence_dir else workspace / "state" / "cocos_graph_evidence_bridge"
    evidence_root.mkdir(parents=True, exist_ok=True)
    graph_payload = run_artifact_only_graph(
        goal=f"Cocos graph evidence bridge for {project.as_posix()}",
        workspace_root=workspace,
        evidence_dir=evidence_root / "graph",
        preset_id="advisory_delivery",
        phase_id="M105.4",
    )
    inspection = inspect_cocos_project_v2(project, evidence_dir=evidence_root / "inspection")
    delivery = describe_cocos_delivery_modes(project, evidence_dir=evidence_root / "delivery")
    checkpoint_payload = graph_payload.get("persistent_checkpoint") or {}
    repair_decision = None
    if checkpoint_payload:
        repair_decision = build_graph_repair_decision(
            checkpoint=GraphCheckpointRecord.model_validate(checkpoint_payload),
            failure_class=None if inspection.get("technical_smoke_go") else "cocos_project_inspection_failed",
        ).model_dump(mode="json")
    evidence_refs = [
        graph_payload.get("evidence_path"),
        graph_payload.get("graph_state_path"),
        inspection.get("evidence_path"),
        delivery.get("evidence_path"),
        (project / "cocos_runtime_config.json").as_posix() if (project / "cocos_runtime_config.json").exists() else None,
        (project / "cocos_game_e2e_manifest.json").as_posix() if (project / "cocos_game_e2e_manifest.json").exists() else None,
        (project / "playtest_evidence" / "cocos_playtest_result.json").as_posix()
        if (project / "playtest_evidence" / "cocos_playtest_result.json").exists()
        else None,
    ]
    payload = {
        "schema_version": COCOS_GRAPH_EVIDENCE_BRIDGE_SCHEMA,
        "created_at": _utc_now(),
        "workspace_root": workspace.as_posix(),
        "project_path": project.as_posix(),
        "status": "completed" if inspection.get("technical_smoke_go") else "blocked",
        "failure_class": None if inspection.get("technical_smoke_go") else "cocos_project_inspection_failed",
        "graph": {
            "run_id": graph_payload.get("run_id"),
            "thread_id": graph_payload.get("thread_id"),
            "attempt_id": graph_payload.get("attempt_id"),
            "evidence_path": graph_payload.get("evidence_path"),
            "graph_state_path": graph_payload.get("graph_state_path"),
            "persistent_checkpoint": checkpoint_payload,
            "repair_decision": repair_decision,
        },
        "inspection": inspection,
        "delivery": delivery,
        "evidence_refs": [ref for ref in evidence_refs if ref],
        "authority_note": "Graph evidence references Cocos facts but does not replace workflow receipt, lease, write_set, or player-visible GO/NO-GO gates.",
    }
    output = evidence_root / "cocos_graph_evidence_bridge.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["evidence_path"] = output.as_posix()
    return payload
