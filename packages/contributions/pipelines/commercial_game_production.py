from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from packages.contracts import TaskCard
from packages.contributions.games.cocos.commercial_assets import (
    generate_cocos_commercial_asset_manifest,
    generate_cocos_local_stable_asset_manifest,
)
from packages.contributions.games.cocos.ecosystem_bridge import collect_cocos_ecosystem_bridge_evidence
from packages.contributions.games.cocos.e2e import discover_cocos_creator_exe
from packages.contributions.games.cocos.no_degradation import evaluate_no_degradation_contract
from packages.contributions.games.game_design_ir import (
    build_game_design_spec_from_requirement_matrix,
    validate_game_design_spec,
)
from packages.contributions.games.game_task_card_generation import (
    PHASE_EXECUTION_BLUEPRINT_SCHEMA,
    TASK_CARD_COMPILE_REPORT_SCHEMA,
)
from packages.contributions.pipelines.commercial_game_development_readiness import (
    build_commercial_game_development_readiness_evidence,
)
from packages.contributions.pipelines.commercial_game_task_worker import (
    blocked_project_runtime_evidence_due_to_upstream,
    bootstrap_cocos_project_shell,
    collect_project_runtime_evidence,
    execute_same_project_task_cards,
    production_payload_from_worker,
    same_project_business_task_cards,
    validate_same_project_reuse,
)
from packages.core_domain.repositories import TaskRepository
from packages.core_domain.task_card_store import TaskCardStore, task_card_quality_report
from packages.core_domain.unified_project_brief import build_unified_project_brief


