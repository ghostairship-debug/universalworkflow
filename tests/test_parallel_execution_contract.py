from __future__ import annotations

from packages.core_domain.parallel_execution_contract import (
    build_parallel_batch_plan,
    build_partial_failure_resume,
)


def test_parallel_batch_plan_allows_disjoint_members() -> None:
    plan = build_parallel_batch_plan(
        [
            {"run_id": "run_a", "mutation_mode": "artifact_only", "write_set": []},
            {"run_id": "run_b", "mutation_mode": "artifact_only", "write_set": []},
        ],
        requested_max_workers=2,
        dirty_paths=[],
    )

    assert plan["execution_mode"] == "parallel"
    assert plan["barrier_enabled"] is True
    assert plan["degraded_to_serial"] is False
    assert plan["effective_max_workers"] == 2


def test_parallel_batch_plan_degrades_write_set_conflict_to_serial() -> None:
    plan = build_parallel_batch_plan(
        [
            {"run_id": "run_a", "mutation_mode": "patch_apply", "write_set": ["packages/example.py"]},
            {"run_id": "run_b", "mutation_mode": "patch_apply", "write_set": [".\\packages\\example.py"]},
        ],
        requested_max_workers=2,
        dirty_paths=[],
    )

    assert plan["execution_mode"] == "serial_degraded"
    assert plan["barrier_enabled"] is False
    assert plan["degraded_to_serial"] is True
    assert "write_set_conflict" in plan["degraded_reasons"]
    assert plan["audit"]["write_set_conflicts"][0]["path"] == "packages/example.py"


def test_parallel_batch_plan_degrades_dirty_requested_write_set_to_serial() -> None:
    plan = build_parallel_batch_plan(
        [
            {"run_id": "run_a", "mutation_mode": "patch_apply", "write_set": ["packages/example.py"]},
            {"run_id": "run_b", "mutation_mode": "artifact_only", "write_set": []},
        ],
        requested_max_workers=2,
        dirty_paths=["packages/example.py", "unrelated.txt"],
    )

    assert plan["execution_mode"] == "serial_degraded"
    assert "dirty_write_set" in plan["degraded_reasons"]
    assert plan["audit"]["dirty_write_set_paths"] == ["packages/example.py"]


def test_partial_failure_resume_payload_names_failed_run_ids() -> None:
    payload = build_partial_failure_resume(
        run_ids=["run_a", "run_b", "run_c"],
        errors=[
            {"run_id": "run_b", "code": "parallel_barrier_broken"},
            {"run_id": "run_c", "code": "entity_not_found"},
        ],
        requested_max_workers=2,
    )

    assert payload["enabled"] is True
    assert payload["failed_run_ids"] == ["run_b", "run_c"]
    assert payload["recommended_max_workers"] == 2
    assert payload["resume_command"] == "workflowctl run batch-resume run_b run_c --max-workers 2"
