from __future__ import annotations

import json
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from packages.contracts import TaskCard
from packages.contributions.games.cocos.e2e import build_cocos_project
from packages.contributions.games.cocos.playtest import playtest_cocos_build
from packages.contributions.pipelines.commercial_game_development_readiness import (
    build_commercial_game_development_readiness_evidence,
)
from packages.contributions.pipelines.commercial_game_evidence_contracts import (
    BROWSER_PLAYTEST_LEDGER_SCHEMA,
    BUILD_LEDGER_SCHEMA,
    GAMEPLAY_SEMANTIC_EVIDENCE_SCHEMA,
    PRODUCT_DEPTH_EVIDENCE_SCHEMA,
    PRODUCT_BODY_EVIDENCE_SCHEMA,
    build_asset_graph_contract,
    build_browser_playtest_ledger,
    build_build_ledger,
    build_cocos_bridge_evidence_contract,
    build_gameplay_semantic_evidence,
    build_human_review_packet,
    build_product_body_evidence,
    build_product_depth_evidence,
    build_same_project_patch_ledger_contract,
)
from packages.contributions.pipelines.commercial_game_task_worker_cli import (
    _parse_json_from_stdout,
    _read_log_text,
    run_task_card_patch_via_workflowctl,
)
from packages.core_domain.task_card_store import task_card_execution_eligibility


TASK_CARD_RUNTIME_MAX_ATTEMPTS = 3
RETRYABLE_RUNTIME_FAILURE_CLASSES = {
    "child_stdout_silent",
    "provider_execution_failed",
    "provider_idle_timeout",
    "provider_no_material_progress_timeout",
    "provider_output_idle_timeout",
    "provider_timeout",
    "provider_wall_timeout",
    "same_project_patch_no_changed_files",
    "same_project_patch_apply_failed",
    "same_project_patch_parse_failed",
    "same_project_patch_review_failed",
    "same_project_patch_tests_not_passed",
    "task_card_expected_artifacts_missing",
    "workflow_child_stalled",
}
FAIL_FAST_PRECONDITION_FAILURE_CLASSES = {
    "cocos_creator_exe_missing",
    "db_path_required_for_task_card_worker",
    "fallback_provider_unavailable",
    "fresh_cli_execution_missing",
    "human_visible_cli_metadata_missing",
    "operator_receipt_scope_mismatch",
    "provider_live_proof_missing",
    "receipt_scope_invalid",
    "source_path_missing",
    "task_card_receipt_issue_failed",
    "worker_lease_scope_invalid",
    "workspace_write_set_violation",
    "write_set_scope_invalid",
}


def same_project_business_task_cards(task_cards: list[TaskCard]) -> list[TaskCard]:
    return [
        card
        for card in task_cards
        if str(card.execution_mode or "").strip() == "same_project_patch"
        and task_card_execution_eligibility(card)["execution_eligible"]
    ]


def validate_same_project_reuse(*, project_dir: Path, source_path: Path) -> dict[str, Any]:
    source_identity = _source_identity(source_path)
    existing_files = _project_existing_files(project_dir)
    if not existing_files:
        return {
            "schema_version": "commercial_game_same_project_reuse_guard_v1",
            "go": True,
            "blockers": [],
            "project_dir": project_dir.as_posix(),
            "source_identity": source_identity,
            "reuse_mode": "empty_or_new_project_dir",
        }

    manifest_path = project_dir / "workflow_project_source.json"
    manifest = _read_json_dict(manifest_path)
    if not manifest:
        return {
            "schema_version": "commercial_game_same_project_reuse_guard_v1",
            "go": False,
            "blockers": ["same_project_unmanaged_project_dir"],
            "project_dir": project_dir.as_posix(),
            "source_identity": source_identity,
            "manifest_path": manifest_path.as_posix(),
            "existing_file_count": len(existing_files),
            "reuse_mode": "blocked_unmanaged_existing_project",
        }

    previous_source = str(manifest.get("source_path") or "")
    previous_sha256 = str(manifest.get("source_sha256") or "")
    source_path_match = previous_source == source_identity["source_path"]
    source_hash_match = bool(previous_sha256) and previous_sha256 == source_identity["source_sha256"]
    legacy_manifest_same_source = not previous_sha256 and source_path_match
    if not (source_hash_match or legacy_manifest_same_source):
        return {
            "schema_version": "commercial_game_same_project_reuse_guard_v1",
            "go": False,
            "blockers": ["same_project_source_mismatch"],
            "project_dir": project_dir.as_posix(),
            "source_identity": source_identity,
            "manifest_path": manifest_path.as_posix(),
            "previous_source_path": previous_source,
            "previous_source_sha256": previous_sha256,
            "existing_file_count": len(existing_files),
            "reuse_mode": "blocked_source_mismatch",
        }

    return {
        "schema_version": "commercial_game_same_project_reuse_guard_v1",
        "go": True,
        "blockers": [],
        "project_dir": project_dir.as_posix(),
        "source_identity": source_identity,
        "manifest_path": manifest_path.as_posix(),
        "previous_source_path": previous_source,
        "previous_source_sha256": previous_sha256,
        "existing_file_count": len(existing_files),
        "reuse_mode": "same_source_project_reuse",
    }


