from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from packages.contributions.games.cocos.commercial_assets import (
    generate_cocos_commercial_asset_manifest,
    generate_cocos_local_stable_asset_manifest,
)
from packages.contributions.games.cocos.ecosystem_bridge import collect_cocos_ecosystem_bridge_evidence
from packages.contributions.games.cocos.e2e import discover_cocos_creator_exe
from packages.contributions.pipelines.commercial_game_task_worker import (
    blocked_project_runtime_evidence_due_to_upstream,
    bootstrap_cocos_project_shell,
    collect_project_runtime_evidence,
    execute_same_project_task_cards,
    production_payload_from_worker,
    same_project_business_task_cards,
)
from packages.core_domain.task_card_store import TaskCardStore, task_card_quality_report


COMMERCIAL_GAME_PIPELINE_CONFIG_SCHEMA = "commercial_game_pipeline_config_v1"
COMMERCIAL_GAME_ASSET_SCHEMA = "commercial_game_asset_stage_v1"
COMMERCIAL_GAME_WORKER_SCHEMA = "commercial_game_task_card_worker_v1"
DEFAULT_CONFIG_PATH = Path("configs/commercial_game_pipeline.json")
EXTERNAL_INPUT_BLOCKERS = {
    "source_path_missing": {
        "failure_class": "input_precondition_missing",
        "owner_role": "operator_input",
        "affected_stage": "pipeline_invocation",
        "repair_mode": "supply_required_input",
        "suggestion": "Rerun the pipeline with --pdf-path pointing to an existing source brief or PDF.",
    },
    "cocos_creator_exe_missing": {
        "failure_class": "input_precondition_missing",
        "owner_role": "operator_input",
        "affected_stage": "pipeline_invocation",
        "repair_mode": "supply_required_input",
        "suggestion": "Rerun the pipeline with --creator-exe pointing to an installed Cocos Creator executable.",
    },
}
PROVIDER_RECOVERY_BLOCKERS = {
    "provider_usage_limit_exceeded": {
        "failure_class": "provider_usage_limit_exceeded",
        "owner_role": "asset_provider_operator",
        "affected_stage": "commercial_game_asset_generation",
        "repair_mode": "provider_quota_or_key_recovery",
        "max_attempts": 0,
        "suggestion": "Restore provider quota or switch to a verified asset provider, then rerun the asset stage.",
        "acceptance": ["provider_quota_available", "asset_stage_rechecked"],
    },
    "provider_quota_or_balance_exceeded": {
        "failure_class": "provider_quota_or_balance_exceeded",
        "owner_role": "asset_provider_operator",
        "affected_stage": "commercial_game_asset_generation",
        "repair_mode": "provider_quota_or_key_recovery",
        "max_attempts": 0,
        "suggestion": "Restore provider balance/quota or switch to a verified asset provider, then rerun the asset stage.",
        "acceptance": ["provider_quota_available", "asset_stage_rechecked"],
    },
    "provider_response_error": {
        "failure_class": "provider_response_error",
        "owner_role": "commercial_game_asset_generation",
        "affected_stage": "commercial_game_asset_generation",
        "repair_mode": "asset_provider_request_repair",
        "max_attempts": 1,
        "suggestion": "Repair the asset provider request payload or prompt budget, then rerun the asset stage.",
        "acceptance": ["provider_request_valid", "asset_stage_rechecked"],
    },
    "child_stdout_silent_recoverable": {
        "failure_class": "child_stdout_silent",
        "owner_role": "workflow_control_plane",
        "affected_stage": "same_project_task_card_worker",
        "repair_mode": "fresh_receipt_retry_until_three_attempts",
        "max_attempts": 3,
        "suggestion": "Resume the same task card with a fresh receipt and DB heartbeat-aware watchdog until the three-attempt runtime policy is exhausted.",
        "acceptance": ["fresh_receipt_created", "db_heartbeat_checked", "same_task_card_resumed", "attempt_recorded"],
    },
    "provider_output_idle_timeout_recoverable": {
        "failure_class": "provider_output_idle_timeout",
        "owner_role": "workflow_control_plane",
        "affected_stage": "same_project_task_card_worker",
        "repair_mode": "fresh_receipt_retry_after_provider_output_idle",
        "max_attempts": 3,
        "suggestion": "Restart the same task card with a fresh receipt after provider output has been idle; workflow_progress heartbeats alone do not satisfy provider progress.",
        "acceptance": ["fresh_receipt_created", "last_provider_output_at_recorded", "same_project_reused", "attempt_recorded"],
    },
    "provider_no_material_progress_timeout_recoverable": {
        "failure_class": "provider_no_material_progress_timeout",
        "owner_role": "workflow_control_plane",
        "affected_stage": "same_project_task_card_worker",
        "repair_mode": "fresh_receipt_retry_or_scope_split_after_no_material_progress",
        "max_attempts": 3,
        "suggestion": "Restart the same task card with a fresh receipt or split the card if provider output continues without changed files, tests, evidence, or artifact progress.",
        "acceptance": ["fresh_receipt_created", "last_material_progress_at_recorded", "same_project_reused", "attempt_recorded"],
    },
    "workflow_child_stalled": {
        "failure_class": "workflow_child_stalled",
        "owner_role": "workflow_control_plane",
        "affected_stage": "same_project_task_card_worker",
        "repair_mode": "close_child_run_then_fresh_receipt_retry_until_three_attempts",
        "max_attempts": 3,
        "suggestion": "Close the stalled child run, release its worker lease, then retry the same task card with a fresh receipt until the three-attempt policy is exhausted.",
        "acceptance": ["child_run_closed", "worker_lease_released", "fresh_receipt_created", "attempt_recorded"],
    },
    "provider_timeout_recoverable": {
        "failure_class": "provider_timeout",
        "owner_role": "provider_operator",
        "affected_stage": "same_project_task_card_worker",
        "repair_mode": "provider_live_proof_or_verified_fallback_then_three_attempt_retry",
        "max_attempts": 3,
        "suggestion": "Verify provider-specific live proof for the worker or a real fallback provider, then retry the same task card with a fresh receipt.",
        "acceptance": ["provider_live_proof_present", "fallback_not_shell_or_noop", "fresh_receipt_created", "attempt_recorded"],
    },
    "task_scope_too_large_after_adaptive_wall_timeout": {
        "failure_class": "task_scope_too_large_after_adaptive_wall_timeout",
        "owner_role": "operator_or_task_planner",
        "affected_stage": "same_project_task_card_worker",
        "repair_mode": "split_or_narrow_task_card_before_retry",
        "max_attempts": 0,
        "suggestion": "Do not keep extending the same task. Split or narrow the active task card, then resume only the next smaller same-project card with a fresh receipt.",
        "acceptance": ["task_card_split_or_scope_narrowed", "downstream_remains_short_circuited", "fresh_receipt_created_for_smaller_card"],
    },
    "provider_execution_failed": {
        "failure_class": "provider_execution_failed",
        "owner_role": "provider_operator",
        "affected_stage": "same_project_task_card_worker",
        "repair_mode": "provider_execution_repair_then_three_attempt_retry",
        "max_attempts": 3,
        "suggestion": "Repair the provider execution failure or switch to a verified real provider, then retry with a fresh receipt.",
        "acceptance": ["provider_execution_succeeds", "fallback_not_shell_or_noop", "fresh_receipt_created", "attempt_recorded"],
    },
    "blocked_after_three_attempts": {
        "failure_class": "blocked_after_three_attempts",
        "owner_role": "operator_or_workflow_repair",
        "affected_stage": "same_project_task_card_worker",
        "repair_mode": "manual_root_cause_repair_after_retry_exhaustion",
        "max_attempts": 0,
        "suggestion": "Do not continue downstream stages; inspect the recorded attempts, repair the root cause, then explicitly resume the task card.",
        "acceptance": ["attempts_reviewed", "root_cause_repaired", "downstream_remains_short_circuited_until_resume"],
    },
}