COMMERCIAL_GAME_PIPELINE_CONFIG_SCHEMA = "commercial_game_pipeline_config_v1"
COMMERCIAL_GAME_ASSET_SCHEMA = "commercial_game_asset_stage_v1"
COMMERCIAL_GAME_WORKER_SCHEMA = "commercial_game_task_card_worker_v1"
DEFAULT_CONFIG_PATH = Path("configs/commercial_game_pipeline.json")
MACHINE_GATE_REPAIR_CARD_SOURCE = "active_phase_machine_gate_repair"
COCOS_PRODUCT_BODY_COMPONENT_ARTIFACTS = [
    "assets/scripts/runtime/workflow/WorkflowBlockPuzzleBoardBinding.ts",
    "assets/scripts/runtime/workflow/WorkflowBlockPuzzleSceneRuntime.ts",
    "assets/scripts/runtime/workflow/WorkflowCandidateTrayBinding.ts",
    "assets/scripts/runtime/workflow/WorkflowCandidatePrefabBinding.ts",
    "assets/scripts/runtime/workflow/WorkflowBuildProductBodyWitness.ts",
    "assets/prefabs/workflow_block_puzzle_board_binding.prefab",
]
MACHINE_GATE_REPAIR_HUMAN_ONLY_BLOCKERS = {"awaiting_human_player_review"}
MACHINE_GATE_REPAIR_EXTERNAL_INPUT_BLOCKERS = {
    "source_path_missing",
    "cocos_creator_exe_missing",
    "fallback_provider_unavailable",
    "provider_quota_or_balance_exceeded",
    "provider_usage_limit_exceeded",
    "provider_usage_limit_reached",
    "task_card_quality_no_go",
    "task_card_lifecycle_no_go",
    "game_design_spec_no_go",
    "same_project_source_mismatch",
    "same_project_unmanaged_project_dir",
}
MACHINE_GATE_REPAIR_BUILD_BLOCKERS = {
    "baseline_only_cannot_pass_commercial_final_gate",
    "cocos_build_fatal_marker_detected",
    "cocos_build_missing",
    "cocos_build_no_artifact_success",
    "cocos_build_nonzero_exit",
    "cocos_build_not_real_execution",
    "cocos_build_output_path_missing",
    "build_ledger_missing",
    "cocos_component_binding_missing",
    "canvas_only_product_body",
    "empty_component_shell_not_runtime_product_body",
    "event_only_gameplay_evidence",
    "feature_flag_only_evidence",
    "gameplay_semantic_evidence_missing",
    "gameplay_semantic_not_real_execution",
    "model_transition_trace_missing",
    "product_body_not_real_execution",
    "runtime_hook_not_product_body",
    "runtime_hook_not_semantic_model",
    "semantic_model_transition_trace_missing",
    "scene_product_body_missing",
    "template_leak_detected",
    "assetdb_import_query_evidence",
    "scene_create_save_evidence",
    "node_component_binding_evidence",
    "prefab_create_instantiate_evidence",
    "cocos_ecosystem_bridge_missing",
}
MACHINE_GATE_REPAIR_BROWSER_BLOCKERS = {
    "browser_playtest_missing_build_output",
    "browser_playtest_missing",
    "browser_playtest_no_go",
    "browser_playtest_not_real_execution",
    "browser_playtest_execution_failed",
    "browser_playtest_screenshots_missing",
    "browser_http_launch_missing",
    "browser_canvas_hash_static_after_actions",
    "browser_commercial_playtest_features_missing",
    "browser_console_or_page_errors",
    "browser_or_audio_runtime_error",
    "browser_required_playtest_features_missing",
    "desktop_cocos_splash_only",
    "desktop_runtime_not_started",
    "mobile_viewport_evidence_missing",
    "reference_quality_candidate_playtest_missing",
    "reference_quality_event_count_below_reference",
    "reference_quality_missing_features",
    "reference_quality_open_panel_count_below_reference",
    "reference_quality_reference_playtest_missing",
    "reference_quality_score_below_reference",
    "reference_quality_screenshot_count_below_reference",
    "reference_quality_visual_density_below_reference",
    "audio_runtime_not_verified",
    "bgm_runtime_not_verified",
    "sfx_runtime_not_verified",
    "volume_toggle_missing",
}
MACHINE_GATE_REPAIR_DEPTH_BLOCKERS = {
    "product_feature_depth_missing",
    "product_depth_not_real_execution",
    "event_only_player_visible_evidence",
    "levels_not_distinct_or_less_than_eight",
    "level_goal_labels_mojibake",
    "shop_ownership_states_missing",
    "skin_system_not_player_visible",
    "chinese_ui_panels_missing",
    "failure_revive_feedback_missing",
    "level_flow_not_verified",
    "animation_feedback_missing",
}
MACHINE_GATE_REPAIR_AI_BLOCKERS = {
    "ai_surrogate_playtest_missing",
    "ai_playtest_modes_incomplete",
    "ai_playtest_replay_artifacts_missing",
    "ai_playtest_screenshots_missing",
    "ai_visual_review_missing",
    "ai_audio_review_missing",
    "ai_quality_score_below_85",
    "core_loop_not_playable",
    "first_session_flow_not_proven",
    "requirement_fidelity_not_proven",
}
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
        "live_agent_roles_default": True,
        "commercial_high_risk_requires_live_design": True,
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
    require_commercial: bool = False,
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
    game_design_contract: dict[str, Any] = {}
    if require_commercial and source_path is not None and Path(source_path).exists():
        game_design_contract = _build_game_design_spec_contract(
            run_root=run_root,
            pipeline_id=pipeline_id,
            source_path=Path(source_path),
        )
        if not game_design_contract.get("go"):
            blockers = ["game_design_spec_no_go", *list(game_design_contract.get("blockers") or [])]
            payload = {
                "schema_version": COMMERCIAL_GAME_ASSET_SCHEMA,
                "created_at": _utc_now(),
                "pipeline_id": pipeline_id,
                "locale": config.get("locale", "zh-CN"),
                "asset_manifest_path": None,
                "asset_manifest": {
                    "schema_version": COMMERCIAL_GAME_ASSET_SCHEMA,
                    "go_no_go": "NO-GO",
                    "blockers": blockers,
                    "results": [],
                    "feature_coverage": {},
                },
                "provider_evidence": [],
                "placeholder_only": False,
                "require_real_assets": bool(require_real_assets),
                "commercial_assets_go": False,
                "commercial_asset_blockers": blockers,
                "game_design_spec_contract": game_design_contract,
                "asset_generation_skipped": True,
                "skip_reason": "game_design_spec_no_go",
                "forbids_fixed_template": True,
            }
            payload_path = asset_root / "commercial_game_asset_stage.json"
            _write_json(payload_path, payload)
            payload["evidence_path"] = payload_path.as_posix()
            return {
                "status": "blocked",
                "failure_class": "game_design_spec_no_go",
                "execution_backend": "commercial_game_asset_generation_precondition_guard_v1",
                "output": payload,
                "shared_outputs": {
                    "commercial_game_assets": payload,
                    "commercial_assets": payload["asset_manifest"],
                    "game_design_spec_contract": game_design_contract,
                },
            }
    style_prompt = _style_prompt(shared_outputs)
    reusable_asset_stage = _reusable_commercial_asset_stage(
        asset_root=asset_root,
        source_path=Path(source_path) if source_path is not None else None,
        game_design_contract=game_design_contract,
    )
    if reusable_asset_stage is not None:
        return {
            "status": "completed",
            "failure_class": None,
            "execution_backend": "commercial_game_asset_generation_reuse_v1",
            "output": reusable_asset_stage,
            "shared_outputs": {
                "commercial_game_assets": reusable_asset_stage,
                "commercial_assets": reusable_asset_stage["asset_manifest"],
                **({"game_design_spec_contract": game_design_contract} if game_design_contract else {}),
            },
        }
    should_attempt_real_provider = bool(
        require_real_assets
        or os.getenv("WORKFLOW_REQUIRE_REAL_ASSETS_FOR_COMMERCIAL_GO") == "1"
    )
    try:
        if should_attempt_real_provider:
            manifest = generate_cocos_commercial_asset_manifest(
                output_dir=asset_root,
                style_prompt=style_prompt,
                include_vertex_review=True,
                enable_provider_fallbacks=True,
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
        "game_design_spec_contract": game_design_contract,
        "source_identity": _source_identity_for_stage(Path(source_path) if source_path is not None else None),
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
            **({"game_design_spec_contract": game_design_contract} if game_design_contract else {}),
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
        lifecycle_no_go = int(quality.get("lifecycle_blocked_count") or 0) > 0
        failure_class = "task_card_lifecycle_no_go" if lifecycle_no_go else "task_card_quality_no_go"
        payload = _worker_payload(
            pipeline_id=pipeline_id,
            project_dir=project_dir,
            task_card_quality=quality,
            commercial_playable_go=False,
            blockers=[failure_class],
            max_repair_attempts=max_repair_attempts,
        )
        return {
            "status": "blocked",
            "failure_class": failure_class,
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

    game_design_contract: dict[str, Any] = {}
    if require_commercial:
        game_design_contract = _build_game_design_spec_contract(
            run_root=run_root,
            pipeline_id=pipeline_id,
            source_path=Path(source_path),
        )
        if not game_design_contract.get("go"):
            blockers = ["game_design_spec_no_go", *list(game_design_contract.get("blockers") or [])]
            payload = _worker_payload(
                pipeline_id=pipeline_id,
                project_dir=project_dir,
                task_card_quality=quality,
                commercial_playable_go=False,
                blockers=_dedupe_strings(blockers),
                max_repair_attempts=max_repair_attempts,
            )
            payload["game_design_spec_contract"] = game_design_contract
            _write_worker_manifest(project_dir, payload)
            return _worker_completed(payload)

    business_cards = same_project_business_task_cards(task_cards)
    compile_blockers = _commercial_task_card_compile_blockers(business_cards) if require_commercial else []
    if compile_blockers:
        payload = _worker_payload(
            pipeline_id=pipeline_id,
            project_dir=project_dir,
            task_card_quality=quality,
            commercial_playable_go=False,
            blockers=compile_blockers,
            max_repair_attempts=max_repair_attempts,
        )
        payload["game_design_spec_contract"] = game_design_contract
        payload["task_card_compile_contract"] = {
            "schema_version": "commercial_game_task_card_compile_contract_v1",
            "go": False,
            "blockers": compile_blockers,
            "business_task_card_ids": [card.task_card_id for card in business_cards],
        }
        payload["same_project_patch_ledger"] = {
            "same_project_worker_patch_go": False,
            "entries": [],
            "blockers": compile_blockers,
        }
        _write_worker_manifest(project_dir, payload)
        return _worker_completed(payload)

    assets_stage = shared_outputs.get("commercial_game_assets")
    asset_manifest = None
    if isinstance(assets_stage, dict):
        asset_manifest = assets_stage.get("asset_manifest")
    if not isinstance(asset_manifest, dict):
        asset_manifest = shared_outputs.get("commercial_assets") if isinstance(shared_outputs.get("commercial_assets"), dict) else None

    reuse_guard = validate_same_project_reuse(project_dir=project_dir, source_path=Path(source_path))
    if not reuse_guard.get("go"):
        blockers = [*list(reuse_guard.get("blockers") or []), *_asset_blockers_from_shared_outputs(shared_outputs)]
        payload = _worker_payload(
            pipeline_id=pipeline_id,
            project_dir=project_dir,
            task_card_quality=quality,
            commercial_playable_go=False,
            blockers=_dedupe_strings(blockers),
            max_repair_attempts=max_repair_attempts,
        )
        payload["game_design_spec_contract"] = game_design_contract
        payload["same_project_reuse_guard"] = reuse_guard
        payload["same_project_patch_ledger"] = {
            "same_project_worker_patch_go": False,
            "entries": [],
            "blockers": _dedupe_strings(blockers),
        }
        return _worker_completed(payload)

    bootstrap_cocos_project_shell(
        project_dir=project_dir,
        source_path=Path(source_path),
        creator_exe=Path(resolved_creator_exe),
        asset_manifest=asset_manifest if isinstance(asset_manifest, dict) else None,
    )
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
    _merge_prebuild_ecosystem_evidence(ecosystem_evidence, prebuild_ecosystem_evidence)
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
    repaired = _run_post_worker_machine_gate_repair_loop(
        root=root,
        run_root=run_root,
        project_dir=project_dir,
        pipeline_id=pipeline_id,
        db_path=Path(db_path) if db_path is not None else None,
        shared_outputs=shared_outputs,
        payload=payload,
        patch_ledger=patch_ledger,
        runtime_evidence=runtime_evidence,
        ecosystem_evidence=ecosystem_evidence,
        business_cards=business_cards,
        task_cards=task_cards,
        quality=quality,
        assets_stage=assets_stage if isinstance(assets_stage, dict) else {},
        require_build=require_build,
        require_playtest=require_playtest,
        require_commercial=require_commercial,
        require_cocos_ecosystem=require_cocos_ecosystem,
        creator_exe=Path(resolved_creator_exe),
        cocos_bridge_mode=cocos_bridge_mode,
        cocos_bridge_timeout_seconds=cocos_bridge_timeout_seconds,
        cocos_bridge_report_path=cocos_bridge_report_path,
        allow_existing_cocos_process=allow_existing_cocos_process,
        max_repair_attempts=max_repair_attempts,
        task_card_runner=task_card_runner,
        game_design_contract=game_design_contract,
    )
    payload = repaired["payload"]
    patch_ledger = repaired["patch_ledger"]
    runtime_evidence = repaired["runtime_evidence"]
    ecosystem_evidence = repaired["ecosystem_evidence"]
    if game_design_contract:
        payload["game_design_spec_contract"] = game_design_contract
    payload["same_project_reuse_guard"] = reuse_guard
    payload["task_card_compile_contract"] = {
        "schema_version": "commercial_game_task_card_compile_contract_v1",
        "go": True,
        "blockers": [],
        "business_task_card_ids": [card.task_card_id for card in business_cards],
    }
    _write_worker_manifest(project_dir, payload)
    completed = _worker_completed(payload)
    completed["shared_outputs"]["cocos_e2e"] = runtime_evidence
    completed["shared_outputs"]["cocos_ecosystem_evidence"] = ecosystem_evidence
    return completed


def _run_post_worker_machine_gate_repair_loop(
    *,
    root: Path,
    run_root: Path,
    project_dir: Path,
    pipeline_id: str,
    db_path: Path | None,
    shared_outputs: dict[str, Any],
    payload: dict[str, Any],
    patch_ledger: dict[str, Any],
    runtime_evidence: dict[str, Any],
    ecosystem_evidence: dict[str, Any],
    business_cards: list[TaskCard],
    task_cards: list[TaskCard],
    quality: dict[str, Any],
    assets_stage: dict[str, Any],
    require_build: bool,
    require_playtest: bool,
    require_commercial: bool,
    require_cocos_ecosystem: bool,
    creator_exe: Path,
    cocos_bridge_mode: str,
    cocos_bridge_timeout_seconds: int,
    cocos_bridge_report_path: str | Path | None,
    allow_existing_cocos_process: bool,
    max_repair_attempts: int,
    task_card_runner: Callable[..., dict[str, Any]] | None,
    game_design_contract: dict[str, Any],
) -> dict[str, Any]:
    executable_cards = list(business_cards)
    repair_history: list[dict[str, Any]] = []
    generated_repair_cards: list[TaskCard] = []
    generated_repair_card_ids: set[str] = set()
    post_worker_gate = _post_worker_machine_gate_report(
        shared_outputs=shared_outputs,
        production_payload=payload,
        ecosystem_evidence=ecosystem_evidence,
        require_commercial=require_commercial,
        require_cocos_ecosystem=require_cocos_ecosystem,
    )
    if not business_cards or not patch_ledger.get("same_project_worker_patch_go"):
        suppressed_reason = (
            "same_project_worker_business_cards_missing"
            if not business_cards
            else "same_project_worker_patch_not_ready"
        )
        payload["post_worker_machine_gate"] = post_worker_gate
        payload["machine_gate_repair_loop"] = {
            "schema_version": "commercial_game_post_worker_machine_gate_repair_loop_v1",
            "enabled": True,
            "eligible": False,
            "suppressed_reason": suppressed_reason,
            "repair_attempt_count": 0,
            "max_repair_attempts": max_repair_attempts,
            "history": [],
            "repairable_machine_blockers": list(post_worker_gate.get("repairable_machine_blockers") or []),
            "unrepairable_machine_blockers": list(post_worker_gate.get("unrepairable_machine_blockers") or []),
            "human_only_blockers": list(post_worker_gate.get("human_only_blockers") or []),
            "machine_evidence_go": bool(post_worker_gate.get("machine_evidence_go")),
            "exhausted": False,
        }
        return {
            "payload": payload,
            "patch_ledger": patch_ledger,
            "runtime_evidence": runtime_evidence,
            "ecosystem_evidence": ecosystem_evidence,
        }

    for repair_round in range(1, max(0, max_repair_attempts) + 1):
        repair_cards = _build_machine_gate_repair_cards(
            pipeline_id=pipeline_id,
            project_dir=project_dir,
            run_root=run_root,
            repair_round=repair_round,
            post_worker_gate=post_worker_gate,
            runtime_evidence=runtime_evidence,
            ecosystem_evidence=ecosystem_evidence,
            game_design_contract=game_design_contract,
        )
        repair_cards = [card for card in repair_cards if card.task_card_id not in generated_repair_card_ids]
        if not repair_cards:
            break
        generated_repair_card_ids.update(card.task_card_id for card in repair_cards)
        generated_repair_cards.extend(repair_cards)
        db_report = _persist_machine_gate_repair_cards(db_path=db_path, cards=repair_cards)
        executable_cards.extend(repair_cards)
        quality = task_card_quality_report([*task_cards, *generated_repair_cards])
        patch_ledger = execute_same_project_task_cards(
            root=root,
            run_root=run_root,
            project_dir=project_dir,
            pipeline_id=pipeline_id,
            db_path=db_path,
            task_cards=executable_cards,
            max_repair_attempts=max_repair_attempts,
            task_card_runner=task_card_runner,
        )
        if patch_ledger.get("same_project_worker_patch_go"):
            prebuild_ecosystem_evidence = collect_cocos_ecosystem_bridge_evidence(
                project_path=project_dir,
                creator_exe=creator_exe,
                evidence_dir=run_root / "cocos_ecosystem",
                require_bridge=require_cocos_ecosystem,
                bridge_mode=cocos_bridge_mode,
                bridge_timeout_seconds=cocos_bridge_timeout_seconds,
                bridge_report_path=cocos_bridge_report_path,
                allow_existing_cocos_process=allow_existing_cocos_process,
            )
            runtime_evidence = collect_project_runtime_evidence(
                project_dir=project_dir,
                creator_exe=creator_exe,
                require_build=require_build,
                require_playtest=require_playtest,
            )
        else:
            prebuild_ecosystem_evidence = {}
            runtime_evidence = blocked_project_runtime_evidence_due_to_upstream(
                project_dir=project_dir,
                patch_ledger=patch_ledger,
                require_build=require_build,
                require_playtest=require_playtest,
            )
        ecosystem_evidence = collect_cocos_ecosystem_bridge_evidence(
            project_path=project_dir,
            creator_exe=creator_exe,
            evidence_dir=run_root / "cocos_ecosystem",
            require_bridge=require_cocos_ecosystem,
            bridge_mode="report_only",
            bridge_timeout_seconds=cocos_bridge_timeout_seconds,
            bridge_report_path=cocos_bridge_report_path,
            allow_existing_cocos_process=allow_existing_cocos_process,
        )
        _merge_prebuild_ecosystem_evidence(ecosystem_evidence, prebuild_ecosystem_evidence)
        payload = production_payload_from_worker(
            schema_version=COMMERCIAL_GAME_WORKER_SCHEMA,
            created_at=_utc_now(),
            pipeline_id=pipeline_id,
            project_dir=project_dir,
            task_card_quality=quality,
            runtime_evidence=runtime_evidence,
            assets_stage=assets_stage,
            ecosystem_evidence=ecosystem_evidence,
            patch_ledger=patch_ledger,
            skipped_task_cards=[card.task_card_id for card in task_cards if card not in business_cards],
            max_repair_attempts=max_repair_attempts,
            dedupe_strings=_dedupe_strings,
            blocker_details=_blocker_details,
            recoverable_suggestions=_recoverable_suggestions,
        )
        post_worker_gate = _post_worker_machine_gate_report(
            shared_outputs=shared_outputs,
            production_payload=payload,
            ecosystem_evidence=ecosystem_evidence,
            require_commercial=require_commercial,
            require_cocos_ecosystem=require_cocos_ecosystem,
        )
        repair_history.append(
            {
                "repair_round": repair_round,
                "task_card_ids": [card.task_card_id for card in repair_cards],
                "db": db_report,
                "patch_ledger_go": bool(patch_ledger.get("same_project_worker_patch_go")),
                "post_repair_machine_evidence_go": bool(post_worker_gate.get("machine_evidence_go")),
                "remaining_repairable_blockers": list(post_worker_gate.get("repairable_machine_blockers") or []),
            }
        )
        if not patch_ledger.get("same_project_worker_patch_go"):
            break

    payload["post_worker_machine_gate"] = post_worker_gate
    payload["machine_gate_repair_loop"] = {
        "schema_version": "commercial_game_post_worker_machine_gate_repair_loop_v1",
        "enabled": True,
        "repair_attempt_count": len(repair_history),
        "max_repair_attempts": max_repair_attempts,
        "history": repair_history,
        "repairable_machine_blockers": list(post_worker_gate.get("repairable_machine_blockers") or []),
        "unrepairable_machine_blockers": list(post_worker_gate.get("unrepairable_machine_blockers") or []),
        "human_only_blockers": list(post_worker_gate.get("human_only_blockers") or []),
        "machine_evidence_go": bool(post_worker_gate.get("machine_evidence_go")),
        "exhausted": bool(post_worker_gate.get("repairable_machine_blockers")) and len(repair_history) >= max_repair_attempts,
    }
    return {
        "payload": payload,
        "patch_ledger": patch_ledger,
        "runtime_evidence": runtime_evidence,
        "ecosystem_evidence": ecosystem_evidence,
    }


def _post_worker_machine_gate_report(
    *,
    shared_outputs: dict[str, Any],
    production_payload: dict[str, Any],
    ecosystem_evidence: dict[str, Any],
    require_commercial: bool,
    require_cocos_ecosystem: bool,
) -> dict[str, Any]:
    gate_shared_outputs = {
        **shared_outputs,
        "commercial_game_production": production_payload,
        "cocos_ecosystem_evidence": ecosystem_evidence,
    }
    no_degradation = evaluate_no_degradation_contract(
        shared_outputs=gate_shared_outputs,
        production=production_payload,
        require_commercial=require_commercial,
        require_cocos_ecosystem=require_cocos_ecosystem,
        require_live_agent_roles=False,
        require_human_player_review=False,
    )
    final_gate = no_degradation.get("commercial_final_gate_evidence") if isinstance(no_degradation, dict) else {}
    machine_blockers = _dedupe_strings(
        [
            *list(final_gate.get("machine_blockers") or []),
            *[
                blocker
                for blocker in no_degradation.get("blockers") or []
                if blocker not in MACHINE_GATE_REPAIR_HUMAN_ONLY_BLOCKERS
            ],
        ]
    )
    human_only = [blocker for blocker in no_degradation.get("blockers") or [] if blocker in MACHINE_GATE_REPAIR_HUMAN_ONLY_BLOCKERS]
    repairable = _repairable_machine_gate_blockers(machine_blockers)
    return {
        "schema_version": "commercial_game_post_worker_machine_gate_report_v1",
        "go_no_go": no_degradation.get("go_no_go"),
        "machine_evidence_go": bool(no_degradation.get("machine_evidence_go")),
        "machine_blockers": machine_blockers,
        "repairable_machine_blockers": repairable,
        "unrepairable_machine_blockers": [blocker for blocker in machine_blockers if blocker not in set(repairable)],
        "human_only_blockers": human_only,
        "no_degradation_contract": no_degradation,
    }


def _repairable_machine_gate_blockers(blockers: list[str]) -> list[str]:
    repairable: list[str] = []
    for blocker in blockers:
        text = str(blocker)
        if text in MACHINE_GATE_REPAIR_HUMAN_ONLY_BLOCKERS or text in MACHINE_GATE_REPAIR_EXTERNAL_INPUT_BLOCKERS:
            continue
        if text.strip():
            repairable.append(text)
    return _dedupe_strings(repairable)


def _build_machine_gate_repair_cards(
    *,
    pipeline_id: str,
    project_dir: Path,
    run_root: Path,
    repair_round: int,
    post_worker_gate: dict[str, Any],
    runtime_evidence: dict[str, Any],
    ecosystem_evidence: dict[str, Any],
    game_design_contract: dict[str, Any],
) -> list[TaskCard]:
    blockers = list(post_worker_gate.get("repairable_machine_blockers") or [])
    cluster = _machine_gate_repair_cluster(blockers)
    if cluster is None:
        return []
    target_blockers = _machine_gate_repair_blockers_for_cluster(cluster, blockers)
    deferred_blockers = [blocker for blocker in blockers if blocker not in set(target_blockers)]
    task_card_id = f"{pipeline_id}_machine_gate_repair_{repair_round:02d}_{cluster}"
    read_set = _machine_gate_repair_read_set(
        project_dir=project_dir,
        run_root=run_root,
        cluster=cluster,
        runtime_evidence=runtime_evidence,
        ecosystem_evidence=ecosystem_evidence,
        game_design_contract=game_design_contract,
    )
    write_set = _machine_gate_repair_write_set(cluster)
    title = _machine_gate_repair_title(cluster)
    guidance = _machine_gate_repair_guidance(cluster, target_blockers, deferred_blockers=deferred_blockers)
    return [
        TaskCard(
            run_id=pipeline_id,
            task_card_id=task_card_id,
            title=title,
            description=(
                f"Repair post-worker machine gate blockers after implementation cards completed. "
                f"Target cluster: {cluster}. Blockers: {', '.join(target_blockers)}."
            ),
            goal=(
                "Fix the current same-project commercial Cocos game so the next machine gate run resolves these "
                f"blockers without waiting for human review: {', '.join(target_blockers)}."
            ),
            milestone="Universal Game Production Quality",
            phase_name="Commercial Game Machine Gate Repair",
            write_set=write_set,
            read_set=read_set,
            test_commands=_machine_gate_repair_tests(cluster),
            expected_artifacts=_machine_gate_repair_expected_artifacts(cluster),
            acceptance_criteria=[
                "The next runtime evidence collection no longer reports the targeted machine blockers",
                "The repair changes the same Cocos project and does not create a replacement project or fixed template",
                "Evidence JSON names real files and stays synchronized with scene, script, prefab, and build outputs",
            ],
            evidence_requirements=[
                "fresh_worker_receipt",
                "changed_files",
                "passing_tests",
                "human_visible_cli_session",
                "direct_provider_visible_cli_session",
                "workflow_runtime_evidence/machine_gate_repair_evidence.json",
            ],
            blocking_conditions=[
                "targeted_machine_blocker_still_present_after_repair",
                "repair_claims_build_or_playtest_without fresh Cocos or browser evidence",
                "repair_replaces_project_or_reintroduces_fixed_template_delivery",
            ],
            model_guidance=guidance,
            risk_level="high",
            execution_mode="same_project_patch",
            status="active",
            metadata={
                "task_card_generation_source": MACHINE_GATE_REPAIR_CARD_SOURCE,
                "phase_execution_blueprint_schema": PHASE_EXECUTION_BLUEPRINT_SCHEMA,
                "task_card_compile_report_schema": TASK_CARD_COMPILE_REPORT_SCHEMA,
                "task_card_compile_go": True,
                "task_card_compile_blockers": [],
                "machine_gate_repair_card": True,
                "machine_gate_repair_round": repair_round,
                "machine_gate_repair_cluster": cluster,
                "machine_gate_blockers": target_blockers,
                "deferred_machine_gate_blockers": deferred_blockers,
                "requirement_coverage_required": False,
                "covered_requirement_ids": [],
                "missing_requirement_ids": [],
                "human_visible_cli_required": True,
                "execution_visibility_mode": "human_visible_cli_enforced",
                "control_plane_visibility": "resident",
                "provider_visibility": "direct_visible",
                "provider_output_mode": "human_readable",
            },
        )
    ]


def _machine_gate_repair_cluster(blockers: list[str]) -> str | None:
    blocker_set = set(blockers)
    if blocker_set & MACHINE_GATE_REPAIR_BUILD_BLOCKERS or any(
        item.startswith("cocos_build_")
        or item.startswith("semantic_")
        or item.startswith("gameplay_semantic_")
        or item.startswith("product_body_")
        for item in blocker_set
    ):
        return "cocos_build_product_body"
    if blocker_set & MACHINE_GATE_REPAIR_BROWSER_BLOCKERS or any(
        item.startswith("browser_")
        or item.startswith("desktop_")
        or item.startswith("missing_playtest_feature_")
        or item.startswith("missing_commercial_feature_")
        or item.startswith("missing_reference_feature_")
        or item.startswith("reference_quality_")
        for item in blocker_set
    ):
        return "browser_playtest_runtime"
    if blocker_set & MACHINE_GATE_REPAIR_DEPTH_BLOCKERS or any(
        item.startswith("product_depth_") or item.startswith("level_") for item in blocker_set
    ):
        return "product_depth"
    if blocker_set & MACHINE_GATE_REPAIR_AI_BLOCKERS or any(item.startswith("ai_") for item in blocker_set):
        return "ai_surrogate_playtest"
    return "general_machine_gate" if blocker_set else None


def _machine_gate_repair_blockers_for_cluster(cluster: str, blockers: list[str]) -> list[str]:
    selected: list[str] = []
    for blocker in blockers:
        text = str(blocker)
        if _machine_gate_repair_cluster([text]) == cluster:
            selected.append(text)
    return _dedupe_strings(selected or blockers)


def _machine_gate_repair_write_set(cluster: str) -> list[str]:
    if cluster == "cocos_build_product_body":
        return [
            "assets/scripts/**",
            "assets/scene/**",
            "assets/prefabs/**",
            "assets/workflow_bridge_probe/**",
            "settings/v2/packages/scene.json",
            "workflow_runtime_evidence/**",
            "workflow_commercial_feature_evidence.json",
        ]
    if cluster == "browser_playtest_runtime":
        return [
            "assets/scripts/**",
            "assets/resources/**",
            "player_visible_evidence/**",
            "workflow_runtime_evidence/**",
            "workflow_commercial_feature_evidence.json",
        ]
    if cluster == "product_depth":
        return [
            "assets/scripts/runtime/**",
            "assets/resources/content/**",
            "assets/resources/localization/**",
            "workflow_runtime_evidence/**",
            "workflow_commercial_feature_evidence.json",
        ]
    if cluster == "ai_surrogate_playtest":
        return [
            "state/ai_playtest/**",
            "state/task_cards/**",
            "workflow_runtime_evidence/**",
        ]
    return ["assets/**", "settings/**", "workflow_runtime_evidence/**", "workflow_commercial_feature_evidence.json"]


def _machine_gate_repair_read_set(
    *,
    project_dir: Path,
    run_root: Path,
    cluster: str,
    runtime_evidence: dict[str, Any],
    ecosystem_evidence: dict[str, Any],
    game_design_contract: dict[str, Any],
) -> list[str]:
    core_candidates = [
        project_dir / "cocos_build_stdout.log",
        project_dir / "cocos_build_stderr.log",
        project_dir / "temp" / "logs" / "project.log",
        project_dir / "settings" / "v2" / "packages" / "scene.json",
        run_root / "cocos_ecosystem" / "cocos_ecosystem_bridge_evidence.json",
        ecosystem_evidence.get("evidence_path"),
    ]
    if cluster == "cocos_build_product_body":
        candidates = [
            *core_candidates,
            project_dir / "assets" / "scene" / "block_puzzle_player_visible.scene",
            project_dir / "assets" / "scene" / "workflow_bridge_scene.scene",
            *_existing_paths(
                [
                    project_dir / "assets" / "scripts" / "runtime" / "gameplay" / "BlockPuzzleRuntimeController.ts",
                    project_dir / "assets" / "scripts" / "runtime" / "input" / "BlockPuzzleInputController.ts",
                    project_dir / "assets" / "scripts" / "runtime" / "input" / "SceneInputFeedbackBinder.ts",
                    project_dir / "assets" / "scripts" / "runtime" / "model" / "BlockPuzzleModel.ts",
                    project_dir / "assets" / "scripts" / "runtime" / "model" / "BlockPuzzleTypes.ts",
                    project_dir / "assets" / "scripts" / "runtime" / "systems" / "CommercialRulesAndScoring.ts",
                    project_dir / "assets" / "scripts" / "runtime" / "ui" / "CommercialHud.ts",
                    project_dir / "assets" / "scripts" / "workflow-e2e-runtime-bridge.js",
                ]
            ),
            project_dir / "assets" / "scripts" / "runtime" / "workflow" / "WorkflowBlockPuzzleBoardBinding.ts",
            project_dir / "assets" / "scripts" / "runtime" / "workflow" / "WorkflowBlockPuzzleSceneRuntime.ts",
            project_dir / "assets" / "scripts" / "runtime" / "workflow" / "WorkflowCandidateTrayBinding.ts",
            project_dir / "assets" / "scripts" / "runtime" / "workflow" / "WorkflowCandidatePrefabBinding.ts",
            project_dir / "assets" / "scripts" / "runtime" / "workflow" / "WorkflowBuildProductBodyWitness.ts",
            project_dir / "assets" / "prefabs" / "workflow_block_puzzle_board_binding.prefab",
            project_dir / "workflow_runtime_evidence" / "build_ledger.json",
            project_dir / "workflow_runtime_evidence" / "machine_gate_repair_evidence.json",
            project_dir / "workflow_runtime_evidence" / "product_body_evidence.json",
            project_dir / "workflow_runtime_evidence" / "product_body_evidence.raw.json",
            project_dir / "workflow_runtime_evidence" / "scene_prefab_binding_evidence.json",
            project_dir / "workflow_commercial_feature_evidence.json",
            runtime_evidence.get("build_ledger_path"),
        ]
    elif cluster == "browser_playtest_runtime":
        candidates = [
            *core_candidates,
            project_dir / "assets" / "scripts" / "runtime" / "audio" / "CommercialAudioRuntime.ts",
            project_dir / "assets" / "scripts" / "runtime" / "effects" / "CommercialFeedbackAnimator.ts",
            project_dir / "assets" / "scripts" / "runtime" / "ui" / "CommercialHud.ts",
            project_dir / "assets" / "scripts" / "workflow-e2e-runtime-bridge.js",
            project_dir / "workflow_runtime_evidence" / "build_ledger.json",
            project_dir / "workflow_runtime_evidence" / "browser_playtest_ledger.json",
            project_dir / "workflow_runtime_evidence" / "reference_quality_evidence.json",
            runtime_evidence.get("build_ledger_path"),
            runtime_evidence.get("browser_playtest_ledger_path"),
            runtime_evidence.get("reference_quality_evidence_path"),
        ]
    elif cluster == "product_depth":
        candidates = [
            game_design_contract.get("game_design_spec_path"),
            game_design_contract.get("requirement_matrix_path"),
            project_dir / "assets" / "resources" / "content" / "level_goal_matrix.json",
            project_dir / "assets" / "resources" / "content" / "reward_gallery_matrix.json",
            project_dir / "assets" / "resources" / "localization" / "zh-CN.json",
            project_dir / "assets" / "scripts" / "runtime" / "systems" / "CommercialProgression.ts",
            project_dir / "assets" / "scripts" / "runtime" / "ui" / "CommercialPanels.ts",
            project_dir / "workflow_runtime_evidence" / "product_depth_evidence.json",
            project_dir / "workflow_runtime_evidence" / "product_depth_evidence.raw.json",
        ]
    elif cluster == "ai_surrogate_playtest":
        candidates = [
            "TestOracleSpec",
            "QualityRubric",
            game_design_contract.get("game_design_spec_path"),
            game_design_contract.get("requirement_matrix_path"),
            project_dir / "workflow_runtime_evidence" / "build_ledger.json",
            project_dir / "workflow_runtime_evidence" / "browser_playtest_ledger.json",
            runtime_evidence.get("browser_playtest_ledger_path"),
        ]
    else:
        candidates = [
            *core_candidates,
            game_design_contract.get("game_design_spec_path"),
            game_design_contract.get("requirement_matrix_path"),
            project_dir / "assets" / "scene" / "block_puzzle_player_visible.scene",
            project_dir / "workflow_runtime_evidence" / "build_ledger.json",
            project_dir / "workflow_runtime_evidence" / "browser_playtest_ledger.json",
        ]
    result: list[str] = []
    for item in candidates:
        if item is None:
            continue
        text = item.as_posix() if isinstance(item, Path) else str(item)
        if text and text not in result:
            result.append(text)
    return result


def _existing_paths(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.exists()]


def _machine_gate_repair_title(cluster: str) -> str:
    return {
        "cocos_build_product_body": "Repair Cocos build and engine-native product body blockers",
        "browser_playtest_runtime": "Repair browser playtest and runtime evidence blockers",
        "product_depth": "Repair product depth and player-visible feature blockers",
        "ai_surrogate_playtest": "Repair AI surrogate playtest inputs and execution blockers",
    }.get(cluster, "Repair post-worker machine gate blockers")


def _machine_gate_repair_tests(cluster: str) -> list[str]:
    tests = ["python -m pytest tests/test_commercial_game_evidence_contracts.py -q"]
    if cluster in {"cocos_build_product_body", "browser_playtest_runtime"}:
        tests.insert(0, "python -m pytest tests/test_engine_native_product_body_contract.py tests/test_ai_playtest_execution_packet.py -q")
    if cluster == "ai_surrogate_playtest":
        tests.insert(0, "python -m pytest tests/test_ai_playtest_quality_gate.py tests/test_game_repair_loop_from_ai_findings.py -q")
    tests.append("python -m infra.scripts.check_doc_links")
    return tests


def _machine_gate_repair_expected_artifacts(cluster: str) -> list[str]:
    if cluster == "cocos_build_product_body":
        return [
            *COCOS_PRODUCT_BODY_COMPONENT_ARTIFACTS,
            "workflow_runtime_evidence/machine_gate_repair_evidence.json",
            "workflow_runtime_evidence/cocos_ecosystem_bridge_evidence.json",
            "workflow_runtime_evidence/product_body_evidence.raw.json",
            "workflow_runtime_evidence/scene_prefab_binding_evidence.json",
            "settings/v2/packages/scene.json",
        ]
    if cluster == "product_depth":
        return [
            "workflow_runtime_evidence/machine_gate_repair_evidence.json",
            "workflow_runtime_evidence/product_depth_evidence.raw.json",
            "workflow_runtime_evidence/level_goal_evidence.json",
        ]
    return ["workflow_runtime_evidence/machine_gate_repair_evidence.json"]


def _machine_gate_repair_guidance(cluster: str, blockers: list[str], *, deferred_blockers: list[str]) -> list[str]:
    common = [
        "Treat the listed machine blockers as workflow-owned repair inputs; do not wait for human review to repair machine-verifiable failures.",
        "Patch only the current same Cocos project and keep source requirements preserved.",
        "Do not mark a stage completed with simulated, skipped, feature-flag-only, screenshot-only, or stale evidence.",
        f"Target blockers: {', '.join(blockers)}.",
    ]
    if deferred_blockers:
        common.append(
            "This card is intentionally narrowed; leave deferred blockers for later repair cards: "
            f"{', '.join(deferred_blockers)}."
        )
    if cluster == "cocos_build_product_body":
        return [
            *common,
            "Read the Cocos build logs first and fix the first fatal compiler or AssetDB marker.",
            "Before creating a workflow component file, check the read-set context; if it already exists, emit an existing-file patch instead of a new-file /dev/null diff.",
            "Every Workflow* class named by Cocos Missing class or script-invalid logs must have exactly one matching exported @ccclass TypeScript component under assets/scripts/runtime/workflow.",
            "If an expected JSON artifact already exists, update it in place as exactly one valid JSON document; do not append a second JSON object, and do not delete then recreate the same artifact path.",
            "If a .scene or .prefab attaches a generated Workflow* component, serialize the Cocos script RF id from the .meta/compiled _RF.push record instead of the plain @ccclass name; plain class names cause Missing class during Creator build.",
            "Do not leave missing or invalid Workflow* scene components; Cocos Creator must be able to import the launch scene without Missing class errors.",
            "Keep product body evidence aligned with actual scene nodes, prefabs, settings current-scene uuid, and component files.",
        ]
    if cluster == "browser_playtest_runtime":
        return [
            *common,
            "Repair launch/runtime code so browser playtest can start over HTTP and capture desktop and mobile screenshots.",
            "When reference_quality blockers are present, match or exceed the configured reference playtest feature coverage, score, event depth, open panels, and screenshot evidence.",
            "Audio evidence must come from runtime playback/toggle state, not an asset manifest alone.",
        ]
    if cluster == "product_depth":
        return [
            *common,
            "Materialize at least eight distinct level goals, shop ownership states, visible skin equip changes, readable Chinese panels, and failure/revive feedback.",
            "Evidence must be player-visible or runtime-state backed, not only a design checklist.",
        ]
    if cluster == "ai_surrogate_playtest":
        return [
            *common,
            "Materialize TestOracleSpec, QualityRubric, latest build artifact references, replay artifacts, screenshots, and requirement coverage traces.",
            "AI can clear machine readiness only; it must not set human_player_review_go.",
        ]
    return common


def _persist_machine_gate_repair_cards(*, db_path: Path | None, cards: list[TaskCard]) -> dict[str, Any] | None:
    if db_path is None or not cards:
        return None
    repo = TaskRepository(db_path)
    created: list[str] = []
    updated: list[str] = []
    for card in cards:
        existed = repo.get_task_card(card.task_card_id) is not None
        repo.upsert_task_card(card)
        if existed:
            updated.append(card.task_card_id)
        else:
            created.append(card.task_card_id)
    return {
        "db_path": db_path.as_posix(),
        "write_mode": "upsert_current_repair_card",
        "created_task_card_ids": created,
        "updated_task_card_ids": updated,
    }


def _merge_prebuild_ecosystem_evidence(ecosystem_evidence: dict[str, Any], prebuild_ecosystem_evidence: dict[str, Any]) -> None:
    if prebuild_ecosystem_evidence.get("bridge_runner_evidence") and not ecosystem_evidence.get("bridge_runner_evidence"):
        ecosystem_evidence["bridge_runner_evidence"] = prebuild_ecosystem_evidence["bridge_runner_evidence"]
    if prebuild_ecosystem_evidence:
        ecosystem_evidence["prebuild_bridge_evidence"] = {
            "ecosystem_integration_go": bool(prebuild_ecosystem_evidence.get("ecosystem_integration_go")),
            "failure_class": prebuild_ecosystem_evidence.get("failure_class"),
            "blockers": list(prebuild_ecosystem_evidence.get("blockers") or []),
            "evidence_path": prebuild_ecosystem_evidence.get("evidence_path"),
        }
    if ecosystem_evidence.get("ecosystem_integration_go"):
        ecosystem_evidence.pop("failure_class", None)
        ecosystem_evidence["blockers"] = []
        ecosystem_evidence["operator_action_required"] = False
        ecosystem_evidence["operator_actions"] = []
        return
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


def build_supervisor_repair_packets(
    *,
    structured_output: dict[str, Any],
    shared_outputs: dict[str, Any],
    max_repair_attempts: int = 3,
) -> list[dict[str, Any]]:
    findings: list[Any] = []
    production = shared_outputs.get("commercial_game_production")
    if isinstance(production, dict):
        findings.extend(production.get("commercial_playable_blockers") or [])
    assets_stage = shared_outputs.get("commercial_game_assets")
    if isinstance(assets_stage, dict):
        findings.extend(assets_stage.get("commercial_asset_blockers") or [])
        if assets_stage.get("placeholder_only"):
            findings.append("placeholder_assets_only")
    qa = shared_outputs.get("role_output:qa_player_perspective_agent")
    if isinstance(qa, dict):
        qa_structured = qa.get("structured_output")
        if isinstance(qa_structured, dict):
            findings.extend(qa_structured.get("repair_findings") or [])
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
    unique_findings = [
        *[item for item in unique_findings if _external_input_blocker(item) is not None],
        *[item for item in unique_findings if _external_input_blocker(item) is None],
    ]

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


def _build_game_design_spec_contract(*, run_root: Path, pipeline_id: str, source_path: Path) -> dict[str, Any]:
    output_root = run_root / "source_truth"
    try:
        brief_manifest = build_unified_project_brief(
            input_paths=[source_path],
            output_dir=output_root / "unified_brief",
            title=f"{pipeline_id} commercial game source truth",
            preserve_raw=True,
        )
        requirement_matrix = _read_json_dict(Path(str(brief_manifest.get("requirement_matrix_path") or "")))
        source_index = _read_json_list(Path(str(brief_manifest.get("source_index_path") or "")))
        spec = build_game_design_spec_from_requirement_matrix(
            title=f"{pipeline_id} GameDesignSpec",
            intake_manifest=brief_manifest,
            requirement_matrix=requirement_matrix,
            source_index=source_index,
        )
        spec_payload = spec.to_dict()
        validation = validate_game_design_spec(spec_payload)
        spec_path = output_root / "game_design_spec.json"
        validation_path = output_root / "game_design_spec_validation.json"
        _write_json(spec_path, spec_payload)
        _write_json(validation_path, validation)
        return {
            "schema_version": "commercial_game_design_spec_contract_v1",
            "go": bool(validation.get("go")),
            "blockers": list(validation.get("blockers") or []),
            "game_design_spec_schema": spec_payload.get("schema_version"),
            "source_material_policy": spec_payload.get("source_material_policy"),
            "source_count": spec_payload.get("source_count"),
            "input_count": spec_payload.get("input_count"),
            "requirement_count": spec_payload.get("requirement_count"),
            "preserved_requirement_count": len(spec_payload.get("preserved_requirement_ids") or []),
            "omitted_requirement_ids": spec_payload.get("omitted_requirement_ids") or [],
            "game_design_spec_path": spec_path.as_posix(),
            "validation_path": validation_path.as_posix(),
            "unified_brief_manifest_path": brief_manifest.get("intake_manifest_path"),
            "requirement_matrix_path": brief_manifest.get("requirement_matrix_path"),
        }
    except Exception as exc:
        blockers = [f"game_design_spec_build_failed:{exc.__class__.__name__}"]
        if "no chunks or media" in str(exc):
            blockers.append("source_requirements_missing")
        payload = {
            "schema_version": "commercial_game_design_spec_contract_v1",
            "go": False,
            "blockers": blockers,
            "failure": str(exc),
        }
        _write_json(output_root / "game_design_spec_contract_failed.json", payload)
        return payload


def _commercial_task_card_compile_blockers(task_cards: list[Any]) -> list[str]:
    blockers: list[str] = []
    allowed_sources = {"active_phase_execution_blueprint", MACHINE_GATE_REPAIR_CARD_SOURCE}
    for card in task_cards:
        metadata = card.metadata if isinstance(card.metadata, dict) else {}
        prefix = f"{card.task_card_id}:"
        if metadata.get("task_card_generation_source") not in allowed_sources:
            blockers.append(f"{prefix}task_card_not_from_active_phase_blueprint")
        if metadata.get("phase_execution_blueprint_schema") != PHASE_EXECUTION_BLUEPRINT_SCHEMA:
            blockers.append(f"{prefix}phase_execution_blueprint_schema_missing")
        if metadata.get("task_card_compile_report_schema") != TASK_CARD_COMPILE_REPORT_SCHEMA:
            blockers.append(f"{prefix}task_card_compile_report_missing")
        if metadata.get("task_card_compile_go") is not True:
            blockers.append(f"{prefix}task_card_compile_no_go")
        if metadata.get("task_card_compile_blockers"):
            blockers.append(f"{prefix}task_card_compile_blockers_present")
        covered_ids = [str(req_id) for req_id in metadata.get("covered_requirement_ids") or [] if str(req_id).strip()]
        coverage_required = metadata.get("requirement_coverage_required") is not False
        if coverage_required and not covered_ids:
            blockers.append(f"{prefix}task_card_req_id_coverage_missing")
        if coverage_required and metadata.get("missing_requirement_ids"):
            blockers.append(f"{prefix}task_card_compile_missing_requirement_ids")
    return _dedupe_strings(blockers)


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
    development_readiness = build_commercial_game_development_readiness_evidence(
        task_card_quality=task_card_quality,
        same_project_worker_gate_present=False,
        requirement_coverage_gate_present="requirement_coverage_blocked_count" in task_card_quality,
        commercial_playable_go=commercial_playable_go,
        human_player_review_go=False,
    )
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
        "commercial_game_development_readiness_go": False,
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
        "commercial_game_development_readiness": development_readiness,
        "max_repair_attempts": max_repair_attempts,
        "repair_policy": "same_project_incremental_repair",
        "forbids_fixed_template": True,
    }


def _write_worker_manifest(project_dir: Path, payload: dict[str, Any]) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    _write_json(project_dir / "workflow_project_manifest.json", payload)


def _style_prompt(shared_outputs: dict[str, Any]) -> str:
    ui = shared_outputs.get("role_output:ui_experience_agent")
    ui_polish = shared_outputs.get("role_output:ui_ux_polish_agent")
    art = shared_outputs.get("role_output:art_direction_agent")
    animation = shared_outputs.get("role_output:animation_vfx_feedback_agent")
    audio = shared_outputs.get("role_output:audio_feedback_designer_agent")
    product = shared_outputs.get("role_output:product_gameplay_agent")
    mechanics = shared_outputs.get("role_output:mechanics_system_designer_agent")
    level_economy = shared_outputs.get("role_output:level_economy_designer_agent")
    signals = []
    for item in (product, mechanics, level_economy, ui, ui_polish, art, animation, audio):
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


def _reusable_commercial_asset_stage(
    *,
    asset_root: Path,
    source_path: Path | None,
    game_design_contract: dict[str, Any],
) -> dict[str, Any] | None:
    payload_path = asset_root / "commercial_game_asset_stage.json"
    payload = _read_json_dict(payload_path)
    if not payload:
        return None
    if payload.get("commercial_assets_go") is not True:
        return None
    if payload.get("placeholder_only") or payload.get("asset_generation_skipped"):
        return None
    manifest = payload.get("asset_manifest") if isinstance(payload.get("asset_manifest"), dict) else {}
    manifest_path = Path(str(payload.get("asset_manifest_path") or manifest.get("manifest_path") or ""))
    if not manifest_path.is_absolute():
        manifest_path = asset_root / manifest_path
    if manifest.get("go_no_go") != "GO" or not manifest_path.exists():
        return None
    if not _commercial_asset_artifacts_exist(manifest):
        return None

    current_source_identity = _source_identity_for_stage(source_path) if source_path is not None else {}
    previous_source_identity = payload.get("source_identity") if isinstance(payload.get("source_identity"), dict) else {}
    if previous_source_identity and current_source_identity:
        if previous_source_identity.get("source_sha256") != current_source_identity.get("source_sha256"):
            return None

    reused_payload = {
        **payload,
        "created_at": _utc_now(),
        "asset_manifest_path": manifest_path.as_posix(),
        "asset_manifest": manifest,
        "game_design_spec_contract": game_design_contract or payload.get("game_design_spec_contract") or {},
        "source_identity": current_source_identity or previous_source_identity,
        "reused_existing_asset_stage": True,
        "reuse_reason": "same_pipeline_valid_commercial_assets_go_manifest",
        "reuse_source_identity_status": (
            "matched"
            if previous_source_identity and current_source_identity
            else "legacy_missing_assumed_same_pipeline_id"
        ),
        "evidence_path": payload_path.as_posix(),
    }
    _write_json(payload_path, reused_payload)
    return reused_payload


def _commercial_asset_artifacts_exist(manifest: dict[str, Any]) -> bool:
    results = manifest.get("results")
    if not isinstance(results, list) or not results:
        return False
    completed_with_artifacts = 0
    for item in results:
        if not isinstance(item, dict) or item.get("status") != "completed":
            continue
        artifact_paths = [Path(str(path)) for path in item.get("artifact_paths") or [] if str(path)]
        if not artifact_paths:
            continue
        if not all(path.exists() for path in artifact_paths):
            return False
        completed_with_artifacts += 1
    return completed_with_artifacts > 0


def _source_identity_for_stage(source_path: Path | None) -> dict[str, str]:
    if source_path is None or not source_path.exists():
        return {}
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


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
