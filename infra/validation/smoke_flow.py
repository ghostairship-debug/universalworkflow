from __future__ import annotations

from typing import Any

from infra.validation.common import *  # noqa: F401,F403

def validate_smoke_flow(env: dict[str, str], db_path: Path) -> dict[str, Any]:
    payload, _ = run_json_command(
        [sys.executable, "-m", "infra.scripts.manage", "--db-path", db_path.as_posix(), "smoke"],
        env,
    )
    return {
        "passed": payload.get("status") == "completed"
        and [item["domain_pack_id"] for item in payload.get("domain_packs", [])] == ["software_delivery_pack"]
        and payload.get("capability_routes", [])
        == [
            {"capability": "noop", "adapter_name": "noop", "adapter_class": "NoopAdapter"},
            {"capability": "shell_exec", "adapter_name": "shell", "adapter_class": "ShellAdapter"},
            {"capability": "shell_exec", "adapter_name": "codex", "adapter_class": "CodexAdapter"},
            {"capability": "shell_exec", "adapter_name": "opencode", "adapter_class": "OpenCodeAdapter"},
        ]
        and payload.get("auto_run", {}).get("status") == "completed"
        and payload.get("human_run", {}).get("status") == "completed"
        and payload.get("auto_run", {}).get("domain_pack", {}).get("domain_pack_id") == "software_delivery_pack"
        and payload.get("auto_run", {}).get("capability_resolution", {}).get("adapter_name") == "shell"
        and timeline_contains_required_events(payload.get("auto_run", {}).get("timeline_events", []), AUTO_TIMELINE)
        and timeline_contains_required_events(payload.get("human_run", {}).get("timeline_events", []), HUMAN_TIMELINE)
        and CLAIM_EVENTS.issubset(set(payload.get("auto_run", {}).get("timeline_events", [])))
        and CLAIM_EVENTS.issubset(set(payload.get("human_run", {}).get("timeline_events", [])))
        and LEASE_EVENTS.issubset(set(payload.get("auto_run", {}).get("timeline_events", [])))
        and LEASE_EVENTS.issubset(set(payload.get("human_run", {}).get("timeline_events", [])))
        and ATTEMPT_EVENTS.issubset(set(payload.get("auto_run", {}).get("timeline_events", [])))
        and ATTEMPT_EVENTS.issubset(set(payload.get("human_run", {}).get("timeline_events", [])))
        and [item["status"] for item in payload.get("auto_run", {}).get("claims", [])] == ["released"]
        and [item["status"] for item in payload.get("human_run", {}).get("claims", [])] == ["released"]
        and [item["status"] for item in payload.get("auto_run", {}).get("attempts", [])] == ["superseded", "completed"]
        and [item["status"] for item in payload.get("human_run", {}).get("attempts", [])] == ["superseded", "completed"]
        and [item["status"] for item in payload.get("auto_run", {}).get("worker_leases", [])] == ["released"]
        and [item["status"] for item in payload.get("human_run", {}).get("worker_leases", [])] == ["released"]
        and [item["stage"] for item in payload.get("auto_run", {}).get("snapshots", [])] == ["compiled", "completed"]
        and [item["stage"] for item in payload.get("human_run", {}).get("snapshots", [])]
        == ["compiled", "awaiting_review", "completed"]
        and payload.get("auto_run", {}).get("budget_projection", {}).get("remaining_retries") == 1
        and payload.get("human_run", {}).get("budget_projection", {}).get("remaining_retries") == 0,
        **payload,
    }
