from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DOGFOOD_COVERAGE_SCHEMA = "m91_dogfood_coverage_v1"


def write_dogfood_coverage(
    *,
    milestone_id: str,
    phase_id: str,
    evidence_dir: str | Path,
    task_cards: list[dict[str, Any]],
    workflow_executed_task_cards: list[str] | None = None,
    codex_direct_task_cards: list[dict[str, str]] | None = None,
    route_evidence: list[str] | None = None,
    operator_packet: str | None = None,
    test_evidence: list[str] | None = None,
    exceptions: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    workflow_cards = list(workflow_executed_task_cards or [])
    direct_cards = list(codex_direct_task_cards or [])
    if not workflow_cards and not exceptions:
        exceptions = [
            {
                "type": "workflow_execution_not_used",
                "reason": "no workflow-executed task card was available for this phase",
            }
        ]
    missing_reasons = [item for item in direct_cards if not item.get("reason")]
    if missing_reasons:
        raise ValueError("codex_direct_task_cards require a reason")
    payload = {
        "schema_version": DOGFOOD_COVERAGE_SCHEMA,
        "milestone_id": milestone_id,
        "phase_id": phase_id,
        "task_cards": task_cards,
        "workflow_executed_task_cards": workflow_cards,
        "codex_direct_task_cards": direct_cards,
        "route_evidence": list(route_evidence or []),
        "operator_packet": operator_packet,
        "test_evidence": list(test_evidence or []),
        "exceptions": list(exceptions or []),
        "co_development_claim_allowed": bool(workflow_cards),
        "created_at": datetime.now(UTC).isoformat(),
    }
    root = Path(evidence_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"dogfood_coverage_{milestone_id.lower()}_{phase_id.lower()}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["evidence_path"] = path.as_posix()
    return payload
