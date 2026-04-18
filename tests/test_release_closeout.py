from __future__ import annotations

from pathlib import Path

from infra.scripts.manage import run_demo


def test_manage_demo_projects_canonical_closeout_packet(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"

    payload = run_demo(db_path)

    assert payload["status"] == "completed"
    assert payload["capability_routes"] == [
        {"capability": "noop", "adapter_name": "noop", "adapter_class": "NoopAdapter"},
        {"capability": "shell_exec", "adapter_name": "shell", "adapter_class": "ShellAdapter"},
        {"capability": "shell_exec", "adapter_name": "opencode", "adapter_class": "OpenCodeAdapter"},
    ]
    assert [item["domain_pack_id"] for item in payload["domain_packs"]] == ["software_delivery_pack"]
    assert payload["paths"]["auto"]["status"] == "completed"
    assert payload["paths"]["auto"]["domain_pack"]["domain_pack_id"] == "software_delivery_pack"
    assert payload["paths"]["human_review"]["intermediate_status"] == "awaiting_review"
    assert payload["paths"]["human_review"]["status"] == "completed"
    assert payload["paths"]["recommended"]["intermediate_status"] == "awaiting_review"
    assert payload["paths"]["recommended"]["status"] == "completed"
    assert payload["paths"]["mandatory"]["intermediate_status"] == "awaiting_review"
    assert payload["paths"]["mandatory"]["status"] == "completed"
    assert payload["paths"]["noop"]["task_kind"] == "noop"
    assert payload["paths"]["noop"]["adapter_name"] == "noop"
    assert payload["paths"]["noop"]["status"] == "completed"
    assert Path(payload["paths"]["auto"]["artifact_path"]).exists()