def load_commercial_game_pipeline_config(workspace_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(workspace_root or ".").resolve()
    path = root / DEFAULT_CONFIG_PATH
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "schema_version": COMMERCIAL_GAME_PIPELINE_CONFIG_SCHEMA,
        "pipeline_id": "commercial_game_production",
        "locale": "zh-CN",
        "target_engine": "cocos",
        "quality_mode": "commercial_playable",
        "live_agent_roles_default": False,
        "real_asset_provider_required_for_commercial_go": True,
        "persistent_project_per_run": True,
        "max_repair_attempts_per_finding": 3,
        "forbid_fixed_template_delivery": True,
    }


def execute_commercial_game_asset_generation(
    *,
    root: Path,
    target_dir: Path,
    shared_outputs: dict[str, Any],
    pipeline_id: str,
    require_real_assets: bool = False,
    source_path: str | Path | None = None,
    creator_exe: str | Path | None = None,
    require_build: bool = False,
) -> dict[str, Any]:
    resolved_creator_exe = discover_cocos_creator_exe(creator_exe) if require_build else creator_exe
    config = load_commercial_game_pipeline_config(root)
    run_root = _run_root(target_dir, pipeline_id)
    asset_root = run_root / "assets"
    precondition_blockers = _asset_generation_precondition_blockers(
        source_path=source_path,
        creator_exe=resolved_creator_exe,
        require_build=require_build,
        require_real_assets=require_real_assets,
    )
    if precondition_blockers:
        payload = {
            "schema_version": COMMERCIAL_GAME_ASSET_SCHEMA,
            "created_at": _utc_now(),
            "pipeline_id": pipeline_id,
            "locale": config.get("locale", "zh-CN"),
            "asset_manifest_path": None,
            "asset_manifest": {
                "schema_version": COMMERCIAL_GAME_ASSET_SCHEMA,
                "go_no_go": "NO-GO",
                "blockers": precondition_blockers,
                "results": [],
                "feature_coverage": {},
            },
            "provider_evidence": [],
            "placeholder_only": False,
            "require_real_assets": bool(require_real_assets),
            "commercial_assets_go": False,
            "commercial_asset_blockers": precondition_blockers,
            "recoverable_suggestions": _recoverable_suggestions(precondition_blockers),
            "asset_generation_skipped": True,
            "skip_reason": "input_precondition_missing",
            "forbids_fixed_template": True,
        }
        payload_path = asset_root / "commercial_game_asset_stage.json"
        _write_json(payload_path, payload)
        payload["evidence_path"] = payload_path.as_posix()
        return {
            "status": "completed",
            "failure_class": None,
            "execution_backend": "commercial_game_asset_generation_precondition_guard_v1",
            "output": payload,
            "shared_outputs": {
                "commercial_game_assets": payload,
                "commercial_assets": payload["asset_manifest"],
            },
        }
    style_prompt = _style_prompt(shared_outputs)
    should_attempt_real_provider = bool(
        require_real_assets
        or os.getenv("WORKFLOW_REQUIRE_REAL_ASSETS_FOR_COMMERCIAL_GO") == "1"
    )
    try:
        if should_attempt_real_provider:
            manifest = generate_cocos_commercial_asset_manifest(
                output_dir=asset_root,
                style_prompt=style_prompt,
                include_vertex_review=False,
            )
            placeholder_only = False
        else:
            manifest = generate_cocos_local_stable_asset_manifest(output_dir=asset_root)
            placeholder_only = True
    except Exception as exc:
        manifest = {
            "schema_version": COMMERCIAL_GAME_ASSET_SCHEMA,
            "created_at": _utc_now(),
            "go_no_go": "NO-GO",
            "blockers": [exc.__class__.__name__],
            "results": [],
            "feature_coverage": {},
            "failure": str(exc),
        }
        placeholder_only = False

    blockers = list(manifest.get("blockers") or [])
    if placeholder_only:
        blockers.append("placeholder_assets_only")
    provider_evidence = _provider_evidence(manifest)
    commercial_assets_go = manifest.get("go_no_go") == "GO" and not placeholder_only
    payload = {
        "schema_version": COMMERCIAL_GAME_ASSET_SCHEMA,
        "created_at": _utc_now(),
        "pipeline_id": pipeline_id,
        "locale": config.get("locale", "zh-CN"),
        "asset_manifest_path": manifest.get("manifest_path"),
        "asset_manifest": manifest,
        "provider_evidence": provider_evidence,
        "placeholder_only": placeholder_only,
        "require_real_assets": bool(require_real_assets),
        "commercial_assets_go": commercial_assets_go,
        "commercial_asset_blockers": blockers,
        "forbids_fixed_template": True,
    }
    payload_path = asset_root / "commercial_game_asset_stage.json"
    _write_json(payload_path, payload)
    payload["evidence_path"] = payload_path.as_posix()
    return {
        "status": "completed",
        "failure_class": None,
        "execution_backend": "commercial_game_asset_generation_v1",
        "output": payload,
        "shared_outputs": {
            "commercial_game_assets": payload,
            "commercial_assets": manifest,
        },
    }