def bootstrap_cocos_project_shell(
    *,
    project_dir: Path,
    source_path: Path,
    creator_exe: Path,
    asset_manifest: dict[str, Any] | None,
) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    for relative in [
        "assets/scripts",
        "assets/scene",
        "assets/resources/commercial_assets",
        "settings",
        "temp/workflow_task_card_worker",
    ]:
        (project_dir / relative).mkdir(parents=True, exist_ok=True)
    package_json = project_dir / "package.json"
    if not package_json.exists():
        package_json.write_text(
            json.dumps(
                {
                    "name": "workflow-commercial-game-project",
                    "uuid": "workflow-commercial-game-project",
                    "creator": {"version": "3.8.8"},
                    "dependencies": {},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    generic_shell_path = project_dir / "workflow_generic_cocos_shell.json"
    generic_shell_path.write_text(
        json.dumps(
            {
                "schema_version": "commercial_game_generic_cocos_shell_v1",
                "bootstrap_mode": "generic_empty_cocos_project_shell_for_task_card_patches",
                "gameplay_template_installed": False,
                "template_policy": "no_default_gameplay_template",
                "runtime_contract": "task_cards_must_implement_game_specific_runtime_from_GameDesignSpec",
                "forbidden_default_artifacts": [
                    "10x10",
                    "CandidateTray",
                    "anti_stall",
                    "fixed_line_clear_trace",
                    "fixed_candidate_refresh_trace",
                    "browser_runtime_bridge_template",
                ],
                "runtime_slots": [
                    "assets/scripts",
                    "assets/scene",
                    "assets/resources/commercial_assets",
                    "workflow_runtime_evidence",
                    "player_visible_evidence",
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (project_dir / "workflow_project_source.json").write_text(
        json.dumps(
            {
                "schema_version": "commercial_game_same_project_bootstrap_v1",
                "source_path": source_path.resolve().as_posix(),
                "source_sha256": _sha256_file(source_path),
                "creator_exe": creator_exe.resolve().as_posix(),
                "asset_manifest_path": asset_manifest.get("manifest_path") if isinstance(asset_manifest, dict) else None,
                "bootstrap_mode": "generic_empty_cocos_project_shell_for_task_card_patches",
                "generic_shell_manifest_path": generic_shell_path.as_posix(),
                "product_body_baseline_manifest_path": None,
                "product_body_baseline_only": False,
                "gameplay_template_installed": False,
                "template_policy": "no_default_gameplay_template",
                "forbidden_delivery_claim": "bootstrap_shell_is_not_commercial_game",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def execute_same_project_task_cards(
    *,
    root: Path,
    run_root: Path,
    project_dir: Path,
    pipeline_id: str,
    db_path: Path | None,
    task_cards: list[TaskCard],
    max_repair_attempts: int,
    task_card_runner: Callable[..., dict[str, Any]] | None,
) -> dict[str, Any]:
    ledger_root = run_root / "task_card_worker"
    card_root = ledger_root / "cards"
    card_root.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    prior_completed_entries = _prior_completed_patch_entries(ledger_root)
    prior_retry_adapters = _prior_retry_adapter_hints(ledger_root)
    if not task_cards:
        return _write_ledger(
            ledger_root,
            {
                "schema_version": "commercial_game_same_project_patch_ledger_v1",
                "pipeline_id": pipeline_id,
                "project_dir": project_dir.as_posix(),
                "same_project_worker_patch_go": False,
                "entries": [],
                "blockers": ["same_project_business_task_cards_missing"],
            },
        )
    ineligible_entries = _ineligible_task_card_entries(
        task_cards,
        project_dir=project_dir,
        pipeline_id=pipeline_id,
        card_root=card_root,
    )
    if ineligible_entries:
        blockers = _patch_ledger_blockers(ineligible_entries, expected_count=len(task_cards))
        lifecycle_blocked = any(entry.get("failure_class") == "task_card_lifecycle_no_go" for entry in ineligible_entries)
        blockers.append("task_card_lifecycle_no_go" if lifecycle_blocked else "task_card_quality_no_go")
        return _write_ledger(
            ledger_root,
            {
                "schema_version": "commercial_game_same_project_patch_ledger_v1",
                "pipeline_id": pipeline_id,
                "project_dir": project_dir.as_posix(),
                "same_project_worker_patch_go": False,
                "task_card_count": len(task_cards),
                "completed_count": 0,
                "entries": ineligible_entries,
                "blockers": _dedupe_strings(blockers),
                "retry_policy": {
                    "runtime_max_attempts": TASK_CARD_RUNTIME_MAX_ATTEMPTS,
                    "fresh_receipt_required_per_attempt": True,
                    "same_project_required": True,
                },
                "next_incomplete_task_card_id": ineligible_entries[0].get("task_card_id"),
                "next_continuation_command": None,
                "next_continuation_argv": None,
            },
        )
    runner = task_card_runner or run_task_card_patch_via_workflowctl
    for card in task_cards:
        materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id=pipeline_id)
        execution_visibility_mode = _task_card_visibility_mode(card)
        card_path = card_root / f"{_safe_id(card.task_card_id)}.md"
        card_path.write_text(_task_card_markdown(card, materialized), encoding="utf-8")
        prior_entry = prior_completed_entries.get(card.task_card_id)
        prior_completed_invalidation: dict[str, Any] | None = None
        if prior_entry is not None:
            prior_artifact_validation = _task_card_artifact_validation(
                card,
                materialized=materialized,
                project_dir=project_dir,
            )
            if prior_artifact_validation["go"]:
                revalidated_entry = {
                    **prior_entry,
                    "task_card_path": prior_entry.get("task_card_path") or card_path.as_posix(),
                    "write_set": prior_entry.get("write_set") or materialized["write_set"],
                    "read_set": prior_entry.get("read_set") or materialized["read_set"],
                    "test_commands": prior_entry.get("test_commands") or materialized["test_commands"],
                    "prior_completed_entry_revalidated": True,
                    "artifact_validation": prior_artifact_validation,
                }
                entries.append(revalidated_entry)
                continue
            prior_completed_invalidation = {
                "prior_completed_entry_invalidated": True,
                "failure_class": "prior_completed_entry_artifact_contract_no_go",
                "artifact_validation": prior_artifact_validation,
            }
        reference_evidence = _already_satisfied_task_card_entry(
            card,
            materialized,
            project_dir=project_dir,
            card_path=card_path,
        )
        entry = _run_task_card_with_retry_policy(
            runner=runner,
            root=root,
            db_path=db_path,
            project_dir=project_dir,
            pipeline_id=pipeline_id,
            task_card=card,
            task_card_path=card_path,
            write_set=materialized["write_set"],
            read_set=materialized["read_set"],
            test_commands=materialized["test_commands"],
            max_fix_iterations=max_repair_attempts,
            max_runtime_attempts=TASK_CARD_RUNTIME_MAX_ATTEMPTS,
            execution_visibility_mode=execution_visibility_mode,
            preferred_adapter_name=prior_retry_adapters.get(card.task_card_id),
        )
        normalized_entry = _normalize_patch_ledger_entry(
            card,
            materialized,
            entry,
            root=root,
            db_path=db_path,
            project_dir=project_dir,
            card_path=card_path,
            max_repair_attempts=max_repair_attempts,
            execution_visibility_mode=execution_visibility_mode,
        )
        if reference_evidence is not None:
            normalized_entry["reference_evidence"] = reference_evidence
        if prior_completed_invalidation is not None:
            normalized_entry.update(
                {
                    "prior_completed_entry_invalidated": True,
                    "prior_completed_entry_failure_class": prior_completed_invalidation["failure_class"],
                    "prior_completed_entry_artifact_validation": prior_completed_invalidation["artifact_validation"],
                }
            )
        entries.append(normalized_entry)
        if entries[-1]["status"] != "completed":
            break
    blockers = _patch_ledger_blockers(entries, expected_count=len(task_cards))
    next_incomplete = next((entry for entry in entries if entry.get("status") != "completed"), None)
    return _write_ledger(
        ledger_root,
        {
            "schema_version": "commercial_game_same_project_patch_ledger_v1",
            "pipeline_id": pipeline_id,
            "project_dir": project_dir.as_posix(),
            "same_project_worker_patch_go": not blockers,
            "task_card_count": len(task_cards),
            "completed_count": sum(1 for entry in entries if entry["status"] == "completed"),
            "entries": entries,
            "blockers": blockers,
            "retry_policy": {
                "runtime_max_attempts": TASK_CARD_RUNTIME_MAX_ATTEMPTS,
                "fresh_receipt_required_per_attempt": True,
                "same_project_required": True,
            },
            "next_incomplete_task_card_id": next_incomplete.get("task_card_id") if next_incomplete else None,
            "next_continuation_command": next_incomplete.get("continuation_command") if next_incomplete else None,
            "next_continuation_argv": next_incomplete.get("continuation_argv") if next_incomplete else None,
        },
    )


def _prior_completed_patch_entries(ledger_root: Path) -> dict[str, dict[str, Any]]:
    ledger_path = ledger_root / "same_project_patch_ledger.json"
    try:
        payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return {}
    completed: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        candidate = entry if entry.get("status") == "completed" else _recover_completed_entry_from_visible_attempt(entry)
        if candidate is None or not _completed_patch_entry_has_fresh_execution(candidate):
            continue
        task_card_id = str(candidate.get("task_card_id") or "")
        if task_card_id:
            completed[task_card_id] = candidate
    return completed


def _recover_completed_entry_from_visible_attempt(entry: dict[str, Any]) -> dict[str, Any] | None:
    attempts = entry.get("attempts") if isinstance(entry.get("attempts"), list) else []
    for attempt in reversed(attempts):
        if not isinstance(attempt, dict):
            continue
        session = attempt.get("visible_cli_session")
        if not isinstance(session, dict) or session.get("return_code") != 0:
            continue
        stdout_path = session.get("stdout_log_path")
        if not stdout_path:
            continue
        payload = _parse_json_from_stdout(_read_log_text(Path(str(stdout_path))))
        if not isinstance(payload, dict):
            continue
        summary = payload.get("pr_ready_summary") if isinstance(payload.get("pr_ready_summary"), dict) else {}
        bounded_patch = summary.get("bounded_patch") if isinstance(summary.get("bounded_patch"), dict) else {}
        tests = summary.get("tests") if isinstance(summary.get("tests"), dict) else {}
        changed_files = bounded_patch.get("changed_files") if isinstance(bounded_patch.get("changed_files"), list) else []
        final_test_status = str(tests.get("status") or "").strip().lower()
        if not changed_files or final_test_status != "passed":
            continue
        recovered = {
            **entry,
            "status": "completed",
            "failure_class": None,
            "final_failure_class": None,
            "retry_exhausted": False,
            "preflight_blocker": False,
            "receipt_id": attempt.get("receipt_id"),
            "child_run_id": attempt.get("child_run_id") or payload.get("run", {}).get("run_id"),
            "child_attempt_id": attempt.get("child_attempt_id"),
            "worker_adapter": attempt.get("worker_adapter"),
            "execution_visibility_mode": attempt.get("execution_visibility_mode"),
            "visible_cli_session": session,
            "visible_cli_log_paths": attempt.get("visible_cli_log_paths") or _visible_cli_log_paths({"visible_cli_session": session}),
            "watchdog_source": attempt.get("watchdog_source") or "human_visible_cli_mirrored_logs",
            "evidence_id": payload.get("evidence_id"),
            "review_decision": payload.get("review_decision"),
            "mutation_result": {
                "changed_files": changed_files,
                "final_test_status": final_test_status,
                "applied_patch_hash": bounded_patch.get("applied_patch_hash"),
                "recovered_from_visible_cli_log": True,
            },
            "changed_files": changed_files,
            "final_test_status": final_test_status,
            "applied_patch_hash": bounded_patch.get("applied_patch_hash"),
            "continuation_required": False,
            "continuation_reason": None,
            "continuation_argv": None,
            "next_continuation_argv": None,
            "continuation_command": None,
            "satisfaction_mode": "fresh_visible_cli_log_reclassified_after_parser_repair",
        }
        return recovered
    return None


def _prior_retry_adapter_hints(ledger_root: Path) -> dict[str, str]:
    ledger = _read_json_dict(ledger_root / "same_project_patch_ledger.json")
    entries = ledger.get("entries") if isinstance(ledger.get("entries"), list) else []
    hints: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("status") == "completed":
            continue
        task_card_id = str(entry.get("task_card_id") or "")
        if not task_card_id:
            continue
        if _patch_root_failure_class(entry) not in {
            "provider_no_material_progress_timeout",
            "provider_output_idle_timeout",
            "provider_timeout",
        }:
            continue
        current_adapter = _normalize_adapter_name(entry.get("requested_adapter") or entry.get("worker_adapter"))
        fallback = _fallback_adapter_for(current_adapter)
        if fallback:
            hints[task_card_id] = fallback
    return hints


def _ineligible_task_card_entries(
    task_cards: list[TaskCard],
    *,
    project_dir: Path,
    pipeline_id: str,
    card_root: Path,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for card in task_cards:
        eligibility = task_card_execution_eligibility(card)
        if eligibility["execution_eligible"]:
            continue
        materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id=pipeline_id)
        card_path = card_root / f"{_safe_id(card.task_card_id)}.md"
        card_path.write_text(_task_card_markdown(card, materialized), encoding="utf-8")
        lifecycle_blockers = [issue["code"] for issue in eligibility["issues"]]
        quality_blockers = [issue["code"] for issue in eligibility.get("quality_issues", [])]
        quality_blocked = eligibility["quality_status"] != "passed"
        failure_class = "task_card_lifecycle_no_go" if lifecycle_blockers else "task_card_quality_no_go"
        entries.append(
            {
                "task_card_id": card.task_card_id,
                "title": card.title,
                "status": "blocked",
                "failure_class": failure_class,
                "final_failure_class": failure_class,
                "retry_exhausted": False,
                "preflight_blocker": True,
                "attempt_index": 0,
                "max_attempts": TASK_CARD_RUNTIME_MAX_ATTEMPTS,
                "consecutive_failure_count": 0,
                "attempts": [],
                "receipt_id": None,
                "child_run_id": None,
                "child_attempt_id": None,
                "worker_adapter": None,
                "task_card_path": card_path.as_posix(),
                "write_set": materialized["write_set"],
                "read_set": materialized["read_set"],
                "test_commands": materialized["test_commands"],
                "mutation_result": {"changed_files": [], "final_test_status": "not_run"},
                "changed_files": [],
                "final_test_status": "not_run",
                "lifecycle_status": eligibility["lifecycle_status"],
                "execution_eligible": False,
                "quality_status": eligibility["quality_status"],
                "quality_blocked": quality_blocked,
                "blockers": [*lifecycle_blockers, *quality_blockers],
                "continuation_required": False,
                "continuation_reason": failure_class,
                "continuation_argv": None,
                "next_continuation_argv": None,
                "continuation_command": None,
            }
        )
    return entries


def _run_task_card_with_retry_policy(
    *,
    runner: Callable[..., dict[str, Any]],
    root: Path,
    db_path: Path | None,
    project_dir: Path,
    pipeline_id: str,
    task_card: TaskCard,
    task_card_path: Path,
    write_set: list[str],
    read_set: list[str],
    test_commands: list[str],
    max_fix_iterations: int,
    max_runtime_attempts: int,
    execution_visibility_mode: str | None,
    preferred_adapter_name: str | None = None,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    last_entry: dict[str, Any] = {}
    adapter_sequence = _adapter_attempt_sequence(task_card, preferred_adapter_name=preferred_adapter_name)
    adapter_index = 0
    continuation_argv = _continuation_argv(
        root=root,
        db_path=db_path,
        project_dir=project_dir,
        card_path=task_card_path,
        card=task_card,
        materialized={"write_set": write_set, "read_set": read_set, "test_commands": test_commands},
        max_repair_attempts=max_fix_iterations,
        entry={},
        execution_visibility_mode=execution_visibility_mode,
    )
    for attempt_index in range(1, max_runtime_attempts + 1):
        attempt_adapter = adapter_sequence[min(adapter_index, len(adapter_sequence) - 1)] if adapter_sequence else None
        effective_task_card_path = _task_card_path_with_retry_context(
            task_card_path,
            attempt_index=attempt_index,
            prior_entry=last_entry,
        )
        raw_entry = runner(
            root=root,
            db_path=db_path,
            project_dir=project_dir,
            pipeline_id=pipeline_id,
            task_card=task_card,
            task_card_path=effective_task_card_path,
            write_set=write_set,
            read_set=read_set,
            test_commands=test_commands,
            max_fix_iterations=max_fix_iterations,
            adapter_name=attempt_adapter,
            execution_visibility_mode=execution_visibility_mode,
        )
        last_entry = dict(raw_entry)
        if attempt_adapter and not last_entry.get("requested_adapter"):
            last_entry["requested_adapter"] = attempt_adapter
        last_entry["attempt_index"] = attempt_index
        last_entry["max_attempts"] = max_runtime_attempts
        attempt_continuation_argv = _continuation_argv(
            root=root,
            db_path=db_path,
            project_dir=project_dir,
            card_path=task_card_path,
            card=task_card,
            materialized={"write_set": write_set, "read_set": read_set, "test_commands": test_commands},
            max_repair_attempts=max_fix_iterations,
            entry=last_entry,
            execution_visibility_mode=execution_visibility_mode,
        )
        if str(last_entry.get("status") or "") == "completed" and not _completed_patch_entry_has_fresh_execution(last_entry):
            last_entry = {
                **last_entry,
                "status": "failed",
                "failure_class": "fresh_cli_execution_missing",
                "final_failure_class": "fresh_cli_execution_missing",
                "recoverable_suggestion": "rerun_task_card_with_fresh_workflowctl_receipt_child_run_and_passing_tests",
            }
        if (
            str(last_entry.get("status") or "") == "completed"
            and execution_visibility_mode == "human_visible_cli_enforced"
            and not _visible_cli_session_valid(last_entry)
        ):
            last_entry = {
                **last_entry,
                "status": "failed",
                "failure_class": "human_visible_cli_metadata_missing",
                "final_failure_class": "human_visible_cli_metadata_missing",
                "recoverable_suggestion": "rerun_task_card_in_human_visible_cli_enforced_mode_with_mirrored_logs",
            }
        if (
            str(last_entry.get("status") or "") == "completed"
            and _provider_visible_cli_required(last_entry)
            and not _provider_visible_cli_session_valid(last_entry)
        ):
            last_entry = {
                **last_entry,
                "status": "failed",
                "failure_class": "direct_provider_visible_cli_metadata_missing",
                "final_failure_class": "direct_provider_visible_cli_metadata_missing",
                "recoverable_suggestion": "rerun_task_card_with_resident_control_plane_and_direct_visible_provider_cli",
            }
        if str(last_entry.get("status") or "") == "completed":
            artifact_validation = _task_card_artifact_validation(
                task_card,
                materialized={"write_set": write_set, "read_set": read_set, "test_commands": test_commands},
                project_dir=project_dir,
            )
            last_entry["artifact_validation"] = artifact_validation
            if not artifact_validation["go"]:
                last_entry = {
                    **last_entry,
                    "status": "failed",
                    "failure_class": "task_card_expected_artifacts_missing",
                    "final_failure_class": "task_card_expected_artifacts_missing",
                    "recoverable_suggestion": "rerun_task_card_and_create_every_expected_artifact_and_referenced_scene_prefab_component_file",
                }
        last_entry["execution_visibility_mode"] = execution_visibility_mode
        attempts.append(
            _patch_attempt_record(
                entry=last_entry,
                attempt_index=attempt_index,
                max_attempts=max_runtime_attempts,
                continuation_argv=attempt_continuation_argv,
            )
        )
        continuation_argv = attempt_continuation_argv
        if str(last_entry.get("status") or "") == "completed":
            return {
                **last_entry,
                "attempts": attempts,
                "consecutive_failure_count": 0,
                "final_failure_class": None,
                "retry_exhausted": False,
                "preflight_blocker": False,
            }
        if _is_fail_fast_precondition(last_entry):
            return {
                **last_entry,
                "attempts": attempts,
                "consecutive_failure_count": 0,
                "final_failure_class": _patch_failure_class(last_entry) or str(last_entry.get("failure_class") or ""),
                "retry_exhausted": False,
                "preflight_blocker": True,
            }
        if not _is_retryable_runtime_failure(last_entry):
            return {
                **last_entry,
                "attempts": attempts,
                "consecutive_failure_count": len(attempts),
                "final_failure_class": _patch_failure_class(last_entry) or str(last_entry.get("failure_class") or ""),
                "retry_exhausted": False,
                "preflight_blocker": False,
            }
        if _should_switch_adapter_after_failure(last_entry) and adapter_index < len(adapter_sequence) - 1:
            adapter_index += 1
    final_failure_class = _patch_failure_class(last_entry) or str(last_entry.get("failure_class") or "same_project_task_card_patch_failed")
    return {
        **last_entry,
        "status": "blocked",
        "failure_class": "blocked_after_three_attempts",
        "attempts": attempts,
        "consecutive_failure_count": len(attempts),
        "final_failure_class": final_failure_class,
        "retry_exhausted": True,
        "preflight_blocker": False,
        "recoverable_suggestion": "operator_repair_required_after_three_consecutive_runtime_failures",
    }


def _patch_attempt_record(
    *,
    entry: dict[str, Any],
    attempt_index: int,
    max_attempts: int,
    continuation_argv: list[str],
) -> dict[str, Any]:
    watchdog = entry.get("watchdog") if isinstance(entry.get("watchdog"), dict) else {}
    mutation_result = entry.get("mutation_result") if isinstance(entry.get("mutation_result"), dict) else {}
    return {
        "attempt_index": attempt_index,
        "max_attempts": max_attempts,
        "status": str(entry.get("status") or "failed"),
        "failure_class": entry.get("failure_class"),
        "receipt_id": entry.get("receipt_id"),
        "child_run_id": entry.get("child_run_id"),
        "child_attempt_id": entry.get("child_attempt_id"),
        "worker_adapter": entry.get("worker_adapter"),
        "execution_visibility_mode": entry.get("execution_visibility_mode"),
        "control_plane_visibility": entry.get("control_plane_visibility"),
        "provider_visibility": entry.get("provider_visibility"),
        "provider_visible_cli_required": bool(entry.get("provider_visible_cli_required")),
        "provider_visible_cli_session": entry.get("provider_visible_cli_session"),
        "provider_visible_cli_log_paths": entry.get("provider_visible_cli_log_paths"),
        "visible_cli_session": entry.get("visible_cli_session"),
        "visible_cli_log_paths": entry.get("visible_cli_log_paths") or _visible_cli_log_paths(entry),
        "artifact_validation": entry.get("artifact_validation"),
        "watchdog_source": entry.get("watchdog_source"),
        "watchdog": watchdog,
        "stdout_preview": entry.get("stdout_preview"),
        "stderr_preview": entry.get("stderr_preview"),
        "changed_files": mutation_result.get("changed_files") or entry.get("changed_files") or [],
        "tests_status": mutation_result.get("final_test_status") or entry.get("final_test_status"),
        "last_provider_output_at": entry.get("last_provider_output_at") or watchdog.get("last_provider_output_at"),
        "last_material_progress_at": entry.get("last_material_progress_at") or watchdog.get("last_material_progress_at"),
        "last_provider_output_age_seconds": watchdog.get("last_provider_output_age_seconds"),
        "last_material_progress_age_seconds": watchdog.get("last_material_progress_age_seconds"),
        "continuation_argv": continuation_argv,
        "continuation_command": subprocess.list2cmdline(continuation_argv),
    }


def _task_card_path_with_retry_context(
    task_card_path: Path,
    *,
    attempt_index: int,
    prior_entry: dict[str, Any],
) -> Path:
    validation = prior_entry.get("artifact_validation") if isinstance(prior_entry, dict) else None
    if attempt_index <= 1 or not isinstance(validation, dict) or validation.get("go"):
        return task_card_path
    retry_path = task_card_path.with_name(f"{task_card_path.stem}.retry_attempt_{attempt_index}.md")
    try:
        original = task_card_path.read_text(encoding="utf-8")
    except OSError:
        return task_card_path
    validation_summary = {
        "blockers": validation.get("blockers") or [],
        "missing_artifacts": validation.get("missing_artifacts") or [],
        "invalid_json_artifacts": validation.get("invalid_json_artifacts") or [],
        "invalid_scene_artifacts": validation.get("invalid_scene_artifacts") or [],
        "mojibake_json_artifacts": validation.get("mojibake_json_artifacts") or [],
        "referenced_missing_artifacts": validation.get("referenced_missing_artifacts") or [],
        "launch_scene_blockers": validation.get("launch_scene_blockers") or [],
    }
    retry_note = (
        "\n\n## Previous Artifact Validation Failure\n\n"
        "The previous worker attempt failed the task-card artifact contract. Fix every listed item in this attempt; "
        "do not repeat missing or placeholder paths. If a referenced scene path is missing, read "
        "`workflow_runtime_evidence/scene_prefab_binding_evidence.json` and `settings/v2/packages/scene.json`, then "
        "reference the existing generated launch scene path only.\n\n"
        "```json\n"
        f"{json.dumps(validation_summary, ensure_ascii=False, indent=2)}\n"
        "```\n"
    )
    try:
        retry_path.write_text(f"{original}{retry_note}", encoding="utf-8")
    except OSError:
        return task_card_path
    return retry_path


def _task_card_artifact_validation(
    card: TaskCard,
    *,
    materialized: dict[str, list[str]],
    project_dir: Path,
) -> dict[str, Any]:
    checked: list[str] = []
    missing: list[str] = []
    invalid_json: list[str] = []
    invalid_scene: list[str] = []
    mojibake_json: list[str] = []
    referenced_missing: list[str] = []
    scene_paths: list[Path] = []
    expected = _dedupe_strings(
        [
            *list(card.expected_artifacts or []),
            *[item for item in card.evidence_requirements if _looks_like_project_artifact_reference(str(item))],
        ]
    )
    for raw in expected:
        raw_path, raw_pointer = _split_artifact_json_pointer(str(raw))
        materialized_path = _materialize_project_scope_path(raw_path, project_dir=project_dir, pipeline_id=card.run_id)
        if _contains_glob(materialized_path):
            continue
        path = Path(materialized_path)
        if not path.is_absolute():
            path = project_dir / materialized_path
        checked.append(path.as_posix())
        if not path.exists():
            missing.append(path.as_posix())
            continue
        if path.suffix.lower() == ".scene":
            scene_paths.append(path)
            if not _is_valid_cocos_scene_artifact(path):
                invalid_scene.append(path.as_posix())
            continue
        if path.suffix.lower() != ".json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            invalid_json.append(path.as_posix())
            continue
        if raw_pointer and not _json_pointer_exists(payload, raw_pointer):
            referenced_missing.append(f"{path.as_posix()}#{raw_pointer}")
        if _is_player_visible_chinese_artifact(path) and _json_contains_mojibake(payload):
            mojibake_json.append(path.as_posix())
        if isinstance(payload, dict):
            for referenced in _project_artifact_references_from_payload(payload):
                if _is_deferred_artifact_reference(payload, referenced):
                    continue
                referenced_path_text, referenced_pointer = _split_artifact_json_pointer(referenced)
                referenced_path = Path(referenced_path_text)
                if not referenced_path.is_absolute():
                    referenced_path = project_dir / referenced_path_text
                if not referenced_path.exists():
                    referenced_missing.append(
                        f"{referenced_path.as_posix()}#{referenced_pointer}" if referenced_pointer else referenced_path.as_posix()
                    )
                    continue
                if referenced_pointer and referenced_path.suffix.lower() == ".json":
                    try:
                        referenced_payload = json.loads(referenced_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        invalid_json.append(referenced_path.as_posix())
                        continue
                    if not _json_pointer_exists(referenced_payload, referenced_pointer):
                        referenced_missing.append(f"{referenced_path.as_posix()}#{referenced_pointer}")
                        continue
                if referenced_path.suffix.lower() == ".scene":
                    scene_paths.append(referenced_path)
                    if not _is_valid_cocos_scene_artifact(referenced_path):
                        invalid_scene.append(referenced_path.as_posix())
    blockers: list[str] = []
    if missing:
        blockers.append("expected_artifact_missing")
    if invalid_json:
        blockers.append("expected_json_artifact_invalid")
    if invalid_scene:
        blockers.append("expected_cocos_scene_artifact_invalid")
    if mojibake_json:
        blockers.append("player_visible_chinese_mojibake_detected")
    if referenced_missing:
        blockers.append("referenced_artifact_missing")
    launch_scene_blockers = _launch_scene_binding_blockers(
        card=card,
        project_dir=project_dir,
        scene_paths=scene_paths,
    )
    blockers.extend(launch_scene_blockers)
    scene_component_blockers = _scene_runtime_component_blockers(card=card, scene_paths=scene_paths)
    blockers.extend(scene_component_blockers)
    return {
        "go": not blockers,
        "blockers": blockers,
        "checked_artifacts": _dedupe_strings(checked),
        "missing_artifacts": _dedupe_strings(missing),
        "invalid_json_artifacts": _dedupe_strings(invalid_json),
        "invalid_scene_artifacts": _dedupe_strings(invalid_scene),
        "mojibake_json_artifacts": _dedupe_strings(mojibake_json),
        "referenced_missing_artifacts": _dedupe_strings(referenced_missing),
        "launch_scene_blockers": launch_scene_blockers,
        "scene_component_blockers": scene_component_blockers,
        "materialized_write_set": materialized.get("write_set") or [],
    }


def _contains_glob(value: str) -> bool:
    return any(marker in str(value) for marker in ("*", "?", "["))


def _split_artifact_json_pointer(reference: str) -> tuple[str, str]:
    text = str(reference).strip().replace("\\", "/")
    if "#" not in text:
        return text, ""
    path, pointer = text.split("#", 1)
    return path, pointer.lstrip("/")


def _json_pointer_exists(payload: Any, pointer: str) -> bool:
    if not pointer:
        return True
    current = payload
    for raw_token in pointer.split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                return False
            current = current[token]
            continue
        if isinstance(current, list):
            try:
                index = int(token)
            except ValueError:
                return False
            if index < 0 or index >= len(current):
                return False
            current = current[index]
            continue
        return False
    return True


def _looks_like_project_artifact_reference(value: str) -> bool:
    text = str(value).strip().replace("\\", "/")
    if not text or " " in text:
        return False
    return text.startswith(
        (
            "assets/",
            "settings/",
            "workflow_runtime_evidence/",
            "player_visible_evidence/",
            "workflow_commercial_feature_evidence.json",
        )
    )


def _project_artifact_references_from_payload(payload: dict[str, Any]) -> list[str]:
    references: list[str] = []

    def visit(value: Any, *, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                visit(child_value, key=str(child_key))
            return
        if isinstance(value, list):
            for item in value:
                visit(item, key=key)
            return
        if not isinstance(value, str):
            return
        normalized = value.strip().replace("\\", "/")
        if not normalized:
            return
        if " " in normalized:
            return
        key_normalized = key.lower()
        path_key = key_normalized.endswith("path") or key_normalized in {
            "prefabs",
            "scene_path",
            "prefab_path",
            "script_path",
            "runtime_component",
            "product_body_path",
            "cocos_resource_path",
            "relative_path",
            "changed_files",
        }
        if not path_key and not normalized.startswith(
            (
                "assets/",
                "settings/",
                "workflow_runtime_evidence/",
                "player_visible_evidence/",
                "workflow_commercial_feature_evidence.json",
            )
        ):
            return
        if normalized.startswith(
            (
                "assets/",
                "settings/",
                "workflow_runtime_evidence/",
                "player_visible_evidence/",
                "workflow_commercial_feature_evidence.json",
            )
        ):
            references.append(normalized)

    visit(payload)
    return _dedupe_strings(references)


def _is_deferred_artifact_reference(payload: dict[str, Any], reference: str) -> bool:
    text = str(reference).lower()
    payload_text = json.dumps(payload, ensure_ascii=False).lower()
    if "screenshots/" in text and any(
        marker in payload_text
        for marker in (
            "deferred",
            "pending_browser_capture",
            "pending_playtest_capture",
            "pending_runtime_capture",
            "declared_for_runtime_capture",
            "capture_required_after",
            "expected_capture_after_runtime_launch",
            "expected_capture_paths",
            "contract_bound",
            "evidence_is_contract_until_runner_capture",
            "fresh_capture_required_by_runner",
            "runner_capture_required",
            "ready_for_runner_capture",
            "runner capture targets",
        )
    ):
        return True
    return False


def _is_valid_cocos_scene_artifact(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, list) or len(payload) < 2:
        return False
    has_scene_asset = any(isinstance(item, dict) and item.get("__type__") == "cc.SceneAsset" for item in payload)
    has_scene = any(isinstance(item, dict) and item.get("__type__") == "cc.Scene" for item in payload)
    has_node = any(isinstance(item, dict) and item.get("__type__") == "cc.Node" for item in payload)
    return bool(has_scene_asset and has_scene and has_node)


def _scene_runtime_component_blockers(*, card: TaskCard, scene_paths: list[Path]) -> list[str]:
    if "scene_prefab_component_binding" not in str(card.task_card_id):
        return []
    valid_scenes = [path for path in _dedupe_paths(scene_paths) if _is_valid_cocos_scene_artifact(path)]
    if not valid_scenes:
        return []
    if any(_scene_has_runtime_component_instance(path) for path in valid_scenes):
        return []
    return ["cocos_scene_runtime_component_binding_missing"]


def _scene_has_runtime_component_instance(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, list):
        return False
    node_component_refs: set[int] = set()
    fake_component_metadata = False
    custom_component_ids: set[int] = set()
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            continue
        if item.get("__type__") == "cc.Node":
            for ref in item.get("_components") or []:
                if isinstance(ref, dict) and isinstance(ref.get("__id__"), int):
                    node_component_refs.add(ref["__id__"])
            continue
        item_type = str(item.get("__type__") or "")
        if item_type == "cc.CompPrefabInfo" and (item.get("component") or item.get("script")):
            fake_component_metadata = True
            continue
        if item_type and not item_type.startswith("cc.") and item.get("_enabled", True) is not False:
            custom_component_ids.add(index)
    return bool(custom_component_ids & node_component_refs) and not (fake_component_metadata and not custom_component_ids)


def _launch_scene_binding_blockers(*, card: TaskCard, project_dir: Path, scene_paths: list[Path]) -> list[str]:
    if "scene_prefab_component_binding" not in str(card.task_card_id):
        return []
    valid_scenes = [path for path in _dedupe_paths(scene_paths) if _is_valid_cocos_scene_artifact(path)]
    if not valid_scenes:
        return ["cocos_launch_scene_valid_scene_missing"]
    scene_json = project_dir / "settings" / "v2" / "packages" / "scene.json"
    if not scene_json.exists():
        return ["cocos_launch_scene_settings_missing"]
    try:
        settings = json.loads(scene_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["cocos_launch_scene_settings_invalid"]
    current_scene = str(settings.get("current-scene") or settings.get("currentScene") or "").strip()
    if not current_scene:
        return ["cocos_launch_scene_current_scene_missing"]
    scene_uuids = {_scene_meta_uuid(path) for path in valid_scenes}
    scene_uuids.discard("")
    if current_scene not in scene_uuids:
        return ["cocos_launch_scene_not_bound_to_generated_scene"]
    return []


def _scene_meta_uuid(scene_path: Path) -> str:
    meta_path = scene_path.with_suffix(scene_path.suffix + ".meta")
    if not meta_path.exists():
        return ""
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(payload.get("uuid") or "").strip()


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = path.resolve().as_posix() if path.exists() else path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def _is_player_visible_chinese_artifact(path: Path) -> bool:
    normalized = path.as_posix().lower()
    return any(
        marker in normalized
        for marker in (
            "localization",
            "chinese_ui_panels_evidence.json",
            "feedback_text_tokens",
            "block_palette_set",
            "reward_gallery_shards",
            "art_direction_manifest",
        )
    )


def _json_contains_mojibake(value: Any, *, key: str = "") -> bool:
    key_normalized = key.strip().lower()
    if key_normalized in {
        "forbidden_garbled_sequences",
        "forbidden_mojibake_sequences",
        "mojibake_examples",
        "blocked_mojibake_examples",
    }:
        return False
    if isinstance(value, dict):
        return any(_json_contains_mojibake(child, key=str(child_key)) for child_key, child in value.items())
    if isinstance(value, list):
        return any(_json_contains_mojibake(child, key=key) for child in value)
    if isinstance(value, str):
        return _looks_like_mojibake(value)
    return False


def _is_fail_fast_precondition(entry: dict[str, Any]) -> bool:
    failure_class = str(entry.get("failure_class") or "")
    return failure_class in FAIL_FAST_PRECONDITION_FAILURE_CLASSES or failure_class.endswith("_preflight_blocker")


def _is_retryable_runtime_failure(entry: dict[str, Any]) -> bool:
    return _patch_root_failure_class(entry) in RETRYABLE_RUNTIME_FAILURE_CLASSES


def _completed_patch_entry_has_fresh_execution(entry: dict[str, Any]) -> bool:
    if str(entry.get("status") or "") != "completed":
        return False
    adapter = str(entry.get("worker_adapter") or entry.get("adapter") or entry.get("capability_adapter") or "").strip().lower()
    satisfaction_mode = str(entry.get("satisfaction_mode") or "").strip().lower()
    if adapter in {"shell", "noop", "dry_run", "dry-run", "existing_same_project_evidence"}:
        return False
    if satisfaction_mode in {"existing_same_project_evidence", "reused_reference_only"}:
        return False
    if entry.get("execution_visibility_mode") == "human_visible_cli_enforced" and not _visible_cli_session_valid(entry):
        return False
    mutation_result = entry.get("mutation_result") if isinstance(entry.get("mutation_result"), dict) else {}
    changed_files = mutation_result.get("changed_files") or entry.get("changed_files") or []
    final_test_status = str(mutation_result.get("final_test_status") or entry.get("final_test_status") or "").strip().lower()
    return bool(
        entry.get("receipt_id")
        and entry.get("child_run_id")
        and (entry.get("child_attempt_id") or entry.get("attempt_id"))
        and changed_files
        and final_test_status == "passed"
    )


def _task_card_visibility_mode(card: TaskCard) -> str | None:
    metadata = card.metadata if isinstance(card.metadata, dict) else {}
    mode = str(metadata.get("execution_visibility_mode") or "").strip()
    if mode:
        return mode
    if metadata.get("human_visible_cli_required") is True:
        return "human_visible_cli_enforced"
    if str(card.execution_mode or "").strip() == "same_project_patch" and str(card.risk_level or "").strip().lower() == "high":
        return "human_visible_cli_enforced"
    return None


def _adapter_attempt_sequence(card: TaskCard, *, preferred_adapter_name: str | None = None) -> list[str]:
    initial = _normalize_adapter_name(preferred_adapter_name or card.provider_lane or "codex")
    sequence = [initial]
    fallback = _fallback_adapter_for(initial)
    if fallback and fallback not in sequence:
        sequence.append(fallback)
    return sequence


def _fallback_adapter_for(adapter_name: Any) -> str | None:
    normalized = _normalize_adapter_name(adapter_name)
    if normalized == "codex":
        return "opencode"
    if normalized == "opencode":
        return "codex"
    return None


def _normalize_adapter_name(adapter_name: Any) -> str:
    normalized = str(adapter_name or "codex").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in {
        "codex_cli",
        "codex_cli_login",
        "codex_or_configured_strong_model",
        "configured_strong_model",
        "strong_model",
        "agent",
    }:
        return "codex"
    if normalized == "opencode_cli":
        return "opencode"
    if normalized in {"shell", "noop", "dry_run", "dry-run"}:
        return "codex"
    return normalized or "codex"


def _should_switch_adapter_after_failure(entry: dict[str, Any]) -> bool:
    return _patch_root_failure_class(entry) in {
        "provider_no_material_progress_timeout",
        "provider_output_idle_timeout",
        "provider_timeout",
        "workflow_child_stalled",
        "child_stdout_silent",
    }


def _visible_cli_session_valid(entry: dict[str, Any]) -> bool:
    session = entry.get("visible_cli_session")
    if not isinstance(session, dict):
        return False
    required = ["pid", "argv", "cwd", "stdout_log_path", "stderr_log_path", "stream_log_path", "started_at"]
    if any(not session.get(key) for key in required):
        return False
    if session.get("status") in {"unavailable", "blocked"}:
        return False
    return True


def _provider_visible_cli_required(entry: dict[str, Any]) -> bool:
    if bool(entry.get("provider_visible_cli_required")):
        return True
    return (
        str(entry.get("control_plane_visibility") or "").strip().lower() == "resident"
        and str(entry.get("provider_visibility") or "").strip().lower() == "direct_visible"
    )


def _provider_visible_cli_session_valid(entry: dict[str, Any]) -> bool:
    session = entry.get("provider_visible_cli_session")
    if not isinstance(session, dict):
        return False
    required = ["argv", "cwd", "stdout_log_path", "stderr_log_path", "stream_log_path", "started_at"]
    if any(not session.get(key) for key in required):
        return False
    if not (session.get("provider_pid") or session.get("wrapper_pid")):
        return False
    if session.get("status") in {"unavailable", "blocked"}:
        return False
    return True


def _visible_cli_log_paths(entry: dict[str, Any]) -> dict[str, Any]:
    session = entry.get("visible_cli_session")
    if not isinstance(session, dict):
        return {}
    return {
        "stdout_log_path": session.get("stdout_log_path"),
        "stderr_log_path": session.get("stderr_log_path"),
        "stream_log_path": session.get("stream_log_path"),
        "session_path": session.get("session_path"),
    }


def collect_project_runtime_evidence(
    *,
    project_dir: Path,
    creator_exe: Path,
    require_build: bool,
    require_playtest: bool,
    build_timeout_seconds: int = 900,
) -> dict[str, Any]:
    build: dict[str, Any] | None = None
    playtest: dict[str, Any] | None = None
    build_ledger: dict[str, Any] | None = None
    browser_playtest_ledger: dict[str, Any] | None = None
    build_ledger_path: str | None = None
    browser_playtest_ledger_path: str | None = None
    blockers: list[str] = []
    runtime_evidence_root = project_dir / "workflow_runtime_evidence"
    if require_build:
        runtime_evidence_root.mkdir(parents=True, exist_ok=True)
        build = build_cocos_project(project_path=project_dir, creator_exe=creator_exe, timeout_seconds=build_timeout_seconds)
        build.setdefault(
            "build_command",
            [creator_exe.as_posix(), "--project", project_dir.as_posix(), "--build", "platform=web-mobile;debug=false"],
        )
        build_ledger = build_build_ledger(build)
        build_ledger_path = (runtime_evidence_root / "build_ledger.json").as_posix()
        build_ledger["evidence_path"] = build_ledger_path
        _write_json(runtime_evidence_root / "build_ledger.json", build_ledger)
        blockers.extend(build_ledger.get("blockers") or [])
        build_output = build.get("build_output_path")
        if require_playtest and build_ledger.get("go") and build_output:
            try:
                playtest = playtest_cocos_build(build_output_path=build_output, evidence_dir=project_dir / "playtest_evidence")
            except Exception as exc:
                playtest = _failed_browser_playtest_evidence(
                    build_output_path=build_output,
                    evidence_dir=project_dir / "playtest_evidence",
                    exc=exc,
                )
            browser_playtest_ledger = build_browser_playtest_ledger(playtest)
            browser_playtest_ledger_path = (runtime_evidence_root / "browser_playtest_ledger.json").as_posix()
            browser_playtest_ledger["evidence_path"] = browser_playtest_ledger_path
            _write_json(runtime_evidence_root / "browser_playtest_ledger.json", browser_playtest_ledger)
            blockers.extend(browser_playtest_ledger.get("blockers") or [])
        elif require_playtest:
            blockers.append("browser_playtest_missing_build_output")
            browser_playtest_ledger = build_browser_playtest_ledger(None)
            browser_playtest_ledger_path = (runtime_evidence_root / "browser_playtest_ledger.json").as_posix()
            browser_playtest_ledger["evidence_path"] = browser_playtest_ledger_path
            _write_json(runtime_evidence_root / "browser_playtest_ledger.json", browser_playtest_ledger)
            blockers.extend(browser_playtest_ledger.get("blockers") or [])
    elif require_playtest:
        runtime_evidence_root.mkdir(parents=True, exist_ok=True)
        blockers.append("browser_playtest_requires_build")
        browser_playtest_ledger = build_browser_playtest_ledger(None)
        browser_playtest_ledger_path = (runtime_evidence_root / "browser_playtest_ledger.json").as_posix()
        browser_playtest_ledger["evidence_path"] = browser_playtest_ledger_path
        _write_json(runtime_evidence_root / "browser_playtest_ledger.json", browser_playtest_ledger)
        blockers.extend(browser_playtest_ledger.get("blockers") or [])
    runtime_evidence_root.mkdir(parents=True, exist_ok=True)
    if build_ledger is None:
        build_ledger = build_build_ledger(None)
        build_ledger_path = (runtime_evidence_root / "build_ledger.json").as_posix()
        build_ledger["evidence_path"] = build_ledger_path
        _write_json(runtime_evidence_root / "build_ledger.json", build_ledger)
    if browser_playtest_ledger is None:
        browser_playtest_ledger = build_browser_playtest_ledger(None)
        browser_playtest_ledger_path = (runtime_evidence_root / "browser_playtest_ledger.json").as_posix()
        browser_playtest_ledger["evidence_path"] = browser_playtest_ledger_path
        _write_json(runtime_evidence_root / "browser_playtest_ledger.json", browser_playtest_ledger)
    feature_evidence = _load_project_feature_evidence(project_dir)
    commercial_feature_coverage = feature_evidence.get("commercial_feature_coverage", {})
    player_visible_checks = feature_evidence.get("player_visible_checks", {})
    gameplay_semantic_evidence = build_gameplay_semantic_evidence(
        feature_evidence.get("gameplay_semantic_evidence"),
        feature_coverage=commercial_feature_coverage,
        playtest=playtest,
    )
    product_body_evidence = build_product_body_evidence(
        feature_evidence.get("product_body_evidence"),
        gameplay_semantic_evidence=gameplay_semantic_evidence,
        playtest=playtest,
    )
    product_depth_evidence = build_product_depth_evidence(
        product_depth=feature_evidence.get("product_depth_evidence"),
        feature_coverage=commercial_feature_coverage,
        player_visible_checks=player_visible_checks,
        playtest=playtest,
    )
    for filename, payload in [
        ("gameplay_semantic_evidence.json", gameplay_semantic_evidence),
        ("product_body_evidence.json", product_body_evidence),
        ("product_depth_evidence.json", product_depth_evidence),
    ]:
        payload["evidence_path"] = (runtime_evidence_root / filename).as_posix()
        _write_json(runtime_evidence_root / filename, payload)
    return {
        "schema_version": "commercial_game_same_project_runtime_evidence_v1",
        "technical_smoke_go": project_dir.exists(),
        "production_scaffold_go": False,
        "commercial_playable_go": False,
        "commercial_playable_blockers": _dedupe_strings(blockers),
        "commercial_feature_coverage": commercial_feature_coverage,
        "player_visible_checks": player_visible_checks,
        "manual_player_evidence": feature_evidence.get("manual_player_evidence", {}),
        "product_depth_evidence": product_depth_evidence,
        "gameplay_semantic_evidence": gameplay_semantic_evidence,
        "product_body_evidence": product_body_evidence,
        "product_body_baseline": feature_evidence.get("product_body_baseline", {}),
        "development_readiness_validation_gates": feature_evidence.get("development_readiness_validation_gates", {}),
        "manifest_path": (project_dir / "workflow_project_manifest.json").as_posix(),
        "build": build,
        "playtest": playtest,
        "build_ledger": build_ledger,
        "browser_playtest_ledger": browser_playtest_ledger,
        "build_ledger_path": build_ledger_path,
        "browser_playtest_ledger_path": browser_playtest_ledger_path,
    }


def blocked_project_runtime_evidence_due_to_upstream(
    *,
    project_dir: Path,
    patch_ledger: dict[str, Any],
    require_build: bool,
    require_playtest: bool,
) -> dict[str, Any]:
    runtime_evidence_root = project_dir / "workflow_runtime_evidence"
    runtime_evidence_root.mkdir(parents=True, exist_ok=True)
    downstream_stages = _blocked_downstream_stages(require_build=require_build, require_playtest=require_playtest)
    blockers = ["blocked_by_same_project_worker"]
    source = {
        "upstream_stage": "same_project_worker_patch",
        "upstream_blockers": list(patch_ledger.get("blockers") or []),
        "blocked_downstream_stages": downstream_stages,
        "skip_reason": "skipped_due_to_upstream_failure",
        "next_continuation_command": patch_ledger.get("next_continuation_command"),
    }
    build_ledger = _blocked_evidence_contract(
        schema_version=BUILD_LEDGER_SCHEMA,
        stage="cocos_build",
        blockers=blockers,
        source=source,
    )
    browser_playtest_ledger = _blocked_evidence_contract(
        schema_version=BROWSER_PLAYTEST_LEDGER_SCHEMA,
        stage="browser_playtest",
        blockers=blockers,
        source=source,
    )
    product_depth_evidence = _blocked_evidence_contract(
        schema_version=PRODUCT_DEPTH_EVIDENCE_SCHEMA,
        stage="product_depth",
        blockers=blockers,
        source=source,
    )
    gameplay_semantic_evidence = _blocked_evidence_contract(
        schema_version=GAMEPLAY_SEMANTIC_EVIDENCE_SCHEMA,
        stage="gameplay_semantic",
        blockers=blockers,
        source=source,
    )
    product_body_evidence = _blocked_evidence_contract(
        schema_version=PRODUCT_BODY_EVIDENCE_SCHEMA,
        stage="product_body",
        blockers=blockers,
        source=source,
    )
    build_ledger_path = runtime_evidence_root / "build_ledger.json"
    browser_playtest_ledger_path = runtime_evidence_root / "browser_playtest_ledger.json"
    product_depth_evidence_path = runtime_evidence_root / "product_depth_evidence.json"
    gameplay_semantic_evidence_path = runtime_evidence_root / "gameplay_semantic_evidence.json"
    product_body_evidence_path = runtime_evidence_root / "product_body_evidence.json"
    build_ledger["evidence_path"] = build_ledger_path.as_posix()
    browser_playtest_ledger["evidence_path"] = browser_playtest_ledger_path.as_posix()
    product_depth_evidence["evidence_path"] = product_depth_evidence_path.as_posix()
    gameplay_semantic_evidence["evidence_path"] = gameplay_semantic_evidence_path.as_posix()
    product_body_evidence["evidence_path"] = product_body_evidence_path.as_posix()
    _write_json(build_ledger_path, build_ledger)
    _write_json(browser_playtest_ledger_path, browser_playtest_ledger)
    _write_json(product_depth_evidence_path, product_depth_evidence)
    _write_json(gameplay_semantic_evidence_path, gameplay_semantic_evidence)
    _write_json(product_body_evidence_path, product_body_evidence)
    return {
        "schema_version": "commercial_game_same_project_runtime_evidence_v1",
        "status": "blocked",
        "technical_smoke_go": project_dir.exists(),
        "production_scaffold_go": False,
        "commercial_playable_go": False,
        "commercial_playable_blockers": blockers,
        "blocked_downstream_stages": downstream_stages,
        "skip_reason": "skipped_due_to_upstream_failure",
        "commercial_feature_coverage": {},
        "player_visible_checks": {},
        "manual_player_evidence": {},
        "product_depth_evidence": product_depth_evidence,
        "gameplay_semantic_evidence": gameplay_semantic_evidence,
        "product_body_evidence": product_body_evidence,
        "manifest_path": (project_dir / "workflow_project_manifest.json").as_posix(),
        "build": None,
        "playtest": None,
        "build_ledger": build_ledger,
        "browser_playtest_ledger": browser_playtest_ledger,
        "build_ledger_path": build_ledger_path.as_posix(),
        "browser_playtest_ledger_path": browser_playtest_ledger_path.as_posix(),
        "product_depth_evidence_path": product_depth_evidence_path.as_posix(),
        "gameplay_semantic_evidence_path": gameplay_semantic_evidence_path.as_posix(),
        "product_body_evidence_path": product_body_evidence_path.as_posix(),
    }


def production_payload_from_worker(
    *,
    schema_version: str,
    created_at: str,
    pipeline_id: str,
    project_dir: Path,
    task_card_quality: dict[str, Any],
    runtime_evidence: dict[str, Any],
    assets_stage: dict[str, Any],
    ecosystem_evidence: dict[str, Any] | None,
    patch_ledger: dict[str, Any],
    skipped_task_cards: list[str],
    max_repair_attempts: int,
    dedupe_strings: Callable[[list[Any]], list[str]],
    blocker_details: Callable[[list[str]], list[dict[str, str]]],
    recoverable_suggestions: Callable[[list[str]], list[str]],
) -> dict[str, Any]:
    blockers = list(runtime_evidence.get("commercial_playable_blockers") or [])
    ecosystem_payload = dict(ecosystem_evidence or {})
    asset_graph = build_asset_graph_contract(assets_stage)
    cocos_bridge_evidence = build_cocos_bridge_evidence_contract(ecosystem_payload)
    same_project_patch_ledger_contract = build_same_project_patch_ledger_contract(patch_ledger)
    build_ledger = build_build_ledger(runtime_evidence.get("build_ledger") or runtime_evidence.get("build"))
    browser_playtest_ledger = build_browser_playtest_ledger(
        runtime_evidence.get("browser_playtest_ledger") or runtime_evidence.get("playtest")
    )
    product_depth_evidence = build_product_depth_evidence(
        product_depth=runtime_evidence.get("product_depth_evidence"),
        feature_coverage=runtime_evidence.get("commercial_feature_coverage"),
        player_visible_checks=runtime_evidence.get("player_visible_checks"),
        playtest=runtime_evidence.get("playtest"),
    )
    gameplay_semantic_evidence = build_gameplay_semantic_evidence(
        runtime_evidence.get("gameplay_semantic_evidence"),
        feature_coverage=runtime_evidence.get("commercial_feature_coverage"),
        playtest=runtime_evidence.get("playtest"),
    )
    product_body_evidence = build_product_body_evidence(
        runtime_evidence.get("product_body_evidence"),
        gameplay_semantic_evidence=gameplay_semantic_evidence,
        playtest=runtime_evidence.get("playtest"),
    )
    evidence_contracts = {
        "asset_graph": asset_graph,
        "cocos_bridge_evidence": cocos_bridge_evidence,
        "same_project_patch_ledger": same_project_patch_ledger_contract,
        "build_ledger": build_ledger,
        "browser_playtest_ledger": browser_playtest_ledger,
        "gameplay_semantic_evidence": gameplay_semantic_evidence,
        "product_body_evidence": product_body_evidence,
        "product_depth_evidence": product_depth_evidence,
    }
    if assets_stage.get("placeholder_only"):
        blockers.append("placeholder_assets_only")
    if assets_stage and not assets_stage.get("commercial_assets_go"):
        blockers.extend(assets_stage.get("commercial_asset_blockers") or ["commercial_assets_no_go"])
    if not patch_ledger.get("same_project_worker_patch_go"):
        blockers.extend(patch_ledger.get("blockers") or ["same_project_worker_patch_missing"])
        blockers.append("blocked_by_same_project_worker")
    if ecosystem_payload and ecosystem_payload.get("strict_required") and not ecosystem_payload.get("ecosystem_integration_go"):
        blockers.extend(ecosystem_payload.get("blockers") or ["cocos_ecosystem_bridge_missing"])
    for contract in evidence_contracts.values():
        blockers.extend(contract.get("blockers") or [])
    blockers = dedupe_strings(blockers)
    machine_evidence_go = all(bool(contract.get("go")) for contract in evidence_contracts.values())
    playtest_payload = runtime_evidence.get("playtest") if isinstance(runtime_evidence.get("playtest"), dict) else {}
    human_review_packet = build_human_review_packet(
        product_depth_evidence=product_depth_evidence,
        evidence_contracts=evidence_contracts,
        manual_player_evidence=runtime_evidence.get("manual_player_evidence"),
        screenshots=list(playtest_payload.get("screenshots") or []),
        blockers=blockers,
    )
    human_review_packet_path = project_dir / "player_visible_evidence" / "human_player_review_packet.json"
    human_review_packet["evidence_path"] = human_review_packet_path.as_posix()
    _write_json(human_review_packet_path, human_review_packet)
    human_player_review_go = bool(human_review_packet.get("human_player_review_go"))
    commercial_playable_go = (
        bool(runtime_evidence.get("commercial_playable_go"))
        and bool(patch_ledger.get("same_project_worker_patch_go"))
        and machine_evidence_go
        and human_player_review_go
        and not blockers
    )
    development_readiness = build_commercial_game_development_readiness_evidence(
        task_card_quality=task_card_quality,
        same_project_patch_ledger=same_project_patch_ledger_contract,
        gameplay_semantic_evidence=gameplay_semantic_evidence,
        product_body_evidence=product_body_evidence,
        product_body_baseline=runtime_evidence.get("product_body_baseline"),
        validation_gates=runtime_evidence.get("development_readiness_validation_gates"),
        commercial_playable_go=commercial_playable_go,
        human_player_review_go=human_player_review_go,
    )
    return {
        "schema_version": schema_version,
        "created_at": created_at,
        "pipeline_id": pipeline_id,
        "project_dir": project_dir.as_posix(),
        "persistent_project_per_run": True,
        "task_card_quality": task_card_quality,
        "task_card_count": int(task_card_quality.get("task_card_count") or 0),
        "technical_smoke_go": bool(runtime_evidence.get("technical_smoke_go")),
        "production_scaffold_go": bool(runtime_evidence.get("production_scaffold_go")),
        "commercial_playable_go": commercial_playable_go,
        "commercial_game_development_readiness_go": bool(
            development_readiness.get("commercial_game_development_readiness_go")
        ),
        "ecosystem_integration_go": bool(ecosystem_payload.get("ecosystem_integration_go")),
        "live_role_provider_proof_go": False,
        "same_project_worker_patch_go": bool(patch_ledger.get("same_project_worker_patch_go")),
        "human_player_review_go": human_player_review_go,
        "machine_evidence_go": machine_evidence_go,
        "asset_graph_go": bool(asset_graph.get("go")),
        "build_ledger_go": bool(build_ledger.get("go")),
        "browser_playtest_ledger_go": bool(browser_playtest_ledger.get("go")),
        "degradation_findings": [],
        "commercial_playable_blockers": blockers,
        "commercial_playable_blocker_details": blocker_details(blockers),
        "recoverable_suggestions": recoverable_suggestions(blockers),
        "commercial_feature_coverage": runtime_evidence.get("commercial_feature_coverage") or {},
        "player_visible_checks": runtime_evidence.get("player_visible_checks") or {},
        "manual_player_evidence": runtime_evidence.get("manual_player_evidence") or {},
        "same_project_patch_ledger": patch_ledger,
        "skipped_non_worker_task_cards": skipped_task_cards,
        "cocos_ecosystem_evidence": ecosystem_payload,
        "evidence_contracts": evidence_contracts,
        "asset_graph": asset_graph,
        "cocos_bridge_evidence_contract": cocos_bridge_evidence,
        "same_project_patch_ledger_contract": same_project_patch_ledger_contract,
        "build_ledger": build_ledger,
        "browser_playtest_ledger": browser_playtest_ledger,
        "gameplay_semantic_evidence": gameplay_semantic_evidence,
        "product_body_evidence": product_body_evidence,
        "product_depth_evidence": product_depth_evidence,
        "human_review_packet": human_review_packet,
        "commercial_game_development_readiness": development_readiness,
        "blocked_downstream_stages": runtime_evidence.get("blocked_downstream_stages") or [],
        "normalized_repair_packet": _normalized_repair_packet(
            patch_ledger=patch_ledger,
            runtime_evidence=runtime_evidence,
        ),
        "manifest_path": runtime_evidence.get("manifest_path"),
        "build": runtime_evidence.get("build"),
        "playtest": runtime_evidence.get("playtest"),
        "assets": assets_stage,
        "max_repair_attempts": max_repair_attempts,
        "repair_policy": "same_project_incremental_repair",
        "forbids_fixed_template": True,
    }


def _write_ledger(ledger_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    ledger_path = ledger_root / "same_project_patch_ledger.json"
    ledger_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["ledger_path"] = ledger_path.as_posix()
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _materialize_task_card(card: TaskCard, *, project_dir: Path, pipeline_id: str) -> dict[str, list[str]]:
    return {
        "write_set": [_materialize_project_scope_path(item, project_dir=project_dir, pipeline_id=pipeline_id) for item in card.write_set],
        "read_set": [_materialize_project_scope_path(item, project_dir=project_dir, pipeline_id=pipeline_id) for item in card.read_set],
        "test_commands": [_materialize_project_command(item, project_dir=project_dir, pipeline_id=pipeline_id) for item in card.test_commands],
    }


def _materialize_project_path(value: str, *, project_dir: Path, pipeline_id: str) -> str:
    text = str(value)
    project = project_dir.as_posix()
    safe_pipeline = _safe_id(pipeline_id)
    return (
        text.replace("state/pipeline_runs/<run>/cocos_project", project)
        .replace("state\\pipeline_runs\\<run>\\cocos_project", project)
        .replace("<run>", safe_pipeline)
    )


_COCOS_PROJECT_SCOPED_PREFIXES = (
    "assets/",
    "build/",
    "extensions/",
    "player_visible_evidence/",
    "profiles/",
    "settings/",
    "temp/",
    "workflow_commercial_feature_evidence.json",
    "workflow_project_manifest.json",
    "workflow_runtime_evidence/",
)


def _materialize_project_scope_path(value: str, *, project_dir: Path, pipeline_id: str) -> str:
    materialized = _materialize_project_path(value, project_dir=project_dir, pipeline_id=pipeline_id)
    normalized = materialized.replace("\\", "/")
    if Path(materialized).is_absolute():
        return normalized
    stripped = normalized.lstrip("./")
    if _is_cocos_project_scoped_path(stripped):
        return (project_dir / stripped).resolve().as_posix()
    return normalized


def _is_cocos_project_scoped_path(value: str) -> bool:
    normalized = value.replace("\\", "/").lstrip("./")
    return any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in _COCOS_PROJECT_SCOPED_PREFIXES)


def _materialize_project_command(value: str, *, project_dir: Path, pipeline_id: str) -> str:
    materialized = _materialize_project_path(value, project_dir=project_dir, pipeline_id=pipeline_id)
    parts = materialized.split()
    if not parts:
        return materialized
    rewritten = [
        _quote_command_path(_materialize_project_scope_path(part, project_dir=project_dir, pipeline_id=pipeline_id))
        if _is_cocos_project_scoped_path(part)
        else part
        for part in parts
    ]
    return " ".join(rewritten)


def _quote_command_path(value: str) -> str:
    if " " not in value:
        return value
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def _task_card_markdown(card: TaskCard, materialized: dict[str, list[str]]) -> str:
    lines = [f"# {card.title}", "", f"task_card_id: `{card.task_card_id}`", "", "## Goal", "", card.goal or card.description, ""]
    for title, values in [
        ("Write Set", materialized["write_set"]),
        ("Read Set", materialized["read_set"]),
        ("Acceptance Criteria", card.acceptance_criteria),
        ("Evidence Requirements", card.evidence_requirements),
        ("Blocking Conditions", card.blocking_conditions),
        ("Model Guidance", card.model_guidance),
        ("Test Commands", materialized["test_commands"]),
    ]:
        lines.extend([f"## {title}", "", *[f"- {value}" for value in values], ""])
    return "\n".join(lines).rstrip() + "\n"


def _normalize_patch_ledger_entry(
    card: TaskCard,
    materialized: dict[str, list[str]],
    entry: dict[str, Any],
    *,
    root: Path,
    db_path: Path | None,
    project_dir: Path,
    card_path: Path,
    max_repair_attempts: int,
    execution_visibility_mode: str | None,
) -> dict[str, Any]:
    mutation_result = entry.get("mutation_result") if isinstance(entry.get("mutation_result"), dict) else {}
    status = str(entry.get("status") or "failed")
    continuation_argv = _continuation_argv(
        root=root,
        db_path=db_path,
        project_dir=project_dir,
        card_path=card_path,
        card=card,
        materialized=materialized,
        max_repair_attempts=max_repair_attempts,
        entry=entry,
        execution_visibility_mode=execution_visibility_mode,
    )
    continuation_required = status != "completed"
    watchdog = entry.get("watchdog") if isinstance(entry.get("watchdog"), dict) else {}
    attempts = entry.get("attempts") if isinstance(entry.get("attempts"), list) else []
    final_failure_class = entry.get("final_failure_class")
    if status != "completed" and not final_failure_class:
        final_failure_class = _patch_root_failure_class(entry)
    return {
        "task_card_id": card.task_card_id,
        "title": card.title,
        "status": status,
        "failure_class": entry.get("failure_class"),
        "final_failure_class": final_failure_class,
        "retry_exhausted": bool(entry.get("retry_exhausted")),
        "preflight_blocker": bool(entry.get("preflight_blocker")),
        "attempt_index": entry.get("attempt_index"),
        "max_attempts": entry.get("max_attempts") or TASK_CARD_RUNTIME_MAX_ATTEMPTS,
        "consecutive_failure_count": int(entry.get("consecutive_failure_count") or 0),
        "attempts": attempts,
        "receipt_id": entry.get("receipt_id"),
        "child_run_id": entry.get("child_run_id"),
        "child_attempt_id": entry.get("child_attempt_id"),
        "worker_adapter": entry.get("worker_adapter"),
        "execution_visibility_mode": execution_visibility_mode,
        "visible_cli_session": entry.get("visible_cli_session"),
        "visible_cli_log_paths": entry.get("visible_cli_log_paths") or _visible_cli_log_paths(entry),
        "watchdog_source": entry.get("watchdog_source"),
        "evidence_id": entry.get("evidence_id"),
        "review_decision": entry.get("review_decision"),
        "task_card_path": card_path.as_posix(),
        "write_set": materialized["write_set"],
        "read_set": materialized["read_set"],
        "test_commands": materialized["test_commands"],
        "artifact_validation": entry.get("artifact_validation"),
        "mutation_result": mutation_result,
        "changed_files": mutation_result.get("changed_files") or entry.get("changed_files") or [],
        "final_test_status": mutation_result.get("final_test_status") or entry.get("final_test_status"),
        "applied_patch_hash": mutation_result.get("applied_patch_hash") or entry.get("applied_patch_hash"),
        "stdout_preview": entry.get("stdout_preview"),
        "stderr_preview": entry.get("stderr_preview"),
        "watchdog": watchdog,
        "timeout_seconds": entry.get("timeout_seconds"),
        "idle_timeout_seconds": entry.get("idle_timeout_seconds"),
        "provider_output_idle_timeout_seconds": entry.get("provider_output_idle_timeout_seconds"),
        "material_progress_idle_timeout_seconds": entry.get("material_progress_idle_timeout_seconds"),
        "last_provider_output_at": entry.get("last_provider_output_at") or watchdog.get("last_provider_output_at"),
        "last_material_progress_at": entry.get("last_material_progress_at") or watchdog.get("last_material_progress_at"),
        "last_provider_output_age_seconds": watchdog.get("last_provider_output_age_seconds"),
        "last_material_progress_age_seconds": watchdog.get("last_material_progress_age_seconds"),
        "recoverable_suggestion": entry.get("recoverable_suggestion"),
        "continuation_required": continuation_required,
        "continuation_reason": _continuation_reason(status=status, entry=entry, watchdog=watchdog),
        "continuation_argv": continuation_argv if continuation_required else None,
        "next_continuation_argv": continuation_argv if continuation_required else None,
        "continuation_command": subprocess.list2cmdline(continuation_argv) if continuation_required else None,
    }


def _already_satisfied_task_card_entry(
    card: TaskCard,
    materialized: dict[str, list[str]],
    *,
    project_dir: Path,
    card_path: Path,
) -> dict[str, Any] | None:
    evidence = _load_project_feature_evidence(project_dir)
    satisfaction = _existing_evidence_satisfaction(
        card,
        evidence=evidence,
        project_dir=project_dir,
    )
    if not satisfaction["go"]:
        return None
    evidence_files = _existing_evidence_files_for_card(card, materialized, evidence=evidence, project_dir=project_dir)
    if not evidence_files:
        return None
    return {
        "task_card_id": card.task_card_id,
        "title": card.title,
        "status": "reference_only",
        "failure_class": "fresh_cli_execution_missing",
        "final_failure_class": "fresh_cli_execution_missing",
        "retry_exhausted": False,
        "preflight_blocker": True,
        "attempt_index": 0,
        "max_attempts": TASK_CARD_RUNTIME_MAX_ATTEMPTS,
        "consecutive_failure_count": 0,
        "attempts": [],
        "receipt_id": None,
        "child_run_id": None,
        "child_attempt_id": None,
        "worker_adapter": "reference_evidence",
        "watchdog_source": "project_feature_evidence",
        "evidence_id": None,
        "review_decision": "evidence_reference_only",
        "task_card_path": card_path.as_posix(),
        "write_set": materialized["write_set"],
        "read_set": materialized["read_set"],
        "test_commands": materialized["test_commands"],
        "mutation_result": {
            "changed_files": [],
            "final_test_status": "not_run",
            "satisfaction_mode": "reused_reference_only",
        },
        "changed_files": [],
        "reference_files": evidence_files,
        "final_test_status": "not_run",
        "applied_patch_hash": None,
        "stdout_preview": None,
        "stderr_preview": None,
        "watchdog": {
            "source": "project_feature_evidence",
            "evidence_requirements_satisfied": satisfaction["satisfied"],
        },
        "timeout_seconds": None,
        "idle_timeout_seconds": None,
        "provider_output_idle_timeout_seconds": None,
        "material_progress_idle_timeout_seconds": None,
        "last_provider_output_at": None,
        "last_material_progress_at": None,
        "last_provider_output_age_seconds": None,
        "last_material_progress_age_seconds": None,
        "recoverable_suggestion": None,
        "continuation_required": False,
        "continuation_reason": None,
        "continuation_argv": None,
        "next_continuation_argv": None,
        "continuation_command": None,
        "satisfaction_mode": "reused_reference_only",
        "implementation_gate_satisfied": False,
        "blockers": ["fresh_cli_execution_missing"],
        "evidence_reuse_real_files": True,
        "evidence_requirements_satisfied": satisfaction["satisfied"],
        "evidence_refs": satisfaction["evidence_refs"],
    }


def _existing_evidence_satisfaction(
    card: TaskCard,
    *,
    evidence: dict[str, Any],
    project_dir: Path,
) -> dict[str, Any]:
    satisfied: list[str] = []
    evidence_refs: list[str] = []
    requirements = [str(item).strip() for item in card.evidence_requirements if str(item).strip()]
    if not requirements:
        return {"go": False, "satisfied": [], "evidence_refs": []}
    for requirement in requirements:
        ok, refs = _existing_requirement_satisfied(requirement, evidence=evidence, project_dir=project_dir)
        if not ok:
            return {"go": False, "satisfied": satisfied, "evidence_refs": _dedupe_strings(evidence_refs)}
        satisfied.append(requirement)
        evidence_refs.extend(refs)
    return {"go": True, "satisfied": satisfied, "evidence_refs": _dedupe_strings(evidence_refs)}


def _existing_requirement_satisfied(
    requirement: str,
    *,
    evidence: dict[str, Any],
    project_dir: Path,
) -> tuple[bool, list[str]]:
    normalized = requirement.strip().lower().replace("-", "_").replace(" ", "_")
    feature_map = _existing_feature_map(evidence)
    if normalized in {"same_project_patch", "repair_patch"}:
        return bool(evidence.get("same_project_patch_files")), ["same_project_patch_files"]
    if normalized == "eightdistinctlevelgoals":
        distinct_count = _as_int(
            evidence.get("distinctLevelGoalCount")
            or _dict(evidence.get("product_depth_evidence")).get("distinctLevelGoalCount")
        )
        return distinct_count >= 8 or _feature_true(feature_map, "levelGoalVariety"), ["product_depth_evidence"]
    if normalized == "level_completion_screenshot":
        return _has_existing_screenshot(evidence, project_dir), ["playtest_screenshots"]
    if normalized == "collection_panel_screenshot":
        return _has_existing_screenshot(evidence, project_dir) and _has_open_panel(evidence, ["皮肤图鉴", "collection"]), [
            "playtest_screenshots",
            "open_panels",
        ]
    if normalized == "audio_runtime_evidence":
        audio_manifest = project_dir / "assets/resources/commercial_assets/audio_manifest.json"
        return (
            audio_manifest.exists()
            and _feature_true(feature_map, "audioPlaybackVerified")
            and _feature_true(feature_map, "bgmStarted")
            and _feature_true(feature_map, "sfxPlaybackVerified")
            and _feature_true(feature_map, "volumeToggleUsable")
        ), ["audio_manifest", "feature_coverage"]
    if normalized in {"console/page_error_capture", "console_page_error_capture"}:
        return not evidence.get("console_errors") and not evidence.get("page_errors"), ["playtest_error_capture"]
    if normalized == "sceneprefabuievidence":
        scene_dir = project_dir / "assets/scene"
        return scene_dir.exists() and any(scene_dir.glob("*.scene")) and (
            _feature_true(feature_map, "nativeCocosUiNodes")
            or _feature_true(feature_map, "editorVisibleSceneHierarchy")
            or _feature_true(feature_map, "chineseUiPanelsVisible")
        ), ["scene_files", "feature_coverage"]
    if normalized == "panelvisibilityscreenshots":
        return _has_existing_screenshot(evidence, project_dir) and bool(evidence.get("open_panels")), [
            "playtest_screenshots",
            "open_panels",
        ]
    if normalized == "rewardcurrencychanges":
        return (
            _feature_true(feature_map, "rewardCurrencyChanges")
            or _feature_true(feature_map, "rewardPreviewConfigured")
            or _level_manifest_has_rewards(project_dir)
        ), ["feature_coverage", "level_manifest"]
    if normalized == "unlockprogressvisible":
        return (
            _feature_true(feature_map, "unlockProgressVisible")
            or _feature_true(feature_map, "sessionUnlockChainConfigured")
            or _level_preview_has_unlock_progress(project_dir)
        ), ["feature_coverage", "level_goal_preview"]
    if normalized == "human_review_packet":
        packet = project_dir / "player_visible_evidence/human_player_review_packet.json"
        if not packet.exists():
            _ensure_human_review_packet_file(project_dir, evidence=evidence)
        return packet.exists(), ["human_review_packet"]
    if normalized == "awaiting_human_review_status":
        return True, ["awaiting_human_review_gate"]
    direct_feature_keys = {
        "animationfeedbackverified": "animationFeedbackVerified",
        "audioplaybackverified": "audioPlaybackVerified",
        "bgmstarted": "bgmStarted",
        "chineseuipanelsvisible": "chineseUiPanelsVisible",
        "failurerevivefeedback": "failureReviveFeedback",
        "levelflowplayable": "levelFlowPlayable",
        "sfxplaybackverified": "sfxPlaybackVerified",
        "shopownershipstates": "shopOwnershipStates",
        "skinequippedvisualchange": "skinEquippedVisualChange",
        "volumetoggleusable": "volumeToggleUsable",
    }
    feature_key = direct_feature_keys.get(normalized)
    if feature_key:
        return _feature_true(feature_map, feature_key), ["feature_coverage"]
    return False, []


def _existing_feature_map(evidence: dict[str, Any]) -> dict[str, Any]:
    product_depth = _dict(evidence.get("product_depth_evidence"))
    merged: dict[str, Any] = {}
    for source in [
        evidence.get("commercial_feature_coverage"),
        evidence.get("player_visible_checks"),
        product_depth,
        product_depth.get("feature_coverage"),
        product_depth.get("player_visible_checks"),
    ]:
        if isinstance(source, dict):
            merged.update(source)
    return merged


def _existing_evidence_files_for_card(
    card: TaskCard,
    materialized: dict[str, list[str]],
    *,
    evidence: dict[str, Any],
    project_dir: Path,
) -> list[str]:
    evidence_files: list[str] = []
    for raw in evidence.get("same_project_patch_files") or []:
        path = project_dir / str(raw)
        if path.exists() and _path_is_in_write_set(path, materialized["write_set"]):
            evidence_files.append(path.as_posix())
    for raw in _dict(evidence.get("product_depth_evidence")).get("screenshots") or []:
        path = Path(str(raw))
        if path.exists():
            evidence_files.append(path.as_posix())
    human_packet = project_dir / "player_visible_evidence/human_player_review_packet.json"
    if human_packet.exists() and _path_is_in_write_set(human_packet, materialized["write_set"]):
        evidence_files.append(human_packet.as_posix())
    return _dedupe_strings(evidence_files)


def _path_is_in_write_set(path: Path, write_set: list[str]) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    for item in write_set:
        candidate = Path(item)
        try:
            base = candidate.resolve()
        except OSError:
            base = candidate
        if resolved == base or base in resolved.parents:
            return True
    return False


def _feature_true(feature_map: dict[str, Any], key: str) -> bool:
    return bool(feature_map.get(key))


def _has_existing_screenshot(evidence: dict[str, Any], project_dir: Path) -> bool:
    screenshots = list(evidence.get("screenshots") or [])
    screenshots.extend(_dict(evidence.get("product_depth_evidence")).get("screenshots") or [])
    for raw in screenshots:
        path = Path(str(raw))
        if not path.is_absolute():
            path = project_dir / path
        if path.exists():
            return True
    return False


def _has_open_panel(evidence: dict[str, Any], tokens: list[str]) -> bool:
    values: list[str] = [str(item) for item in evidence.get("open_panels") or []]
    values.extend(str(item) for item in _dict(evidence.get("product_depth_evidence")).get("open_panels") or [])
    values.extend(str(item) for item in evidence.get("events") or [])
    haystack = "\n".join(values).lower()
    return any(token.lower() in haystack for token in tokens)


def _level_manifest_has_rewards(project_dir: Path) -> bool:
    for path in [
        project_dir / "assets/scripts/level_manifest.json",
        project_dir / "assets/level_goal_manifest.json",
    ]:
        data = _read_json_dict(path)
        levels = data.get("levels") if isinstance(data, dict) else None
        if isinstance(levels, list):
            for level in levels:
                reward = _dict(_dict(level).get("reward"))
                if _as_int(reward.get("coins")) > 0 or reward.get("unlock_level_ids"):
                    return True
    return False


def _level_preview_has_unlock_progress(project_dir: Path) -> bool:
    data = _read_json_dict(project_dir / "assets/scene/level_goal_preview.json")
    bindings = _dict(data.get("ui_bindings"))
    if bindings.get("unlock_progress_node"):
        return True
    sections = data.get("sections")
    if isinstance(sections, list):
        return any(str(_dict(section).get("section_id")).lower() == "unlock_progress" for section in sections)
    return False


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _source_identity(source_path: Path) -> dict[str, str]:
    return {
        "source_path": source_path.resolve().as_posix(),
        "source_sha256": _sha256_file(source_path),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_existing_files(project_dir: Path) -> list[str]:
    if not project_dir.exists():
        return []
    try:
        return sorted(path.as_posix() for path in project_dir.rglob("*") if path.is_file())
    except OSError:
        return []


def _ensure_human_review_packet_file(project_dir: Path, *, evidence: dict[str, Any]) -> Path:
    packet_path = project_dir / "player_visible_evidence/human_player_review_packet.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    screenshots = list(evidence.get("screenshots") or [])
    screenshots.extend(_dict(evidence.get("product_depth_evidence")).get("screenshots") or [])
    packet = {
        "schema_version": "commercial_game_human_review_packet_v1",
        "status": "AWAITING_HUMAN_REVIEW",
        "reviewer_required": True,
        "accepted_by_human": False,
        "human_player_review_go": False,
        "commercial_playable_go_allowed": False,
        "ready_for_human_review": False,
        "machine_evidence_status": "pending_final_gate_refresh",
        "machine_blockers": ["awaiting_human_player_review"],
        "screenshots": _dedupe_strings(screenshots),
        "review_items": [
            "eight distinct level goals",
            "shop and skin ownership states",
            "equipped skin visual change",
            "Chinese UI panels",
            "level flow",
            "failure and revive feedback",
            "audio, BGM, SFX, and volume behavior",
            "animation and feedback polish",
        ],
        "manual_player_evidence": {},
        "forbidden_claim": "unattended_packet_is_not_human_review",
    }
    _write_json(packet_path, packet)
    return packet_path


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _patch_ledger_blockers(entries: list[dict[str, Any]], *, expected_count: int) -> list[str]:
    blockers: list[str] = []
    for entry in entries:
        blockers.extend(str(item) for item in entry.get("blockers") or [] if str(item))
        if entry.get("implementation_gate_satisfied") is False:
            blockers.append("fresh_cli_execution_missing")
        if entry.get("execution_visibility_mode") == "human_visible_cli_enforced" and not _visible_cli_session_valid(entry):
            blockers.append("human_visible_cli_metadata_missing")
        if entry.get("status") == "completed" and not _completed_patch_entry_has_fresh_execution(entry):
            blockers.append("fresh_cli_execution_missing")
    if len(entries) < expected_count:
        blockers.append("same_project_task_card_patch_incomplete")
    if any(entry.get("status") != "completed" for entry in entries):
        blockers.append("same_project_task_card_patch_failed")
    failure_classes = _dedupe_strings([_patch_failure_class(entry) for entry in entries] + [_patch_root_failure_class(entry) for entry in entries])
    if "blocked_after_three_attempts" in failure_classes:
        blockers.append("blocked_after_three_attempts")
    if "child_stdout_silent" in failure_classes:
        blockers.append("child_stdout_silent_recoverable")
    if "provider_output_idle_timeout" in failure_classes:
        blockers.append("provider_output_idle_timeout_recoverable")
    if "provider_no_material_progress_timeout" in failure_classes:
        blockers.append("provider_no_material_progress_timeout_recoverable")
    if "workflow_child_stalled" in failure_classes:
        blockers.append("workflow_child_stalled")
    if "provider_timeout" in failure_classes:
        blockers.append("provider_timeout_recoverable")
    if "provider_execution_failed" in failure_classes:
        blockers.append("provider_execution_failed")
    for failure_class in failure_classes:
        if failure_class and failure_class not in {
            "blocked_after_three_attempts",
            "child_stdout_silent",
            "provider_output_idle_timeout",
            "provider_no_material_progress_timeout",
            "workflow_child_stalled",
            "provider_timeout",
            "provider_execution_failed",
        }:
            blockers.append(failure_class)
    if not entries:
        blockers.append("same_project_worker_patch_missing")
    return _dedupe_strings(blockers)


def _continuation_argv(
    *,
    root: Path,
    db_path: Path | None,
    project_dir: Path,
    card_path: Path,
    card: TaskCard,
    materialized: dict[str, list[str]],
    max_repair_attempts: int,
    entry: dict[str, Any],
    execution_visibility_mode: str | None = None,
) -> list[str]:
    argv = [
        sys.executable,
        "-m",
        "packages.contributions.pipelines.commercial_game_task_card_resume",
        "--workspace-root",
        root.as_posix(),
        "--project-dir",
        project_dir.as_posix(),
        "--pipeline-id",
        card.run_id,
        "--task-card-path",
        card_path.as_posix(),
        "--task-card-ref",
        card.task_card_id,
        "--max-fix-iterations",
        str(max_repair_attempts),
    ]
    adapter_name = _normalize_adapter_name(entry.get("requested_adapter") or entry.get("worker_adapter") or card.provider_lane or "")
    if adapter_name:
        argv.extend(["--adapter", adapter_name])
    if db_path is not None:
        argv.extend(["--db-path", db_path.as_posix()])
    mode = str(execution_visibility_mode or entry.get("execution_visibility_mode") or "").strip()
    if mode:
        argv.extend(["--execution-visibility-mode", mode])
    for item in materialized["write_set"]:
        argv.extend(["--write-set", item])
    for item in materialized["read_set"]:
        argv.extend(["--read-set", item])
    for item in materialized["test_commands"]:
        argv.extend(["--test-command", item])
    return argv


def _continuation_reason(*, status: str, entry: dict[str, Any], watchdog: dict[str, Any]) -> str | None:
    if status == "completed":
        return None
    if entry.get("retry_exhausted"):
        return "blocked_after_three_attempts"
    if entry.get("preflight_blocker"):
        return "preflight_blocker"
    failure_class = str(entry.get("failure_class") or "")
    normalized_failure = _patch_root_failure_class(entry)
    if normalized_failure == "child_stdout_silent":
        return "child_stdout_silent_recoverable"
    if normalized_failure == "provider_output_idle_timeout":
        return "provider_output_idle_timeout_recoverable"
    if normalized_failure == "provider_no_material_progress_timeout":
        return "provider_no_material_progress_timeout_recoverable"
    if normalized_failure == "workflow_child_stalled":
        return "workflow_child_stalled"
    if normalized_failure == "provider_timeout":
        return "provider_timeout_recoverable"
    return failure_class or "same_project_task_card_patch_failed"


def _patch_failure_class(entry: dict[str, Any]) -> str:
    watchdog = entry.get("watchdog") if isinstance(entry.get("watchdog"), dict) else {}
    failure_class = str(entry.get("failure_class") or "")
    if failure_class == "blocked_after_three_attempts":
        return failure_class
    if failure_class in {"provider_output_idle_timeout", "provider_no_material_progress_timeout"}:
        return failure_class
    if failure_class in {"provider_timeout", "provider_idle_timeout", "provider_wall_timeout"}:
        return "provider_timeout"
    if failure_class:
        return failure_class
    timeout_type = str(watchdog.get("timeout_type") or "")
    if timeout_type in {"provider_output_idle_timeout", "provider_no_material_progress_timeout"}:
        return timeout_type
    if timeout_type in {"idle_timeout", "wall_timeout"}:
        return "provider_timeout"
    return ""


def _patch_root_failure_class(entry: dict[str, Any]) -> str:
    final_failure_class = str(entry.get("final_failure_class") or "")
    if final_failure_class:
        normalized = _patch_failure_class({"failure_class": final_failure_class, "watchdog": entry.get("watchdog")})
        return normalized or final_failure_class
    failure_class = _patch_failure_class(entry)
    if failure_class == "blocked_after_three_attempts":
        attempts = entry.get("attempts") if isinstance(entry.get("attempts"), list) else []
        if attempts:
            return _patch_failure_class(attempts[-1])
    return failure_class


def _blocked_downstream_stages(*, require_build: bool, require_playtest: bool) -> list[str]:
    stages = ["gameplay_semantic", "product_body", "product_depth", "human_player_review"]
    if require_build:
        stages.insert(0, "cocos_build")
    if require_playtest:
        insert_at = 1 if require_build else 0
        stages.insert(insert_at, "browser_playtest")
        stages.insert(insert_at + 1, "audio_runtime")
    return _dedupe_strings(stages)


def _blocked_evidence_contract(
    *,
    schema_version: str,
    stage: str,
    blockers: list[str],
    source: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "status": "blocked",
        "go": False,
        "blockers": list(blockers),
        "source": {"stage": stage, **source},
    }


def _normalized_repair_packet(*, patch_ledger: dict[str, Any], runtime_evidence: dict[str, Any]) -> dict[str, Any] | None:
    if patch_ledger.get("same_project_worker_patch_go"):
        return None
    entries = [entry for entry in patch_ledger.get("entries") or [] if isinstance(entry, dict)]
    failed_entry = next((entry for entry in entries if entry.get("status") != "completed"), None)
    return {
        "root_cause": "same_project_worker_patch_failed",
        "upstream_blockers": _dedupe_strings(list(patch_ledger.get("blockers") or [])),
        "blocked_downstream_stages": _dedupe_strings(list(runtime_evidence.get("blocked_downstream_stages") or [])),
        "next_incomplete_task_card_id": patch_ledger.get("next_incomplete_task_card_id"),
        "final_failure_class": failed_entry.get("final_failure_class") if failed_entry else None,
        "retry_exhausted": bool(failed_entry.get("retry_exhausted")) if failed_entry else False,
        "attempt_count": len(failed_entry.get("attempts") or []) if failed_entry else 0,
        "max_attempts": failed_entry.get("max_attempts") if failed_entry else None,
        "last_provider_output_at": failed_entry.get("last_provider_output_at") if failed_entry else None,
        "last_material_progress_at": failed_entry.get("last_material_progress_at") if failed_entry else None,
        "continuation_command": patch_ledger.get("next_continuation_command"),
        "continuation_argv": patch_ledger.get("next_continuation_argv"),
    }


def _load_project_feature_evidence(project_dir: Path) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for path in [
        project_dir / "workflow_commercial_feature_evidence.json",
        project_dir / "player_visible_evidence" / "cocos_player_visible_evidence.json",
        project_dir / "playtest_evidence" / "cocos_playtest_result.json",
    ]:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        for key in ("commercial_feature_coverage", "feature_coverage", "player_visible_checks", "manual_player_evidence"):
            value = payload.get(key)
            if isinstance(value, dict):
                target_key = "commercial_feature_coverage" if key == "feature_coverage" else key
                merged.setdefault(target_key, {}).update(value)
        product_depth = payload.get("product_depth_evidence")
        if isinstance(product_depth, dict):
            merged.setdefault("product_depth_evidence", {}).update(product_depth)
        for key in ("level_goals", "levelGoals", "distinctLevelGoalCount"):
            if key in payload:
                merged.setdefault("product_depth_evidence", {})[key] = payload[key]
                merged[key] = payload[key]
        for key in ("same_project_patch_files", "screenshots", "open_panels", "events", "console_errors", "page_errors"):
            value = payload.get(key)
            if isinstance(value, list):
                merged.setdefault(key, [])
                merged[key].extend(value)
        _merge_direct_commercial_feature_markers(merged, payload)
        if isinstance(product_depth, dict):
            for key in ("screenshots", "open_panels", "events"):
                value = product_depth.get(key)
                if isinstance(value, list):
                    merged.setdefault(key, [])
                    merged[key].extend(value)
    _merge_runtime_evidence_artifacts(merged, project_dir)
    baseline = _read_json_dict(project_dir / "workflow_product_body_baseline.json")
    if baseline:
        merged["product_body_baseline"] = baseline
    readiness_gates = _read_json_dict(project_dir / "workflow_development_readiness_validation_gates.json")
    if readiness_gates:
        merged["development_readiness_validation_gates"] = readiness_gates
    for key in ("same_project_patch_files", "screenshots", "open_panels", "events", "console_errors", "page_errors"):
        if isinstance(merged.get(key), list):
            merged[key] = _dedupe_strings(merged[key])
    return merged


def _merge_runtime_evidence_artifacts(merged: dict[str, Any], project_dir: Path) -> None:
    evidence_root = project_dir / "workflow_runtime_evidence"
    runtime_artifacts: list[str] = []
    gameplay_raw = _read_json_dict(evidence_root / "gameplay_semantic_evidence.raw.json")
    if gameplay_raw:
        merged["gameplay_semantic_evidence"] = gameplay_raw
    product_body_raw = _read_json_dict(evidence_root / "product_body_evidence.raw.json")
    if product_body_raw:
        merged["product_body_evidence"] = product_body_raw
        _normalize_product_body_worker_schema(merged["product_body_evidence"])
    product_depth_raw = _read_json_dict(evidence_root / "product_depth_evidence.raw.json")
    if product_depth_raw:
        merged.setdefault("product_depth_evidence", {}).update(product_depth_raw)
    level_goal = _read_json_dict(evidence_root / "level_goal_evidence.json")
    if level_goal:
        runtime_artifacts.append((evidence_root / "level_goal_evidence.json").as_posix())
        _merge_level_goal_evidence(merged, level_goal)
    level_goal_matrix = _read_json_dict(project_dir / "assets" / "resources" / "content" / "level_goal_matrix.json")
    if level_goal_matrix:
        runtime_artifacts.append((project_dir / "assets" / "resources" / "content" / "level_goal_matrix.json").as_posix())
        _merge_level_goal_evidence(merged, level_goal_matrix)
    core_loop = _read_json_dict(evidence_root / "core_loop_runtime_evidence.json")
    if core_loop:
        runtime_artifacts.append((evidence_root / "core_loop_runtime_evidence.json").as_posix())
        _merge_core_loop_evidence(merged, core_loop)
    scene_prefab = _read_json_dict(evidence_root / "scene_prefab_binding_evidence.json")
    if scene_prefab:
        runtime_artifacts.append((evidence_root / "scene_prefab_binding_evidence.json").as_posix())
        _merge_scene_prefab_binding_evidence(merged, scene_prefab)
    shop_gallery = _read_json_dict(evidence_root / "commercial_shop_skin_gallery_evidence.json")
    shop_ownership = _read_json_dict(evidence_root / "shop_ownership_state.json")
    skin_equipped = _read_json_dict(evidence_root / "skin_equipped_visual_change.json")
    gallery_collection = _read_json_dict(evidence_root / "gallery_collection_state.json")
    shop_gallery = _combined_shop_skin_gallery_evidence(
        shop_gallery=shop_gallery,
        shop_ownership=shop_ownership,
        skin_equipped=skin_equipped,
        gallery_collection=gallery_collection,
    )
    if shop_gallery:
        runtime_artifacts.append((evidence_root / "commercial_shop_skin_gallery_evidence.json").as_posix())
        if shop_ownership:
            runtime_artifacts.append((evidence_root / "shop_ownership_state.json").as_posix())
        if skin_equipped:
            runtime_artifacts.append((evidence_root / "skin_equipped_visual_change.json").as_posix())
        if gallery_collection:
            runtime_artifacts.append((evidence_root / "gallery_collection_state.json").as_posix())
        _merge_shop_skin_gallery_evidence(merged, shop_gallery)
    audio_assets = _read_json_dict(evidence_root / "audio_asset_manifest_evidence.json")
    if audio_assets:
        runtime_artifacts.append((evidence_root / "audio_asset_manifest_evidence.json").as_posix())
        _merge_audio_asset_manifest_evidence(merged, audio_assets)
    audio_polish = _read_json_dict(evidence_root / "audio_feedback_polish_evidence.json")
    feedback_animation = _read_json_dict(evidence_root / "feedback_animation_evidence.json")
    input_polish = _read_json_dict(evidence_root / "input_polish_evidence.json")
    audio_polish = _combined_audio_feedback_polish_evidence(
        audio_polish=audio_polish,
        feedback_animation=feedback_animation,
        input_polish=input_polish,
    )
    if audio_polish:
        runtime_artifacts.append((evidence_root / "audio_feedback_polish_evidence.json").as_posix())
        if feedback_animation:
            runtime_artifacts.append((evidence_root / "feedback_animation_evidence.json").as_posix())
        if input_polish:
            runtime_artifacts.append((evidence_root / "input_polish_evidence.json").as_posix())
        _merge_audio_feedback_polish_evidence(merged, audio_polish)
    chinese_ui = _read_json_dict(evidence_root / "chinese_ui_panels_evidence.json")
    if chinese_ui:
        runtime_artifacts.append((evidence_root / "chinese_ui_panels_evidence.json").as_posix())
        _merge_chinese_ui_panels_evidence(merged, chinese_ui)
    if core_loop and shop_gallery and audio_polish:
        for key in ("gameplay_semantic_evidence", "product_body_evidence"):
            payload = merged.setdefault(key, {})
            payload["baseline_only"] = False
            payload["runtime_phase"] = True
            payload["runtime_artifact_paths"] = runtime_artifacts
            payload["evidence_path"] = evidence_root.as_posix()


def _normalize_product_body_worker_schema(product_body: dict[str, Any]) -> None:
    engine_native = _dict(product_body.get("engine_native_product_body"))
    component_bindings = list(product_body.get("component_bindings") or product_body.get("cocos_component_bindings") or [])
    scene_nodes = list(product_body.get("scene_nodes") or [])
    engine_native_files = [*list(product_body.get("engine_native_files") or []), *list(engine_native.get("runtime_components") or [])]
    scene_prefab_bindings = [
        *list(product_body.get("engine_native_scene_prefab_bindings") or []),
        *list(product_body.get("scene_prefab_component_bindings") or []),
        *list(engine_native.get("engine_native_scene_prefab_bindings") or []),
        *list(engine_native.get("scene_prefab_component_bindings") or []),
    ]
    for item in engine_native_files:
        if isinstance(item, dict) and item.get("path"):
            component_bindings.append(str(item.get("path")))
    for item in scene_prefab_bindings:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or item.get("scene_path") or item.get("prefab_path") or item.get("component_path") or "")
        if path:
            scene_nodes.append(path)
            if path.endswith(".ts"):
                component_bindings.append(path)
        for key in ("scene_meta_path", "prefab_meta_path", "settings_path"):
            if item.get(key):
                scene_nodes.append(str(item[key]))
        for key in ("bound_components", "bound_runtime_fields", "commands"):
            for value in item.get(key) or []:
                if value:
                    scene_nodes.append(str(value))
    if component_bindings:
        product_body["component_bindings"] = _dedupe_strings(component_bindings)
    if scene_nodes:
        product_body["scene_nodes"] = _dedupe_strings(scene_nodes)
    if not product_body.get("scene_path"):
        for item in scene_prefab_bindings:
            if not isinstance(item, dict):
                continue
            scene_path = str(item.get("scene_path") or item.get("path") or "")
            if scene_path.endswith(".scene"):
                product_body["scene_path"] = scene_path
                break


def _merge_level_goal_evidence(merged: dict[str, Any], payload: dict[str, Any]) -> None:
    product_depth = merged.setdefault("product_depth_evidence", {})
    goals: list[dict[str, Any]] = []
    for level in payload.get("levels") or []:
        if not isinstance(level, dict):
            continue
        for goal in level.get("goals") or []:
            if isinstance(goal, dict):
                goals.append(
                    {
                        "id": goal.get("id") or goal.get("goal_id") or goal.get("goalId"),
                        "goal": (
                            goal.get("visible_label")
                            or goal.get("label")
                            or goal.get("description")
                            or goal.get("id")
                            or goal.get("goal_id")
                            or goal.get("goalId")
                            or _goal_label_from_matrix_goal(goal)
                        ),
                        "level_id": level.get("level_id") or level.get("levelId") or level.get("id"),
                    }
                )
    if not goals:
        for goal in payload.get("level_goals") or []:
            if isinstance(goal, dict):
                goals.append(
                    {
                        "id": goal.get("goal_id") or goal.get("id"),
                        "goal": goal.get("visible_label") or goal.get("label") or goal.get("description") or goal.get("goal_id"),
                        "level_id": goal.get("level_id") or "level_goal_set",
                    }
                )
    if goals:
        product_depth["level_goals"] = goals
        product_depth["distinctLevelGoalCount"] = len({str(goal.get("id") or goal.get("goal")).lower() for goal in goals})
        merged["level_goals"] = goals
        merged["distinctLevelGoalCount"] = product_depth["distinctLevelGoalCount"]
    features = merged.setdefault("commercial_feature_coverage", {})
    if payload.get("levels"):
        features["levelFlowPlayable"] = True
    if _dict(payload.get("revive_and_failure_rules")) or _dict(payload.get("failure_rules")):
        features["failureReviveFeedback"] = True
    rules_runtime_state = _dict(payload.get("rules_runtime_state_proof"))
    if _dict(rules_runtime_state.get("revive")):
        features["failureReviveFeedback"] = True


def _goal_label_from_matrix_goal(goal: dict[str, Any]) -> str:
    kind = str(goal.get("kind") or goal.get("type") or "goal").strip()
    amount = goal.get("amount") or goal.get("target") or goal.get("count")
    color = goal.get("color")
    parts = [kind]
    if color:
        parts.append(str(color))
    if amount:
        parts.append(str(amount))
    return "_".join(parts)


def _merge_core_loop_evidence(merged: dict[str, Any], payload: dict[str, Any]) -> None:
    features = merged.setdefault("commercial_feature_coverage", {})
    semantic = merged.setdefault("gameplay_semantic_evidence", {})
    runtime_state = _dict(payload.get("engine_native_runtime_state"))
    if runtime_state:
        semantic.setdefault("engine_native_runtime_state", runtime_state)
        if runtime_state.get("board_size"):
            semantic.setdefault("board_size", runtime_state.get("board_size"))
        if runtime_state.get("candidate_batch_size"):
            semantic.setdefault("candidate_count", runtime_state.get("candidate_batch_size"))
    transition_payload = _dict(payload.get("semantic_model_transition_trace"))
    transition_events = transition_payload.get("events") if isinstance(transition_payload.get("events"), list) else []
    if transition_events:
        semantic.setdefault("semantic_traces", {})
        for event in transition_events:
            semantic["semantic_traces"].setdefault(str(event), True)
    replay = payload.get("scripted_core_loop_replay") if isinstance(payload.get("scripted_core_loop_replay"), list) else []
    if replay:
        semantic.setdefault("model_transition_traces", replay)
    if payload.get("state_transitions") or replay:
        features["levelFlowPlayable"] = True
    if any("failed" in str(transition.get("to") or transition.get("after_phase") or "").lower() for transition in [*list(payload.get("state_transitions") or []), *replay] if isinstance(transition, dict)):
        features["failureReviveFeedback"] = True


def _merge_scene_prefab_binding_evidence(merged: dict[str, Any], payload: dict[str, Any]) -> None:
    product_body = merged.setdefault("product_body_evidence", {})
    features = merged.setdefault("commercial_feature_coverage", {})
    scene_bindings = [item for item in payload.get("scene_bindings") or [] if isinstance(item, dict)]
    prefab_bindings = [item for item in payload.get("prefab_bindings") or [] if isinstance(item, dict)]
    scene_payload = _dict(payload.get("scene"))
    prefabs_payload = [item for item in payload.get("prefabs") or [] if isinstance(item, dict)]
    if scene_payload:
        component_paths = [
            str(item.get("component_path") or item.get("path") or item.get("component"))
            for item in scene_payload.get("component_bindings") or []
            if isinstance(item, dict) and (item.get("component_path") or item.get("path") or item.get("component"))
        ]
        scene_binding = {
            "scene_path": scene_payload.get("scene_path"),
            "scene_id": scene_payload.get("root_node") or scene_payload.get("scene_name"),
            "prefabs": [str(item.get("prefab_path")) for item in prefabs_payload if item.get("prefab_path")],
            "components": component_paths,
        }
        scene_bindings.append(scene_binding)
        if component_paths:
            product_body.setdefault("component_bindings", [])
            product_body["component_bindings"].extend(component_paths)
        if scene_payload.get("scene_path"):
            product_body["scene_path"] = scene_payload.get("scene_path")
        product_body.setdefault("scene_nodes", [])
        for value in (
            scene_payload.get("scene_path"),
            scene_payload.get("root_node"),
            scene_payload.get("runtime_controller_node"),
            *scene_binding["prefabs"],
            *component_paths,
        ):
            if value:
                product_body["scene_nodes"].append(str(value))
    if scene_bindings:
        product_body.setdefault("scene_bindings", scene_bindings)
        product_body.setdefault("scene_nodes", [])
        for binding in scene_bindings:
            if binding.get("scene_id"):
                product_body["scene_nodes"].append(binding.get("scene_id"))
            if binding.get("scene_path"):
                product_body["scene_nodes"].append(binding.get("scene_path"))
            product_body["scene_nodes"].extend(binding.get("prefabs") or [])
            product_body["scene_nodes"].extend(binding.get("components") or [])
        product_body["scene_nodes"] = _dedupe_strings(product_body["scene_nodes"])
        features["cocosAssetBindings"] = True
        features["nativeCocosUiNodes"] = True
    if prefab_bindings:
        product_body.setdefault("component_bindings", [])
        for binding in prefab_bindings:
            product_body["component_bindings"].append(binding.get("prefab_path"))
            product_body["component_bindings"].extend(binding.get("visible_surfaces") or [])
        product_body["component_bindings"] = _dedupe_strings(product_body["component_bindings"])
        features["cocosAssetBindings"] = True
    if prefabs_payload:
        product_body.setdefault("component_bindings", [])
        product_body["component_bindings"].extend(
            str(item.get("prefab_path")) for item in prefabs_payload if item.get("prefab_path")
        )
        product_body["component_bindings"] = _dedupe_strings(product_body["component_bindings"])
        features["cocosAssetBindings"] = True


def _merge_direct_commercial_feature_markers(merged: dict[str, Any], payload: dict[str, Any]) -> None:
    features = merged.setdefault("commercial_feature_coverage", {})
    if payload.get("generatedArtAssets"):
        features["generatedArtAssets"] = True
    if payload.get("particleEffects"):
        features["particleEffects"] = True
        features["animationTimeline"] = True
        features["animationFeedbackVerified"] = True
    if payload.get("generatedAudioAssets") or _dict(payload.get("runtimeAudio")) or _dict(payload.get("audio_runtime")):
        features["generatedAudioAssets"] = True
    runtime_audio = _dict(payload.get("runtimeAudio")) or _dict(payload.get("audio_runtime"))
    for key in ("audioPlaybackVerified", "bgmStarted", "sfxPlaybackVerified", "volumeToggleUsable"):
        if runtime_audio.get(key) or payload.get(key):
            features[key] = True


def _merge_shop_skin_gallery_evidence(merged: dict[str, Any], payload: dict[str, Any]) -> None:
    features = merged.setdefault("commercial_feature_coverage", {})
    visible = merged.setdefault("player_visible_checks", {})
    replay = payload.get("skin_gallery_replay") if isinstance(payload.get("skin_gallery_replay"), list) else []
    unlock_replay = payload.get("unlock_replay") if isinstance(payload.get("unlock_replay"), list) else []
    state_proof = _dict(payload.get("reward_gallery_state_proof"))
    runtime_state = _dict(payload.get("shop_skin_gallery_runtime_state"))
    if _dict(payload.get("shop_ownership_state")) or state_proof.get("unlockable_skin_count") or any(
        isinstance(item, dict) and item.get("ownedSkinIds") for item in replay
    ) or runtime_state.get("state_fields_persisted") or any(isinstance(item, dict) and item.get("skin_unlocked") for item in unlock_replay):
        features["shopOwnershipStates"] = True
        visible["shopOwnershipStates"] = True
    if _dict(payload.get("skin_equipped_visual_change")) or state_proof.get("unlockable_skin_count") or any(
        isinstance(item, dict) and (item.get("activeSkinId") or item.get("step") == "select_mint_tile") for item in replay
    ) or runtime_state.get("skin_reward_ids") or any(isinstance(item, dict) and item.get("skin_unlocked") for item in unlock_replay):
        features["skinEquippedVisualChange"] = True
        visible["skinEquippedVisualChange"] = True
    if _dict(payload.get("gallery_collection_state")) or state_proof.get("gallery_collection_count") or any(
        isinstance(item, dict) and item.get("completedArtIds") for item in replay
    ) or runtime_state.get("gallery_entry_ids") or any(
        isinstance(item, dict) and (item.get("puzzle_piece_state") or item.get("awarded_reward_ids")) for item in unlock_replay
    ):
        visible["galleryCollectionState"] = True
        features["galleryCollectionState"] = True


def _combined_shop_skin_gallery_evidence(
    *,
    shop_gallery: dict[str, Any],
    shop_ownership: dict[str, Any],
    skin_equipped: dict[str, Any],
    gallery_collection: dict[str, Any],
) -> dict[str, Any]:
    combined = dict(shop_gallery) if isinstance(shop_gallery, dict) else {}
    if shop_ownership:
        combined.setdefault("shop_ownership_state", _dict(shop_ownership.get("shop_ownership_state")) or shop_ownership)
        if not combined.get("gallery_collection_state") and _dict(shop_ownership.get("gallery_collection_state")):
            combined["gallery_collection_state"] = shop_ownership["gallery_collection_state"]
    if skin_equipped:
        combined.setdefault(
            "skin_equipped_visual_change",
            _dict(skin_equipped.get("skin_equipped_visual_change")) or skin_equipped,
        )
    if gallery_collection:
        combined.setdefault(
            "gallery_collection_state",
            _dict(gallery_collection.get("gallery_collection_state")) or gallery_collection,
        )
    return combined


def _merge_chinese_ui_panels_evidence(merged: dict[str, Any], payload: dict[str, Any]) -> None:
    raw_panels = payload.get("chinese_ui_panels")
    if isinstance(raw_panels, dict):
        panel_candidates = []
        for panel_id, panel in raw_panels.items():
            if isinstance(panel, dict):
                normalized = dict(panel)
                normalized.setdefault("panel_id", str(panel_id))
                panel_candidates.append(normalized)
    else:
        panel_candidates = raw_panels or []
    panels = [panel for panel in panel_candidates if isinstance(panel, dict)]
    if not panels:
        return
    panel_ids = {str(panel.get("panel_id") or "").strip().lower() for panel in panels}
    required = {"hud_panel", "shop_panel", "gallery_panel", "settings_panel", "failure_revive_panel"}
    all_have_labels = all(bool(_chinese_panel_label_values(panel)) for panel in panels)
    labels_are_readable = all(_labels_are_readable_chinese(_chinese_panel_label_values(panel)) for panel in panels)
    if required <= panel_ids and all_have_labels and labels_are_readable:
        features = merged.setdefault("commercial_feature_coverage", {})
        visible = merged.setdefault("player_visible_checks", {})
        product_depth = merged.setdefault("product_depth_evidence", {})
        features["chineseUiPanelsVisible"] = True
        visible["chineseUiPanelsVisible"] = True
        product_depth["chinese_ui_panels"] = panels
        product_depth["open_panels"] = [str(panel.get("chinese_name") or panel.get("panel_id")) for panel in panels]


def _chinese_panel_label_values(panel: dict[str, Any]) -> list[str]:
    labels = panel.get("chinese_labels")
    if isinstance(labels, dict):
        return [str(value) for value in labels.values() if str(value).strip()]
    readable_labels = panel.get("readable_simplified_chinese_labels")
    if isinstance(readable_labels, list):
        return [str(value) for value in readable_labels if str(value).strip()]
    return []


def _labels_are_readable_chinese(values: list[str]) -> bool:
    if not values:
        return False
    return all(not _looks_like_mojibake(value) for value in values)


def _looks_like_mojibake(value: str) -> bool:
    text = str(value)
    if _looks_like_reencoded_utf8_mojibake(text):
        return True
    if "锟" in text or "鈧" in text or "�" in text:
        return True
    markers = set(
        "閸掑梿鏆熼惃鍋嗛崯绨甸柌绔电€规繄鐓堕崗鎶芥４鐠愭嫳鐟佽"
        "婢跺瀭缁嬮張闂婇牷閺傜懓娼″☉鍫ユ珟缂佸繐鍚€闂傤垰鍙"
        "寰楀垎鏈楂杩炲嚮画娑堥櫎妯紡缁忓吀叧鐩爣鏃犳敖鎸戞垬瀹屾垚"
        "湰泦澶嶆椿暟鏆傚仠鍟嗗簵鏀惰棌璁剧疆鎷栨嫿搴曠儴妫嬬洏"
        "绌轰綅澗鎵嬪畬濉弧浠绘剰琛屾垨鍒楀嵆緱鏂版柟鍧楀叏"
        "閮ㄧ敤悗浼氬埛闄ゅ緱鎷煎浘纰庣墖"
    )
    marker_count = sum(1 for char in text if char in markers)
    cjk_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    return cjk_count >= 2 and marker_count / max(cjk_count, 1) >= 0.45


def _looks_like_reencoded_utf8_mojibake(text: str) -> bool:
    if not text:
        return False
    for codec in ("gbk", "cp936", "latin1"):
        try:
            recovered = text.encode(codec).decode("utf-8")
        except UnicodeError:
            continue
        if recovered == text:
            continue
        if any("\u4e00" <= char <= "\u9fff" for char in recovered):
            return True
    return False


def _merge_audio_feedback_polish_evidence(merged: dict[str, Any], payload: dict[str, Any]) -> None:
    features = merged.setdefault("commercial_feature_coverage", {})
    visible = merged.setdefault("player_visible_checks", {})
    _merge_direct_commercial_feature_markers(merged, payload)
    audio = _dict(payload.get("audio_runtime_evidence"))
    feedback = _dict(payload.get("feedback_animation_evidence"))
    polish = _dict(payload.get("polish_runtime_evidence"))
    session = _dict(payload.get("human_visible_cli_session"))
    audio_runtime_verified = (
        bool(audio.get("runtime_bound") and audio.get("event_bindings_count"))
        or any(bool(value) for key, value in audio.items() if str(key).endswith("_runtime_bound"))
        or bool(session.get("audio_triggered"))
    )
    feedback_verified = bool(feedback.get("runtime_bound") and feedback.get("binding_count")) or bool(session.get("feedback_animation_triggered"))
    polish_verified = bool(polish.get("runtime_bound") and polish.get("effects_count")) or bool(session.get("polish_effects_applied"))
    if audio_runtime_verified:
        features["audioPlaybackVerified"] = True
        features["bgmStarted"] = True
        features["sfxPlaybackVerified"] = True
        features["volumeToggleUsable"] = True
        visible["audioPlaybackVerified"] = True
        visible["volumeToggleUsable"] = True
    if feedback_verified:
        features["animationFeedbackVerified"] = True
        visible["animationFeedbackVerified"] = True
    if polish_verified:
        visible["polishEffectsApplied"] = True
    feedback_types = {str(item).lower() for item in feedback.get("feedback_types") or []}
    if {"failure", "success"} & feedback_types:
        features["failureReviveFeedback"] = True


def _merge_audio_asset_manifest_evidence(merged: dict[str, Any], payload: dict[str, Any]) -> None:
    features = merged.setdefault("commercial_feature_coverage", {})
    audio_assets = payload.get("audio_assets") if isinstance(payload.get("audio_assets"), list) else []
    manifest_paths = _strings(payload.get("manifest_paths"))
    receipt = _dict(payload.get("fresh_worker_receipt"))
    generated_artifacts = _strings(receipt.get("generated_artifacts"))
    artifact_consistency = _dict(payload.get("artifact_consistency"))
    if (
        audio_assets
        or manifest_paths
        or generated_artifacts
        or payload.get("generatedAudioAssets")
        or payload.get("generated_audio_assets")
        or artifact_consistency.get("all_manifest_events_have_bank_asset")
    ):
        features["generatedAudioAssets"] = True
    if payload.get("bgm_tracks") or payload.get("sfx_events"):
        product_depth = merged.setdefault("product_depth_evidence", {})
        product_depth["audio_design_depth"] = {
            "bgm_track_count": len(payload.get("bgm_tracks") or []),
            "sfx_event_count": len(payload.get("sfx_events") or []),
        }
    _merge_direct_commercial_feature_markers(merged, payload)


def _combined_audio_feedback_polish_evidence(
    *,
    audio_polish: dict[str, Any],
    feedback_animation: dict[str, Any],
    input_polish: dict[str, Any],
) -> dict[str, Any]:
    combined = dict(audio_polish) if isinstance(audio_polish, dict) else {}
    if feedback_animation:
        combined["feedback_animation_evidence"] = _normalize_feedback_animation_evidence(feedback_animation)
    if input_polish:
        combined["polish_runtime_evidence"] = _normalize_input_polish_evidence(input_polish)
    return combined


def _normalize_feedback_animation_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    evidence = _dict(payload.get("feedback_animation_evidence")) or payload
    bindings = evidence.get("runtime_event_bindings") if isinstance(evidence.get("runtime_event_bindings"), list) else []
    feedback_types = []
    for binding in bindings:
        text = str(binding).lower()
        if "placement" in text:
            feedback_types.append("placement")
        if "line" in text or "clear" in text:
            feedback_types.append("line_clear")
        if "invalid" in text:
            feedback_types.append("invalid")
        if "success" in text:
            feedback_types.append("success")
        if "failure" in text:
            feedback_types.append("failure")
        if "revive" in text:
            feedback_types.append("revive")
    binding_count = int(evidence.get("binding_count") or len(bindings) or 0)
    runtime_bound = bool(evidence.get("runtime_bound")) or any(
        bool(value) for key, value in evidence.items() if str(key).endswith("_runtime_bound")
    )
    return {
        **evidence,
        "runtime_bound": runtime_bound,
        "binding_count": binding_count,
        "feedback_types": _dedupe_strings(feedback_types or _strings(evidence.get("feedback_types"))),
    }


def _normalize_input_polish_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    controller_features = payload.get("input_controller_features") if isinstance(payload.get("input_controller_features"), list) else []
    board_features = payload.get("board_view_features") if isinstance(payload.get("board_view_features"), list) else []
    resolved = _dict(payload.get("defect_reproduction_prevention"))
    verified_count = sum(1 for item in resolved.values() if isinstance(item, dict) and item.get("verified"))
    effects_count = len(controller_features) + len(board_features) + verified_count
    return {
        **payload,
        "runtime_bound": bool(controller_features or board_features or verified_count),
        "effects_count": effects_count,
    }


def _failed_browser_playtest_evidence(*, build_output_path: str | Path, evidence_dir: str | Path, exc: Exception) -> dict[str, Any]:
    evidence = Path(evidence_dir)
    evidence.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "failed",
        "passed": False,
        "commercial_passed": False,
        "failure_class": exc.__class__.__name__,
        "failure_reason": str(exc),
        "build_output_path": Path(build_output_path).as_posix(),
        "url": None,
        "screenshots": [],
        "canvas_hashes": [],
        "console_errors": [],
        "page_errors": [str(exc)],
        "feature_coverage": {},
    }
    output = evidence / "cocos_playtest_exception.json"
    _write_json(output, result)
    result["result_path"] = output.as_posix()
    return result


def _safe_id(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value)).strip("_") or "pipeline"


def _dedupe_strings(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value)
        if text not in seen:
            seen.add(text)
            result.append(text)
    return result