def execute_commercial_game_task_card_worker(
    *,
    root: Path,
    target_dir: Path,
    shared_outputs: dict[str, Any],
    pipeline_id: str,
    db_path: str | Path | None,
    source_path: str | Path | None,
    creator_exe: str | Path | None,
    output_dir: str | Path | None,
    require_build: bool,
    require_playtest: bool,
    require_commercial: bool,
    require_cocos_ecosystem: bool = False,
    cocos_bridge_mode: str = "auto",
    cocos_bridge_timeout_seconds: int = 180,
    cocos_bridge_report_path: str | Path | None = None,
    allow_existing_cocos_process: bool = False,
    max_repair_attempts: int = 3,
    task_card_runner: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    resolved_creator_exe = discover_cocos_creator_exe(creator_exe) if require_build else creator_exe
    run_root = _run_root(target_dir, pipeline_id)
    project_dir = Path(output_dir).resolve() if output_dir is not None else run_root / "cocos_project"
    project_dir.parent.mkdir(parents=True, exist_ok=True)
    task_cards = TaskCardStore(db_path).list_for_run(pipeline_id) if db_path is not None else []
    quality = task_card_quality_report(task_cards)
    if quality["go_no_go"] != "GO":
        payload = _worker_payload(
            pipeline_id=pipeline_id,
            project_dir=project_dir,
            task_card_quality=quality,
            commercial_playable_go=False,
            blockers=["task_card_quality_no_go"],
            max_repair_attempts=max_repair_attempts,
        )
        return {
            "status": "blocked",
            "failure_class": "task_card_quality_no_go",
            "execution_backend": "commercial_game_task_card_worker_v1",
            "output": payload,
            "shared_outputs": {"commercial_game_production": payload},
        }

    if source_path is None or not Path(source_path).exists():
        blockers = ["source_path_missing", *_asset_blockers_from_shared_outputs(shared_outputs)]
        payload = _worker_payload(
            pipeline_id=pipeline_id,
            project_dir=project_dir,
            task_card_quality=quality,
            commercial_playable_go=False,
            blockers=blockers,
            max_repair_attempts=max_repair_attempts,
        )
        _write_worker_manifest(project_dir, payload)
        return _worker_completed(payload)

    if resolved_creator_exe is None or not Path(resolved_creator_exe).exists():
        blockers = ["cocos_creator_exe_missing", *_asset_blockers_from_shared_outputs(shared_outputs)]
        payload = _worker_payload(
            pipeline_id=pipeline_id,
            project_dir=project_dir,
            task_card_quality=quality,
            commercial_playable_go=False,
            blockers=blockers,
            max_repair_attempts=max_repair_attempts,
        )
        _write_worker_manifest(project_dir, payload)
        return _worker_completed(payload)

    assets_stage = shared_outputs.get("commercial_game_assets")
    asset_manifest = None
    if isinstance(assets_stage, dict):
        asset_manifest = assets_stage.get("asset_manifest")
    if not isinstance(asset_manifest, dict):
        asset_manifest = shared_outputs.get("commercial_assets") if isinstance(shared_outputs.get("commercial_assets"), dict) else None

    bootstrap_cocos_project_shell(
        project_dir=project_dir,
        source_path=Path(source_path),
        creator_exe=Path(resolved_creator_exe),
        asset_manifest=asset_manifest if isinstance(asset_manifest, dict) else None,
    )
    business_cards = same_project_business_task_cards(task_cards)
    patch_ledger = execute_same_project_task_cards(
        root=root,
        run_root=run_root,
        project_dir=project_dir,
        pipeline_id=pipeline_id,
        db_path=Path(db_path) if db_path is not None else None,
        task_cards=business_cards,
        max_repair_attempts=max_repair_attempts,
        task_card_runner=task_card_runner,
    )
    prebuild_ecosystem_evidence = collect_cocos_ecosystem_bridge_evidence(
        project_path=project_dir,
        creator_exe=resolved_creator_exe,
        evidence_dir=run_root / "cocos_ecosystem",
        require_bridge=require_cocos_ecosystem,
        bridge_mode=cocos_bridge_mode,
        bridge_timeout_seconds=cocos_bridge_timeout_seconds,
        bridge_report_path=cocos_bridge_report_path,
        allow_existing_cocos_process=allow_existing_cocos_process,
    )
    if patch_ledger.get("same_project_worker_patch_go"):
        runtime_evidence = collect_project_runtime_evidence(
            project_dir=project_dir,
            creator_exe=Path(resolved_creator_exe),
            require_build=require_build,
            require_playtest=require_playtest,
        )
    else:
        runtime_evidence = blocked_project_runtime_evidence_due_to_upstream(
            project_dir=project_dir,
            patch_ledger=patch_ledger,
            require_build=require_build,
            require_playtest=require_playtest,
        )
    ecosystem_evidence = collect_cocos_ecosystem_bridge_evidence(
        project_path=project_dir,
        creator_exe=resolved_creator_exe,
        evidence_dir=run_root / "cocos_ecosystem",
        require_bridge=require_cocos_ecosystem,
        bridge_mode="report_only",
        bridge_timeout_seconds=cocos_bridge_timeout_seconds,
        bridge_report_path=cocos_bridge_report_path,
        allow_existing_cocos_process=allow_existing_cocos_process,
    )
    if prebuild_ecosystem_evidence.get("bridge_runner_evidence") and not ecosystem_evidence.get("bridge_runner_evidence"):
        ecosystem_evidence["bridge_runner_evidence"] = prebuild_ecosystem_evidence["bridge_runner_evidence"]
    if prebuild_ecosystem_evidence.get("failure_class"):
        ecosystem_evidence["ecosystem_integration_go"] = False
        ecosystem_evidence["failure_class"] = prebuild_ecosystem_evidence.get("failure_class")
        ecosystem_evidence["blockers"] = _dedupe_strings(
            [*(ecosystem_evidence.get("blockers") or []), *(prebuild_ecosystem_evidence.get("blockers") or [])]
        )
        ecosystem_evidence["recoverable_suggestion"] = prebuild_ecosystem_evidence.get("recoverable_suggestion")
    if prebuild_ecosystem_evidence.get("operator_action_required"):
        ecosystem_evidence["operator_action_required"] = True
        ecosystem_evidence["operator_actions"] = prebuild_ecosystem_evidence.get("operator_actions") or []
    payload = production_payload_from_worker(
        schema_version=COMMERCIAL_GAME_WORKER_SCHEMA,
        created_at=_utc_now(),
        pipeline_id=pipeline_id,
        project_dir=project_dir,
        task_card_quality=quality,
        runtime_evidence=runtime_evidence,
        assets_stage=assets_stage if isinstance(assets_stage, dict) else {},
        ecosystem_evidence=ecosystem_evidence,
        patch_ledger=patch_ledger,
        skipped_task_cards=[card.task_card_id for card in task_cards if card not in business_cards],
        max_repair_attempts=max_repair_attempts,
        dedupe_strings=_dedupe_strings,
        blocker_details=_blocker_details,
        recoverable_suggestions=_recoverable_suggestions,
    )
    _write_worker_manifest(project_dir, payload)
    completed = _worker_completed(payload)
    completed["shared_outputs"]["cocos_e2e"] = runtime_evidence
    completed["shared_outputs"]["cocos_ecosystem_evidence"] = ecosystem_evidence
    return completed


def build_supervisor_repair_packets(
    *,
    structured_output: dict[str, Any],
    shared_outputs: dict[str, Any],
    max_repair_attempts: int = 3,
) -> list[dict[str, Any]]:
    findings: list[Any] = []
    qa = shared_outputs.get("role_output:qa_player_perspective_agent")
    if isinstance(qa, dict):
        qa_structured = qa.get("structured_output")
        if isinstance(qa_structured, dict):
            findings.extend(qa_structured.get("repair_findings") or [])
    production = shared_outputs.get("commercial_game_production")
    if isinstance(production, dict):
        findings.extend(production.get("commercial_playable_blockers") or [])
    assets_stage = shared_outputs.get("commercial_game_assets")
    if isinstance(assets_stage, dict):
        findings.extend(assets_stage.get("commercial_asset_blockers") or [])
        if assets_stage.get("placeholder_only"):
            findings.append("placeholder_assets_only")
    findings.extend(structured_output.get("repair_findings") or [])

    packets: list[dict[str, Any]] = []
    unique_findings = []
    seen_findings: set[str] = set()
    for finding in findings:
        finding_text = _finding_text(finding)
        if not finding_text or finding_text in seen_findings:
            continue
        seen_findings.add(finding_text)
        unique_findings.append(finding_text)

    for index, finding_text in enumerate(unique_findings, start=1):
        external_input = _external_input_blocker(finding_text)
        if external_input is not None:
            packets.append(
                {
                    "repair_packet_id": f"repair_{index:03d}_{_safe_id(external_input['owner_role'])}",
                    "finding": finding_text,
                    "severity": "high",
                    "owner_role": external_input["owner_role"],
                    "affected_stage": external_input["affected_stage"],
                    "repair_mode": external_input["repair_mode"],
                    "max_attempts": 0,
                    "rerun_policy": "rerun_full_pipeline_after_operator_input",
                    "forbidden_changes": ["do_not_patch_business_code_for_missing_operator_input"],
                    "acceptance": ["required_input_present", "pipeline_rechecked"],
                    "recoverable_suggestion": external_input["suggestion"],
                    "failure_class": external_input["failure_class"],
                }
            )
            continue
        provider_recovery = _provider_recovery_blocker(finding_text)
        if provider_recovery is not None:
            packets.append(
                {
                    "repair_packet_id": f"repair_{index:03d}_{_safe_id(provider_recovery['owner_role'])}",
                    "finding": finding_text,
                    "severity": "high",
                    "owner_role": provider_recovery["owner_role"],
                    "affected_stage": provider_recovery["affected_stage"],
                    "repair_mode": provider_recovery["repair_mode"],
                    "max_attempts": int(provider_recovery["max_attempts"]),
                    "rerun_policy": "failed_asset_stage_plus_downstream_final_gate",
                    "forbidden_changes": ["do_not_create_new_project_for_repair", "do_not_replace_real_assets_with_placeholders"],
                    "acceptance": list(provider_recovery["acceptance"]),
                    "recoverable_suggestion": provider_recovery["suggestion"],
                    "failure_class": provider_recovery["failure_class"],
                }
            )
            continue
        owner = _repair_owner_for(finding_text)
        packets.append(
            {
                "repair_packet_id": f"repair_{index:03d}_{_safe_id(owner)}",
                "finding": finding_text,
                "severity": "high" if "missing" in finding_text or "blocked" in finding_text else "medium",
                "owner_role": owner,
                "affected_stage": _repair_stage_for(owner),
                "repair_mode": "same_project_incremental_patch",
                "max_attempts": max_repair_attempts,
                "rerun_policy": "failed_stage_plus_downstream_final_gate",
                "forbidden_changes": ["do_not_create_new_project_for_repair", "do_not_replace_real_assets_with_placeholders"],
                "acceptance": ["finding_resolved", "targeted_test_passed", "final_gate_rechecked"],
            }
        )
    return packets


def _worker_completed(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "completed",
        "failure_class": None,
        "execution_backend": "commercial_game_task_card_worker_v1",
        "output": payload,
        "shared_outputs": {"commercial_game_production": payload},
    }


def _worker_payload(
    *,
    pipeline_id: str,
    project_dir: Path,
    task_card_quality: dict[str, Any],
    commercial_playable_go: bool,
    blockers: list[str],
    max_repair_attempts: int,
) -> dict[str, Any]:
    return {
        "schema_version": COMMERCIAL_GAME_WORKER_SCHEMA,
        "created_at": _utc_now(),
        "pipeline_id": pipeline_id,
        "project_dir": project_dir.as_posix(),
        "persistent_project_per_run": True,
        "task_card_quality": task_card_quality,
        "task_card_count": int(task_card_quality.get("task_card_count") or 0),
        "technical_smoke_go": False,
        "production_scaffold_go": False,
        "commercial_playable_go": commercial_playable_go,
        "ecosystem_integration_go": False,
        "live_role_provider_proof_go": False,
        "same_project_worker_patch_go": False,
        "human_player_review_go": False,
        "degradation_findings": [],
        "commercial_playable_blockers": _dedupe_strings(blockers),
        "commercial_playable_blocker_details": _blocker_details(_dedupe_strings(blockers)),
        "recoverable_suggestions": _recoverable_suggestions(_dedupe_strings(blockers)),
        "commercial_feature_coverage": {},
        "player_visible_checks": {},
        "max_repair_attempts": max_repair_attempts,
        "repair_policy": "same_project_incremental_repair",
        "forbids_fixed_template": True,
    }


def _write_worker_manifest(project_dir: Path, payload: dict[str, Any]) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    _write_json(project_dir / "workflow_project_manifest.json", payload)


def _style_prompt(shared_outputs: dict[str, Any]) -> str:
    ui = shared_outputs.get("role_output:ui_experience_agent")
    product = shared_outputs.get("role_output:product_gameplay_agent")
    signals = []
    for item in (product, ui):
        if isinstance(item, dict):
            structured = item.get("structured_output")
            if isinstance(structured, dict):
                signals.append(json.dumps(structured, ensure_ascii=False)[:1000])
    if signals:
        return "premium polished Chinese mobile Cocos mini game; " + " ".join(signals)[:1800]
    return "premium polished Chinese Cocos mobile mini game, clear UI, commercial casual game art"


def _asset_blockers_from_shared_outputs(shared_outputs: dict[str, Any]) -> list[str]:
    assets_stage = shared_outputs.get("commercial_game_assets")
    if not isinstance(assets_stage, dict):
        return []
    blockers = [str(item) for item in assets_stage.get("commercial_asset_blockers") or []]
    if assets_stage.get("placeholder_only"):
        blockers.append("placeholder_assets_only")
    return _dedupe_strings(blockers)


def _asset_generation_precondition_blockers(
    *,
    source_path: str | Path | None,
    creator_exe: str | Path | None,
    require_build: bool,
    require_real_assets: bool,
) -> list[str]:
    blockers: list[str] = []
    if require_real_assets and (source_path is None or not Path(source_path).exists()):
        blockers.append("source_path_missing")
    if require_build and (creator_exe is None or not Path(creator_exe).exists()):
        blockers.append("cocos_creator_exe_missing")
    return blockers


def _provider_evidence(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = []
    for item in manifest.get("results") or []:
        if not isinstance(item, dict):
            continue
        evidence.append(
            {
                "asset_name": item.get("asset_name"),
                "provider": item.get("provider"),
                "model": item.get("model"),
                "status": item.get("status"),
                "artifact_paths": item.get("artifact_paths") or [],
                "failure_class": item.get("failure_class"),
            }
        )
    return evidence


def _finding_text(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("finding") or value.get("blocker") or value.get("check") or value)
    return str(value)


def _external_input_blocker(finding: str) -> dict[str, str] | None:
    return EXTERNAL_INPUT_BLOCKERS.get(finding.strip())


def _provider_recovery_blocker(finding: str) -> dict[str, Any] | None:
    normalized = finding.strip().lower()
    for marker, payload in PROVIDER_RECOVERY_BLOCKERS.items():
        if marker in normalized:
            return payload
    return None


def _dedupe_strings(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value)
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _blocker_details(blockers: list[str]) -> list[dict[str, str]]:
    details: list[dict[str, str]] = []
    for blocker in blockers:
        external_input = _external_input_blocker(str(blocker))
        if external_input is not None:
            details.append(
                {
                    "blocker": str(blocker),
                    "failure_class": external_input["failure_class"],
                    "owner_role": external_input["owner_role"],
                    "repair_mode": external_input["repair_mode"],
                    "recoverable_suggestion": external_input["suggestion"],
                }
            )
        else:
            provider_recovery = _provider_recovery_blocker(str(blocker))
            if provider_recovery is not None:
                details.append(
                    {
                        "blocker": str(blocker),
                        "failure_class": provider_recovery["failure_class"],
                        "owner_role": provider_recovery["owner_role"],
                        "repair_mode": provider_recovery["repair_mode"],
                        "recoverable_suggestion": provider_recovery["suggestion"],
                    }
                )
                continue
            details.append(
                {
                    "blocker": str(blocker),
                    "failure_class": "commercial_readiness_blocker",
                    "owner_role": _repair_owner_for(str(blocker)),
                    "repair_mode": "same_project_incremental_patch",
                }
            )
    return details


def _recoverable_suggestions(blockers: list[str]) -> list[str]:
    suggestions: list[str] = []
    for blocker in blockers:
        external_input = _external_input_blocker(str(blocker))
        if external_input is not None and external_input["suggestion"] not in suggestions:
            suggestions.append(external_input["suggestion"])
            continue
        provider_recovery = _provider_recovery_blocker(str(blocker))
        if provider_recovery is not None and provider_recovery["suggestion"] not in suggestions:
            suggestions.append(provider_recovery["suggestion"])
    return suggestions


def _repair_owner_for(finding: str) -> str:
    normalized = finding.lower()
    if any(marker in normalized for marker in ("asset", "audio", "music", "sfx", "placeholder")):
        return "commercial_game_asset_generation"
    if any(marker in normalized for marker in ("ui", "panel", "button", "text", "overlap")):
        return "ui_experience_agent"
    if any(marker in normalized for marker in ("level", "goal", "progress", "gameplay")):
        return "product_gameplay_agent"
    if any(marker in normalized for marker in ("test", "playtest", "browser", "screenshot")):
        return "qa_player_perspective_agent"
    if any(marker in normalized for marker in ("workflow", "task_card", "sqlite")):
        return "workflow_runtime"
    return "commercial_game_task_card_worker"


def _repair_stage_for(owner: str) -> str:
    if owner in {"commercial_game_asset_generation", "commercial_game_task_card_worker"}:
        return owner
    if owner == "workflow_runtime":
        return "bug_first_workflow_repair"
    return f"role:{owner}"


def _run_root(target_dir: Path, pipeline_id: str) -> Path:
    root = target_dir / _safe_id(pipeline_id)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_id(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value)).strip("_") or "pipeline"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
