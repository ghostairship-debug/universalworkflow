from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contracts import PipelineStage, Run, TaskCard
from packages.core_domain.db import migrate
from packages.core_domain.multimodal_route_plan import build_multimodal_route_plan
from packages.core_domain.repositories import RunRepository, TaskRepository
from packages.core_domain.task_card_store import export_task_cards_markdown, task_card_quality_report
from packages.core_domain.unified_project_brief import build_unified_project_brief
from packages.contributions.games.game_design_ir import (
    build_game_design_spec,
    build_game_design_spec_from_requirement_matrix,
)
from packages.contributions.games.game_task_card_generation import (
    build_game_production_task_cards_from_design_spec,
    build_phase_execution_blueprint,
    build_product_phase_candidates_from_design_spec,
    compile_task_cards_from_phase_execution_blueprint,
)
from packages.contributions.games.commercial_quality_score import evaluate_commercial_quality_scorecard


SOURCE_MATERIAL_POLICY = "no_delete_no_merge_no_rename_only_augment"


ROLE_MODEL_PROFILES: dict[str, dict[str, str]] = {
    "intake_packaging_agent": {
        "model_tier": "medium_strong",
        "default_lane": "configured_text_model",
        "reason": "organizes source material without replacing it with a summary",
    },
    "product_gameplay_agent": {
        "model_tier": "medium_strong",
        "default_lane": "configured_text_model",
        "reason": "needs product judgment and gameplay design",
    },
    "mechanics_system_designer_agent": {
        "model_tier": "strong",
        "default_lane": "codex_or_configured_strong_model",
        "reason": "turns source rules into stateful mechanics, edge cases, and feel constraints",
    },
    "level_economy_designer_agent": {
        "model_tier": "medium_strong",
        "default_lane": "configured_text_model",
        "reason": "balances level pacing, progression, rewards, and retention loops",
    },
    "ui_experience_agent": {
        "model_tier": "medium_strong",
        "default_lane": "configured_text_model",
        "reason": "needs visual and interaction judgment",
    },
    "ui_ux_polish_agent": {
        "model_tier": "medium_strong",
        "default_lane": "configured_text_or_visual_review_model",
        "reason": "reviews commercial UI polish, readability, ergonomic flow, and screenshot quality",
    },
    "art_direction_agent": {
        "model_tier": "medium_strong",
        "default_lane": "configured_text_or_visual_model",
        "reason": "defines coherent art direction and non-placeholder asset acceptance",
    },
    "animation_vfx_feedback_agent": {
        "model_tier": "medium_strong",
        "default_lane": "configured_text_or_visual_model",
        "reason": "sets motion grammar, VFX feedback, and animation evidence requirements",
    },
    "audio_feedback_designer_agent": {
        "model_tier": "medium_strong",
        "default_lane": "configured_text_or_audio_model",
        "reason": "designs BGM, SFX event mapping, mix rules, and runtime audio proof",
    },
    "technical_plan_agent": {
        "model_tier": "strong",
        "default_lane": "codex_or_configured_strong_model",
        "reason": "sets engineering boundaries and downstream task quality",
    },
    "multimodal_generation_agent": {
        "model_tier": "medium_strong",
        "default_lane": "configured_text_model_for_planning_then_api_for_generation",
        "reason": "plans image/audio/music needs while generation uses capability APIs",
    },
    "task_card_generation_agent": {
        "model_tier": "strong",
        "default_lane": "codex_or_configured_strong_model",
        "reason": "bad task cards cause downstream execution drift",
    },
    "ai_playtest_oracle_agent": {
        "model_tier": "strong",
        "default_lane": "configured_text_or_visual_review_model",
        "reason": "defines automated player personas, scorecards, and repair-loop triggers",
    },
    "qa_player_perspective_agent": {
        "model_tier": "medium_strong",
        "default_lane": "configured_text_or_visual_review_model",
        "reason": "reviews player-visible usability and quality",
    },
    "commercial_quality_score_agent": {
        "model_tier": "strong",
        "default_lane": "configured_text_or_visual_review_model",
        "reason": "turns real playtest screenshots, pointer replay, and R5 no-regression into a commercial scorecard",
    },
    "supervisor": {
        "model_tier": "strong",
        "default_lane": "codex_or_configured_strong_model",
        "reason": "decides continue, repair, stop, or cluster upgrade",
    },
}


def execute_single_agent_role_stage(
    stage: PipelineStage,
    *,
    root: Path,
    target_dir: Path,
    shared_outputs: dict[str, Any] | None = None,
    source_path: str | Path | None = None,
    unified_brief_dir: str | Path | None = None,
    db_path: str | Path | None = None,
    pipeline_id: str | None = None,
    pipeline_goal: str | None = None,
    pipeline_template: str | None = None,
    pipeline_name: str | None = None,
    live_agent_roles: bool = False,
) -> dict[str, Any]:
    role_id = str(stage.metadata.get("role_id") or "intake_packaging_agent")
    role_dir = target_dir / "agent_roles" / f"{stage.order_index:02d}_{stage.stage_id}"
    role_dir.mkdir(parents=True, exist_ok=True)
    brief_manifest = _resolve_or_build_brief(
        stage=stage,
        role_dir=role_dir,
        source_path=source_path,
        unified_brief_dir=unified_brief_dir,
    )
    output = _build_role_output(
        stage=stage,
        role_id=role_id,
        role_dir=role_dir,
        brief_manifest=brief_manifest,
        shared_outputs=shared_outputs or {},
        db_path=db_path,
        pipeline_id=pipeline_id,
        pipeline_goal=pipeline_goal,
        pipeline_template=pipeline_template,
        pipeline_name=pipeline_name,
    )
    if live_agent_roles:
        live_payload = _call_live_role_llm(
            role_id=role_id,
            stage=stage,
            structured_output=output["structured_output"],
            brief_manifest=brief_manifest,
        )
        output.update(live_payload["output_updates"])
        if live_payload["status"] != "completed":
            output_path = role_dir / "role_output.json"
            output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
            markdown_path = role_dir / "role_output.md"
            markdown_path.write_text(_render_role_output_markdown(output), encoding="utf-8")
            return {
                "handled": True,
                "result": {
                    "status": "blocked",
                    "failure_class": live_payload["failure_class"],
                    "execution_backend": "single_agent_role_protocol_v1",
                    "output": {
                        **output,
                        "role_output_path": output_path.as_posix(),
                        "role_output_markdown_path": markdown_path.as_posix(),
                    },
                },
                "pipeline_status": "blocked",
                "stop_reason": live_payload["failure_class"],
                "shared_outputs": {
                    "last_role_output": output,
                    f"role_output:{role_id}": output,
                    "unified_brief": brief_manifest,
                },
            }
    output_path = role_dir / "role_output.json"
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path = role_dir / "role_output.md"
    markdown_path.write_text(_render_role_output_markdown(output), encoding="utf-8")
    return {
        "handled": True,
        "result": {
            "status": "completed",
            "failure_class": None,
            "execution_backend": "single_agent_role_protocol_v1",
            "output": {
                **output,
                "role_output_path": output_path.as_posix(),
                "role_output_markdown_path": markdown_path.as_posix(),
            },
        },
        "shared_outputs": {
            "last_role_output": output,
            f"role_output:{role_id}": output,
            "unified_brief": brief_manifest,
        },
    }


def _call_live_role_llm(
    *,
    role_id: str,
    stage: PipelineStage,
    structured_output: dict[str, Any],
    brief_manifest: dict[str, Any],
) -> dict[str, Any]:
    from packages.runtime_langgraph.chat_runtime import ChatActionDecision, build_chat_llm_runtime_from_env

    runtime = build_chat_llm_runtime_from_env()
    description = runtime.describe()
    if not bool(description.get("configured")):
        return {
            "status": "blocked",
            "failure_class": "live_llm_provider_missing",
            "output_updates": {
                "llm_call_status": "blocked",
                "generation_mode": "live_llm_required_but_unconfigured",
                "llm_provider_evidence": description,
            },
        }
    prompt = (
        "你是 workflow 的单角色 agent。请基于已有结构化草案，给出简短审阅和补充，不要写代码。\n"
        "硬约束：你只能补充 derived_review_notes；不得删除、合并、改名、改写任何 preserved source requirement。\n"
        f"role_id: {role_id}\n"
        f"stage: {stage.name}\n"
        f"goal: {stage.goal}\n"
        f"brief_manifest: {json.dumps(_compact_manifest(brief_manifest), ensure_ascii=False)}\n"
        f"structured_draft: {json.dumps(structured_output, ensure_ascii=False)[:6000]}\n"
    )
    timeout_seconds = _live_role_timeout_seconds()
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        lambda: list(
            runtime.stream_reply(
                content=prompt,
                context={"role_id": role_id, "stage_id": stage.stage_id},
                decision=ChatActionDecision(action_type="answer_only", confidence=0.8),
            )
        )
    )
    try:
        chunks = future.result(timeout=timeout_seconds)
    except TimeoutError:
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        return {
            "status": "blocked",
            "failure_class": "live_llm_call_timeout",
            "output_updates": {
                "llm_call_status": "blocked",
                "generation_mode": "live_llm_call_timeout",
                "llm_provider_evidence": description,
                "llm_timeout_seconds": timeout_seconds,
            },
        }
    except Exception as exc:
        executor.shutdown(wait=False, cancel_futures=True)
        return {
            "status": "blocked",
            "failure_class": "live_llm_call_failed",
            "output_updates": {
                "llm_call_status": "failed",
                "generation_mode": "live_llm_call_failed",
                "llm_provider_evidence": description,
                "llm_failure": f"{type(exc).__name__}: {exc}",
            },
        }
    executor.shutdown(wait=False, cancel_futures=True)
    return {
        "status": "completed",
        "failure_class": None,
        "output_updates": {
            "llm_call_status": "called",
            "generation_mode": "live_llm_augmented_role_builder",
            "live_llm_contract": "derived_review_notes_only",
            "llm_provider_evidence": description,
            "derived_review_notes": [
                {
                    "source": "live_llm",
                    "role_id": role_id,
                    "text": "".join(chunks)[:4000],
                }
            ],
        },
    }


def _live_role_timeout_seconds() -> float:
    try:
        return max(1.0, float(os.getenv("WORKFLOW_LIVE_ROLE_TIMEOUT_SECONDS") or "60"))
    except ValueError:
        return 60.0


def _resolve_or_build_brief(
    *,
    stage: PipelineStage,
    role_dir: Path,
    source_path: str | Path | None,
    unified_brief_dir: str | Path | None,
) -> dict[str, Any]:
    if unified_brief_dir is not None:
        manifest_path = Path(unified_brief_dir).resolve() / "normalized" / "intake_manifest.json"
        if manifest_path.exists():
            return json.loads(manifest_path.read_text(encoding="utf-8"))
    if source_path is not None and Path(source_path).exists():
        return build_unified_project_brief(
            input_paths=[Path(source_path)],
            output_dir=role_dir / "unified_brief",
            title=stage.goal,
        )
    synthetic = role_dir / "unified_brief" / "synthetic_goal.md"
    synthetic.parent.mkdir(parents=True, exist_ok=True)
    synthetic.write_text(f"# Pipeline Goal\n\n{stage.goal}\n", encoding="utf-8")
    manifest = build_unified_project_brief(
        input_paths=[synthetic],
        output_dir=role_dir / "unified_brief",
        title=stage.name,
    )
    manifest["source_material_status"] = "synthetic_goal_only"
    return manifest


def _build_role_output(
    *,
    stage: PipelineStage,
    role_id: str,
    role_dir: Path,
    brief_manifest: dict[str, Any],
    shared_outputs: dict[str, Any],
    db_path: str | Path | None,
    pipeline_id: str | None,
    pipeline_goal: str | None,
    pipeline_template: str | None,
    pipeline_name: str | None,
) -> dict[str, Any]:
    packet_path = _packet_path_for_role(role_id, brief_manifest)
    packet_preview = _read_preview(packet_path)
    structured_output = _structured_output_for_role(
        role_id=role_id,
        stage=stage,
        brief_manifest=brief_manifest,
        shared_outputs=shared_outputs,
        packet_preview=packet_preview,
        pipeline_id=pipeline_id,
        pipeline_goal=pipeline_goal,
        pipeline_template=pipeline_template,
    )
    preservation_contract = _build_requirement_preservation_contract(
        role_id=role_id,
        structured_output=structured_output,
        brief_manifest=brief_manifest,
    )
    structured_output.update(
        {
            "source_material_policy": SOURCE_MATERIAL_POLICY,
            "input_requirement_ids": preservation_contract["input_requirement_ids"],
            "preserved_requirement_ids": preservation_contract["preserved_requirement_ids"],
            "preserved_requirements": preservation_contract["preserved_requirements"],
            "derived_requirements": preservation_contract["derived_requirements"],
            "omitted_requirement_ids": preservation_contract["omitted_requirement_ids"],
            "preservation_go": preservation_contract["preservation_go"],
            "preservation_blockers": preservation_contract["blockers"],
        }
    )
    task_card_persistence: dict[str, Any] | None = None
    if role_id == "task_card_generation_agent" and db_path is not None:
        task_card_persistence = _persist_task_card_candidates(
            candidates=structured_output.get("task_card_candidates", []),
            db_path=Path(db_path),
            target_dir=role_dir,
            pipeline_id=pipeline_id or stage.stage_id,
            pipeline_goal=pipeline_goal or stage.goal,
            pipeline_template=pipeline_template,
            pipeline_name=pipeline_name,
        )
        structured_output["task_card_persistence"] = task_card_persistence
    return {
        "schema_version": "post_m109_single_agent_role_output_v2",
        "created_at": datetime.now(UTC).isoformat(),
        "stage_id": stage.stage_id,
        "stage_name": stage.name,
        "role_id": role_id,
        "role_kind": stage.metadata.get("role_kind") or "single_agent",
        "model_profile": ROLE_MODEL_PROFILES.get(role_id, ROLE_MODEL_PROFILES["intake_packaging_agent"]),
        "llm_call_status": "not_called_by_default",
        "generation_mode": "deterministic_offline_role_builder",
        "llm_call_policy": "default execution builds structured role evidence without a live LLM call; live LLM routing must be explicitly enabled and proven by provider evidence in a later phase",
        "input_brief_manifest": brief_manifest,
        "shared_output_keys": sorted(shared_outputs.keys()),
        "agent_packet_path": packet_path,
        "packet_preview": packet_preview,
        "source_material_policy": SOURCE_MATERIAL_POLICY,
        "input_requirement_ids": preservation_contract["input_requirement_ids"],
        "preserved_requirement_ids": preservation_contract["preserved_requirement_ids"],
        "derived_requirements": preservation_contract["derived_requirements"],
        "omitted_requirement_ids": preservation_contract["omitted_requirement_ids"],
        "preservation_go": preservation_contract["preservation_go"],
        "preservation_contract": preservation_contract,
        "structured_output": structured_output,
        "deliverables": _deliverables_for_role(role_id),
        "evidence_requirements": [
            "role_output_json",
            "role_output_markdown",
            "input_brief_manifest",
            "agent_packet_path",
            "source_requirement_preservation_contract",
        ],
        "blocking_conditions": [
            "missing_unified_brief",
            "agent_packet_unreadable",
            "provider_policy_disallows_live_llm_when_required",
            "source_requirement_omitted",
        ],
        "next_handoff": _next_handoff_for_role(role_id),
        "artifact_root": role_dir.as_posix(),
    }


def _structured_output_for_role(
    *,
    role_id: str,
    stage: PipelineStage,
    brief_manifest: dict[str, Any],
    shared_outputs: dict[str, Any],
    packet_preview: str,
    pipeline_id: str | None,
    pipeline_goal: str | None,
    pipeline_template: str | None,
) -> dict[str, Any]:
    brief_text = _read_brief_text(brief_manifest, limit=8_000)
    source_requirements = _load_requirement_entries(brief_manifest)
    source_counts = {
        "source_count": int(brief_manifest.get("source_count") or 0),
        "chunk_count": int(brief_manifest.get("chunk_count") or 0),
        "media_count": int(brief_manifest.get("media_count") or 0),
        "requirement_count": len(source_requirements),
    }
    context = {
        "pipeline_id": pipeline_id,
        "pipeline_goal": pipeline_goal or stage.goal,
        "pipeline_template": pipeline_template or stage.metadata.get("template"),
        "brief_policy": "source_preserving_unified_brief",
        "requirement_matrix_path": brief_manifest.get("requirement_matrix_path"),
        "requirement_coverage_policy": "implementation_task_cards_must_carry_source_req_id_coverage",
        **source_counts,
    }
    if role_id == "intake_packaging_agent":
        return {
            "context": context,
            "normalized_materials": {
                "project_brief_path": brief_manifest.get("project_brief_path"),
                "source_index_path": brief_manifest.get("source_index_path"),
                "media_manifest_path": brief_manifest.get("media_manifest_path"),
                "requirement_matrix_path": brief_manifest.get("requirement_matrix_path"),
                "agent_packets": brief_manifest.get("agent_packets", {}),
            },
            "source_requirement_ids": _requirement_ids(source_requirements),
            "handoff_contract": "Downstream roles should cite the unified brief path and packet path instead of asking for raw scattered inputs.",
        }
    if role_id == "product_gameplay_agent":
        return {
            "context": context,
            "gameplay_goals": [
                "Player can understand the objective within the first screen.",
                "Each level has a visible target, progress signal, and fail or success feedback.",
                "Prototype claims must stay separate from commercial playable claims.",
            ],
            "core_loop": ["read goal", "make move", "receive feedback", "earn progress", "unlock next target"],
            "progression_model": {
                "level_unlock": "sequential_unlock_with_visible_next_goal",
                "session_target": "short_mobile_session",
                "retention_hook": "skin_or_gallery_unlock_after_clear_conditions",
            },
            "acceptance_outline": [
                "At least one playable loop is visible from the player perspective.",
                "Level target, progress, and reward are inspectable in evidence.",
                "Commercial readiness is blocked unless UI, audio, assets, and playtest evidence pass.",
            ],
            "source_requirement_ids": _role_requirement_ids("product_gameplay_agent", source_requirements),
            "brief_signal": _brief_signal(brief_text, packet_preview),
        }
    if role_id == "mechanics_system_designer_agent":
        return {
            "context": context,
            "mechanic_contract": {
                "core_verbs": ["brief_defined_primary_move", "evaluate_move", "resolve_feedback", "advance_or_fail"],
                "state_invariants": [
                    "the runtime state, not a browser-only hook, decides valid moves and progress",
                    "every fail, revive, reward, and unlock transition emits semantic evidence",
                    "invalid input must produce visible feedback without corrupting saved progress",
                ],
                "edge_case_policy": [
                    "prevent soft-lock or no-move board states when the source game rules imply continuous play",
                    "make retry and recovery states explicit instead of relying on page reload",
                    "tie score, combo, or clear feedback to actual state transitions",
                ],
            },
            "feel_requirements": [
                "input response must be immediate and visually legible",
                "success and failure feedback must be readable without opening debug panels",
                "core loop replay evidence must show at least one win path and one invalid-action path",
            ],
            "handoff_to_level_economy": [
                "Expose tunable rule parameters that level pacing can vary safely.",
                "Mark mechanics that need level-specific tutorials or early-session constraints.",
            ],
            "source_requirement_ids": _role_requirement_ids("mechanics_system_designer_agent", source_requirements),
            "brief_signal": _brief_signal(brief_text, packet_preview),
        }
    if role_id == "level_economy_designer_agent":
        return {
            "context": context,
            "level_progression_plan": {
                "minimum_distinct_goals": 8,
                "difficulty_curve": ["teach_one_rule", "combine_two_constraints", "introduce_pressure", "reward_mastery"],
                "goal_evidence": "level_goal_matrix plus scripted progression replay",
            },
            "economy_balance_plan": {
                "sources": ["clear_reward", "daily_or_session_bonus", "achievement_or_gallery_unlock"],
                "sinks": ["skin_unlock", "revive_or_hint_cost", "gallery_completion_reward"],
                "anti_stall": "reward pacing must encourage replay without blocking first-session progress",
            },
            "content_depth_checks": [
                "each level objective is visible in HUD and result screens",
                "rewards, skins, gallery, or collection states have locked, affordable, owned, and equipped variants",
                "save/load evidence proves progression persistence",
            ],
            "source_requirement_ids": _role_requirement_ids("level_economy_designer_agent", source_requirements),
        }
    if role_id == "ui_experience_agent":
        return {
            "context": context,
            "screen_flow": ["loading", "main_menu", "gameplay", "pause", "result", "gallery_or_skin"],
            "panel_requirements": [
                "Every visible panel must have a clear title, primary action, and close or back path.",
                "HUD must expose target, score or progress, and current level state.",
                "Mobile layout must keep buttons thumb-reachable without covering the play area.",
            ],
            "feedback_requirements": ["tap feedback", "success animation", "failure hint", "audio volume control"],
            "mobile_ux_constraints": {
                "minimum_touch_target_px": 44,
                "safe_area_required": True,
                "no_text_overlap": True,
            },
            "source_requirement_ids": _role_requirement_ids("ui_experience_agent", source_requirements),
        }
    if role_id == "ui_ux_polish_agent":
        return {
            "context": context,
            "commercial_ui_polish_rubric": {
                "first_session": ["clear objective", "obvious primary action", "no debug-looking labels"],
                "hud": ["target", "progress", "score_or_moves", "level", "audio/settings access"],
                "panels": ["shop", "gallery", "settings", "pause", "result", "failure_revive"],
                "layout": ["safe_area", "thumb_reach", "text_fit", "playfield_not_obscured"],
            },
            "visual_hierarchy_rules": [
                "primary playfield stays dominant during gameplay",
                "secondary panels are dismissible and never block normal input by accident",
                "Chinese copy must be readable, localized, and free of mojibake",
            ],
            "evidence_expectations": [
                "desktop and mobile screenshots from normal gameplay and at least two open panels",
                "layout overlap report",
                "open panel trace from browser playtest bridge",
            ],
            "source_requirement_ids": _role_requirement_ids("ui_ux_polish_agent", source_requirements),
        }
    if role_id == "art_direction_agent":
        return {
            "context": context,
            "asset_style_bible": {
                "visual_target": "polished casual mobile puzzle, coherent theme, readable board materials",
                "asset_families": ["board_cells", "pieces_or_tiles", "buttons", "panel_frames", "reward_gallery", "icons"],
                "non_placeholder_definition": [
                    "asset files or manifests are tied to source requirements",
                    "palette, material, and icon language are consistent across HUD, shop, gallery, and results",
                    "generated or imported assets include provenance and usage bindings",
                ],
            },
            "art_review_gates": [
                "vision review must inspect screenshots, not only manifest text",
                "asset names and player-facing labels must be localized and readable",
                "style drift between gameplay board and panels is a repair finding",
            ],
            "source_requirement_ids": _role_requirement_ids("art_direction_agent", source_requirements),
        }
    if role_id == "animation_vfx_feedback_agent":
        return {
            "context": context,
            "motion_feedback_plan": {
                "core_events": ["valid_move", "invalid_move", "clear_success", "combo_or_streak", "reward_unlock", "fail_or_revive"],
                "timing_budget_ms": {"tap_feedback": 120, "clear_resolution": 650, "panel_transition": 280},
                "accessibility": ["reduced_motion_safe", "feedback_not_color_only"],
            },
            "vfx_quality_checks": [
                "effects reinforce state transitions instead of playing as detached decoration",
                "success/failure animations are visible in screenshot or replay evidence",
                "animation does not obscure the board target or active input zone",
            ],
            "source_requirement_ids": _role_requirement_ids("animation_vfx_feedback_agent", source_requirements),
        }
    if role_id == "audio_feedback_designer_agent":
        return {
            "context": context,
            "audio_design_sheet": {
                "bgm": ["short_loop", "non_jarring_start", "pause_or_mute_respect"],
                "sfx_events": ["tap", "valid_move", "invalid_move", "clear", "reward", "fail", "panel_open"],
                "mix_rules": ["sfx_ducking_over_bgm", "volume_toggle", "mute_state_persists"],
            },
            "runtime_audio_evidence": [
                "audio asset manifest references generated or deterministic audio files",
                "browser playtest proves BGM started, SFX triggered, and volume toggle is usable",
                "audio errors or autoplay failures are blockers in unattended mode",
            ],
            "source_requirement_ids": _role_requirement_ids("audio_feedback_designer_agent", source_requirements),
        }
    if role_id == "technical_plan_agent":
        return {
            "context": context,
            "implementation_plan": [
                "Keep workflow orchestration code separate from Cocos contribution code.",
                "Use pipeline evidence directories for generated role outputs and gate results.",
                "Treat Cocos Creator execution as a capability stage with honest missing-input blockers.",
            ],
            "write_set_boundaries": [
                "packages/core_domain/* for generic workflow runtime behavior",
                "packages/contributions/pipelines/* for M109 pipeline templates",
                "packages/contributions/games/cocos/* for Cocos-specific validators only",
                "state/pipeline_runs or caller-provided output directories for generated evidence",
            ],
            "test_plan": [
                "python -m pytest tests/test_m109_unified_brief.py -q",
                "python -m pytest tests/test_pipeline_and_automation_cli.py -q",
                "python -m apps.operator_cli.main pipeline truth-report --template commercial_game_production",
            ],
            "risk_register": [
                "Do not claim commercial playable readiness without Cocos build and player-visible evidence.",
                "Do not route around receipt, lease, write_set, or evidence rules.",
            ],
            "source_requirement_ids": _role_requirement_ids("technical_plan_agent", source_requirements),
        }
    if role_id == "multimodal_generation_agent":
        route_plan = build_multimodal_route_plan()
        return {
            "context": context,
            "asset_manifest_requirements": [
                "ui_theme_reference",
                "gameplay_tiles_or_blocks",
                "panel_backgrounds",
                "button_states",
                "success_failure_sfx",
                "short_loop_music",
            ],
            "provider_route_requirements": [
                {
                    "asset_type": "image_or_sprite",
                    "preferred_route": "MMX/MiniMax API when credentials are available",
                    "fallback": "human-provided assets or deterministic placeholder manifest",
                    "evidence": "provider-specific live proof is required before verified_ready",
                },
                {
                    "asset_type": "tts_or_voice",
                    "preferred_route": "GCP/Vertex-family voice route when configured",
                    "fallback": "no-voice mode with explicit blocker",
                    "evidence": "audio file plus provenance manifest",
                },
                {
                    "asset_type": "visual_review",
                    "preferred_route": "Vertex/Gemini-family visual review when configured",
                    "fallback": "rule-based screenshot checklist",
                    "evidence": "screenshot references and review verdict",
                },
            ],
            "route_plan": route_plan,
            "generation_policy": "Planning can run offline; actual media generation must use a live provider or be marked as placeholder.",
            "source_requirement_ids": _role_requirement_ids("multimodal_generation_agent", source_requirements),
        }
    if role_id == "ai_playtest_oracle_agent":
        return {
            "context": context,
            "playtest_modes": [
                "scripted_core_loop",
                "exploratory_ui_panel_walk",
                "first_session_persona",
                "visual_screenshot_review",
                "audio_feedback_review",
                "regression_replay",
                "device_matrix_smoke",
            ],
            "quality_rubric": {
                "target_score": 88,
                "visual_minimum": 85,
                "audio_minimum": 80,
                "core_loop_minimum": 90,
                "p0_allowed": 0,
                "p1_allowed": 0,
            },
            "repair_loop_triggers": [
                "score_below_target",
                "missing_required_playtest_mode",
                "screenshot_density_below_reference",
                "audio_runtime_error",
                "open_panel_trace_missing",
                "source_requirement_fidelity_not_proven",
            ],
            "source_requirement_ids": _role_requirement_ids("ai_playtest_oracle_agent", source_requirements),
        }
    if role_id == "task_card_generation_agent":
        game_design_spec = _game_design_spec_from_brief_manifest(brief_manifest)
        return {
            "context": context,
            "specialist_role_handoff": _specialist_role_handoff_summary(shared_outputs),
            "product_phase_candidates": [
                candidate.to_dict()
                for candidate in build_product_phase_candidates_from_design_spec(
                    run_id=_safe_id(pipeline_id or stage.stage_id),
                    spec=game_design_spec,
                )
            ],
            "stage_internal_phase_graph": _stage_internal_phase_graph(
                pipeline_id or stage.stage_id,
                pipeline_goal=pipeline_goal or stage.goal,
                brief_manifest=brief_manifest,
                pipeline_template=pipeline_template or str(stage.metadata.get("pipeline_recipe") or ""),
            ),
            "task_card_candidates": _task_card_candidate_payloads(
                pipeline_id=pipeline_id or stage.stage_id,
                pipeline_goal=pipeline_goal or stage.goal,
                pipeline_template=pipeline_template or str(stage.metadata.get("pipeline_recipe") or "commercial_game_production"),
                brief_manifest=brief_manifest,
            ),
            "quality_gate": {
                "authority_source": "sqlite_task_cards_table",
                "markdown_role": "human_snapshot_only",
                "requirement_coverage_required_for_implementation": True,
                "minimum_fields": [
                    "goal",
                    "read_set",
                    "write_set",
                    "test_commands",
                    "acceptance_criteria",
                    "evidence_requirements",
                    "blocking_conditions",
                    "risk_level",
                    "model_guidance",
                    "expected_artifacts",
                ],
            },
        }
    if role_id == "qa_player_perspective_agent":
        qa_from_evidence = _qa_output_from_cocos_e2e(shared_outputs=shared_outputs, context=context)
        if qa_from_evidence is not None:
            return qa_from_evidence
        return {
            "context": context,
            "player_visible_checks": [
                {"check": "first_screen_understandable", "status": "pending_until_playtest_evidence"},
                {"check": "level_goal_visible", "status": "pending_until_playtest_evidence"},
                {"check": "interactive_panels_usable", "status": "pending_until_playtest_evidence"},
                {"check": "audio_not_jarring", "status": "pending_until_audio_evidence"},
                {"check": "commercial_claim_supported", "status": "blocked_without_build_and_playtest"},
            ],
            "red_team_policy": "default_to_disproof_until_player_visible_runtime_evidence_passes",
            "blocking_findings": [
                {"finding": "build_and_playtest_evidence_missing", "status": "blocked"},
                {"finding": "runtime_semantic_trace_not_reviewed", "status": "blocked"},
                {"finding": "component_binding_evidence_not_reviewed", "status": "blocked"},
            ],
            "repair_findings": [
                {"finding": "build_and_playtest_evidence_missing", "status": "blocked"},
            ],
            "go_no_go_recommendation": "NO-GO until Cocos build/playtest evidence exists",
        }
    if role_id == "commercial_quality_score_agent":
        production = shared_outputs.get("commercial_game_production")
        production_payload = dict(production) if isinstance(production, dict) else {}
        browser_playtest_ledger = production_payload.get("browser_playtest_ledger")
        scorecard = evaluate_commercial_quality_scorecard(
            production_payload.get("commercial_quality_scorecard")
            if isinstance(production_payload.get("commercial_quality_scorecard"), dict)
            else None,
            playtest=production_payload.get("playtest") if isinstance(production_payload.get("playtest"), dict) else None,
            browser_playtest_ledger=browser_playtest_ledger if isinstance(browser_playtest_ledger, dict) else None,
            reference_quality_evidence=production_payload.get("reference_quality_evidence")
            if isinstance(production_payload.get("reference_quality_evidence"), dict)
            else None,
            ai_surrogate_playtest_evidence=production_payload.get("ai_surrogate_playtest_evidence")
            if isinstance(production_payload.get("ai_surrogate_playtest_evidence"), dict)
            else None,
            product_depth_evidence=production_payload.get("product_depth_evidence")
            if isinstance(production_payload.get("product_depth_evidence"), dict)
            else None,
            product_body_evidence=production_payload.get("product_body_evidence")
            if isinstance(production_payload.get("product_body_evidence"), dict)
            else None,
        )
        return {
            "context": context,
            "scorecard_schema": "commercial_game_quality_scorecard_v1",
            "commercial_quality_scorecard": scorecard,
            "quality_areas": scorecard["area_scores"],
            "hard_blockers": scorecard["hard_blockers"],
            "repair_findings": scorecard["repair_task_card_suggestions"],
            "go_no_go_recommendation": "GO" if scorecard["go"] else "NO-GO",
            "policy": {
                "bridge_or_overlay_can_score_product_body": False,
                "real_pointer_drag_required": True,
                "portrait_mobile_required": True,
                "r5_reference_is_no_regression_input_only": True,
            },
        }
    if role_id == "supervisor":
        return {
            "context": context,
            "decision": "force_no_go_until_red_team_and_machine_contracts_pass",
            "repair_or_stop_rules": [
                "Repair workflow/runtime bugs before business feature expansion.",
                "Stop commercial-ready claims when evidence is prototype-only.",
                "Upgrade a role to cluster only after repeated single-agent failure evidence.",
            ],
            "force_no_go_rules": [
                "source requirement omission",
                "missing human_visible_cli_enforced metadata for high-risk commercial cards",
                "baseline-only product body",
                "runtime hook, canvas-only, event-only, or feature-flag-only product evidence",
                "missing fresh receipt, child run, child attempt, changed files, or passing tests",
                "missing explicit human acceptance",
            ],
            "cluster_upgrade_recommendation": {
                "default": "keep_specialized_single_agent_roles",
                "upgrade_candidates": [
                    "art_direction_agent",
                    "animation_vfx_feedback_agent",
                    "audio_feedback_designer_agent",
                    "ai_playtest_oracle_agent",
                    "qa_player_perspective_agent",
                    "commercial_quality_score_agent",
                ],
                "trigger": "upgrade only if a specialized role repeatedly fails despite clear task cards and evidence",
            },
        }
    return {"context": context, "role_note": "No specialized structured output registered for this role."}


def _specialist_role_handoff_summary(shared_outputs: dict[str, Any]) -> dict[str, Any]:
    role_ids = [
        "product_gameplay_agent",
        "mechanics_system_designer_agent",
        "level_economy_designer_agent",
        "ui_experience_agent",
        "ui_ux_polish_agent",
        "art_direction_agent",
        "animation_vfx_feedback_agent",
        "audio_feedback_designer_agent",
        "technical_plan_agent",
        "multimodal_generation_agent",
        "ai_playtest_oracle_agent",
    ]
    roles: list[dict[str, Any]] = []
    for role_id in role_ids:
        output = shared_outputs.get(f"role_output:{role_id}")
        if not isinstance(output, dict):
            roles.append({"role_id": role_id, "status": "missing"})
            continue
        structured = output.get("structured_output") if isinstance(output.get("structured_output"), dict) else {}
        roles.append(
            {
                "role_id": role_id,
                "status": "present",
                "preservation_go": bool(output.get("preservation_go")),
                "deliverables": list(output.get("deliverables") or []),
                "structured_keys": sorted(structured.keys()),
                "source_requirement_count": len(output.get("preserved_requirement_ids") or []),
            }
        )
    return {
        "schema_version": "commercial_game_specialist_role_handoff_v1",
        "role_count": len(roles),
        "present_role_count": sum(1 for item in roles if item["status"] == "present"),
        "roles": roles,
    }


def _qa_output_from_cocos_e2e(*, shared_outputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any] | None:
    payload = shared_outputs.get("cocos_e2e")
    if not isinstance(payload, dict):
        return None
    readiness = payload.get("commercial_readiness")
    if not isinstance(readiness, dict):
        manifest = payload.get("manifest") if isinstance(payload.get("manifest"), dict) else {}
        metadata = manifest.get("metadata") if isinstance(manifest.get("metadata"), dict) else {}
        readiness = metadata.get("commercial_readiness") if isinstance(metadata.get("commercial_readiness"), dict) else {}
    player_checks = payload.get("player_visible_checks")
    if not isinstance(player_checks, dict):
        player_checks = readiness.get("player_visible_checks") if isinstance(readiness.get("player_visible_checks"), dict) else {}
    normalized_checks: list[dict[str, Any]] = []
    repair_findings: list[dict[str, Any]] = []
    for key, value in player_checks.items():
        if isinstance(value, dict):
            status = str(value.get("status") or "unknown")
            evidence_path = value.get("evidence_path")
        else:
            status = "pass" if bool(value) else "fail"
            evidence_path = None
        item = {"check": key, "status": status}
        if evidence_path:
            item["evidence_path"] = evidence_path
        normalized_checks.append(item)
        if status != "pass":
            repair_findings.append({"finding": f"{key} did not pass", "status": status})
    blockers = payload.get("commercial_playable_blockers")
    if not isinstance(blockers, list):
        blockers = readiness.get("commercial_playable_blockers") if isinstance(readiness.get("commercial_playable_blockers"), list) else []
    for blocker in blockers:
        repair_findings.append({"finding": str(blocker), "status": "blocked"})
    red_team_findings = list(repair_findings)
    playtest = payload.get("playtest") if isinstance(payload.get("playtest"), dict) else {}
    commercial_playable_go = bool(payload.get("commercial_playable_go") or readiness.get("commercial_playable_go"))
    if not commercial_playable_go:
        red_team_findings.append({"finding": "commercial_playable_go_not_supported", "status": "blocked"})
    return {
        "context": context,
        "evidence_source": "shared_outputs.cocos_e2e",
        "red_team_policy": "default_to_disproof",
        "player_visible_checks": normalized_checks,
        "blocking_findings": red_team_findings,
        "repair_findings": repair_findings,
        "go_no_go_recommendation": "GO" if commercial_playable_go and not repair_findings else "NO-GO",
        "commercial_playable_go": commercial_playable_go,
        "commercial_playable_blockers": blockers,
        "console_errors": list(playtest.get("console_errors") or []),
        "page_errors": list(playtest.get("page_errors") or []),
        "screenshots": list(playtest.get("screenshots") or []),
        "manifest_path": payload.get("manifest_path"),
    }


def _compact_manifest(brief_manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": brief_manifest.get("schema_version"),
        "project_brief_path": brief_manifest.get("project_brief_path"),
        "source_count": brief_manifest.get("source_count"),
        "chunk_count": brief_manifest.get("chunk_count"),
        "media_count": brief_manifest.get("media_count"),
        "agent_packets": brief_manifest.get("agent_packets"),
    }


def _read_brief_text(brief_manifest: dict[str, Any], *, limit: int) -> str:
    path_value = brief_manifest.get("project_brief_path")
    if not path_value:
        return ""
    path = Path(path_value)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:limit]


def _brief_signal(brief_text: str, packet_preview: str) -> dict[str, bool]:
    combined = f"{brief_text}\n{packet_preview}".lower()
    return {
        "mentions_ui": "ui" in combined or "界面" in combined,
        "mentions_audio": "audio" in combined or "音频" in combined or "music" in combined,
        "mentions_level": "level" in combined or "关卡" in combined,
        "mentions_asset": "asset" in combined or "资源" in combined,
    }


def _load_requirement_entries(brief_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    payload = _load_requirement_matrix_payload(brief_manifest)
    requirements = payload.get("requirements")
    if not isinstance(requirements, list):
        return []
    return [item for item in requirements if isinstance(item, dict) and item.get("req_id")]


def _load_requirement_matrix_payload(brief_manifest: dict[str, Any]) -> dict[str, Any]:
    path_value = brief_manifest.get("requirement_matrix_path")
    if not path_value:
        return {}
    path = Path(path_value)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_source_index_entries(brief_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    path_value = brief_manifest.get("source_index_path")
    if not path_value:
        return []
    path = Path(path_value)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def _requirement_ids(requirements: list[dict[str, Any]]) -> list[str]:
    return [str(item["req_id"]) for item in requirements if item.get("req_id")]


def _role_requirement_ids(role_id: str, requirements: list[dict[str, Any]]) -> list[str]:
    if role_id in {"intake_packaging_agent", "task_card_generation_agent", "supervisor"}:
        return _requirement_ids(requirements)
    category_hints = {
        "mechanics_system_designer_agent": {"product", "general"},
        "level_economy_designer_agent": {"product", "general"},
        "ui_ux_polish_agent": {"ui", "qa"},
        "art_direction_agent": {"multimodal", "ui"},
        "animation_vfx_feedback_agent": {"multimodal", "ui", "product"},
        "audio_feedback_designer_agent": {"multimodal"},
        "ai_playtest_oracle_agent": {"qa", "product", "ui", "technical"},
        "commercial_quality_score_agent": {"qa", "product", "ui", "technical"},
    }.get(role_id)
    if category_hints:
        selected = [item for item in requirements if str(item.get("category") or "") in category_hints]
        if not selected and requirements:
            selected = [item for item in requirements if str(item.get("priority") or "") == "high"]
        return _requirement_ids(selected or requirements)
    selected = [item for item in requirements if item.get("downstream_owner") == role_id]
    return _requirement_ids(selected)


def _build_requirement_preservation_contract(
    *,
    role_id: str,
    structured_output: dict[str, Any],
    brief_manifest: dict[str, Any],
) -> dict[str, Any]:
    requirements = _load_requirement_entries(brief_manifest)
    input_ids = _role_requirement_ids(role_id, requirements)
    declared_ids = _strings_from(structured_output.get("source_requirement_ids"))
    preserved_ids = declared_ids or input_ids
    if role_id in {"intake_packaging_agent", "task_card_generation_agent", "supervisor"}:
        preserved_ids = input_ids
    preserved_ids = _dedupe_strings([req_id for req_id in preserved_ids if req_id in set(input_ids)])
    omitted_ids = [req_id for req_id in input_ids if req_id not in set(preserved_ids)]
    requirement_by_id = {str(item.get("req_id")): item for item in requirements if item.get("req_id")}
    derived = structured_output.get("derived_requirements")
    if not isinstance(derived, list):
        derived = []
    blockers = ["source_requirement_omitted"] if omitted_ids else []
    return {
        "schema_version": "post_m109_source_requirement_preservation_v1",
        "source_material_policy": SOURCE_MATERIAL_POLICY,
        "role_id": role_id,
        "input_requirement_ids": input_ids,
        "preserved_requirement_ids": preserved_ids,
        "preserved_requirements": [requirement_by_id[req_id] for req_id in preserved_ids if req_id in requirement_by_id],
        "derived_requirements": derived,
        "omitted_requirement_ids": omitted_ids,
        "preservation_go": not omitted_ids,
        "blockers": blockers,
    }


def _strings_from(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _task_card_candidate_payloads(
    *,
    pipeline_id: str,
    pipeline_goal: str,
    pipeline_template: str,
    brief_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    base = _safe_id(pipeline_id)
    if _is_universal_game_quality_phase(pipeline_goal):
        return _universal_game_quality_task_card_candidates(
            base=base,
            pipeline_goal=pipeline_goal,
            brief_manifest=brief_manifest,
        )
    if _is_product_body_runtime_phase(pipeline_goal):
        return _product_body_runtime_task_card_candidates(base=base, pipeline_goal=pipeline_goal, brief_manifest=brief_manifest)
    if _is_commercial_core_content_phase(pipeline_goal):
        return _commercial_core_content_task_card_candidates(base=base, pipeline_goal=pipeline_goal, brief_manifest=brief_manifest)
    if _is_commercial_machine_evidence_phase(pipeline_goal):
        return _commercial_machine_evidence_task_card_candidates(base=base, pipeline_goal=pipeline_goal, brief_manifest=brief_manifest)
    if _is_commercial_asset_browser_runtime_phase(pipeline_goal):
        return _commercial_asset_browser_runtime_task_card_candidates(
            base=base,
            pipeline_goal=pipeline_goal,
            brief_manifest=brief_manifest,
        )
    if _is_commercial_game_production_template(pipeline_template):
        return _commercial_core_content_task_card_candidates(
            base=base,
            pipeline_goal=pipeline_goal,
            brief_manifest=brief_manifest,
        )
    candidates = [
        {
            "task_card_id": f"{base}_m109_role_brief_contract",
            "title": "Verify unified brief and role handoff contract",
            "description": "Confirm that the pipeline has a source-preserving unified brief and that every role can read the packet intended for it before implementation work begins.",
            "goal": f"Use the unified brief as the shared source for {pipeline_goal} without lossy summary replacement.",
            "write_set": ["state/pipeline_runs"],
            "read_set": ["normalized/project_brief.full.md", "normalized/source_index.json", "agent_packets/*.md"],
            "acceptance_criteria": ["Unified brief path exists.", "Agent packet paths are present.", "No role is asked to consume missing raw scattered files."],
            "test_commands": ["python -m apps.operator_cli.main intake package --help"],
            "expected_artifacts": ["intake_manifest.json", "project_brief.full.md", "agent_packets"],
            "evidence_requirements": ["intake_manifest", "source_index", "agent_packet_paths"],
            "blocking_conditions": ["unified_brief_missing", "agent_packet_missing"],
            "model_guidance": ["Read the unified brief first.", "Use original paths for audit.", "Do not replace source material with a short summary."],
            "risk_level": "medium",
            "provider_lane": "configured_text_model",
            "execution_mode": "artifact_review",
        },
        {
            "task_card_id": f"{base}_m109_role_design_plan",
            "title": "Produce player-facing product UI and technical plan",
            "description": "Turn the unified brief into concrete gameplay, UI, and technical boundaries that a worker can implement without guessing the product shape.",
            "goal": "Create a product/UI/technical plan with visible player goals, screen flow, write-set boundaries, and test commands.",
            "write_set": ["state/pipeline_runs"],
            "read_set": ["role_output:product_gameplay_agent", "role_output:ui_experience_agent", "role_output:technical_plan_agent"],
            "acceptance_criteria": ["Gameplay loop is explicit.", "UI screen flow is explicit.", "Technical write-set boundaries are explicit."],
            "test_commands": ["python -m pytest tests/test_m109_unified_brief.py -q"],
            "expected_artifacts": ["product role_output.json", "ui role_output.json", "technical role_output.json"],
            "evidence_requirements": ["role_output_json", "structured_output", "test_output"],
            "blocking_conditions": ["generic_role_output", "missing_test_plan"],
            "model_guidance": ["Keep outputs implementable.", "Separate prototype evidence from commercial readiness claims."],
            "risk_level": "medium",
            "provider_lane": "codex_or_configured_strong_model",
            "execution_mode": "role_stage_execution",
        },
        {
            "task_card_id": f"{base}_m109_role_multimodal_route",
            "title": "Define multimodal asset route and honest blockers",
            "description": "Specify image, audio, music, and visual review routes for the Cocos trial while marking unavailable providers as blockers instead of fake readiness.",
            "goal": "Prepare a multimodal route table that can guide later asset generation without requiring unavailable APIs during default tests.",
            "write_set": ["state/pipeline_runs"],
            "read_set": ["role_output:multimodal_generation_agent", "provider capability readiness"],
            "acceptance_criteria": ["Image/sprite route is named.", "Audio/music route is named.", "Visual QA route is named.", "Provider live proof requirement is explicit."],
            "test_commands": ["python -m apps.operator_cli.main pipeline truth-report --template commercial_game_production"],
            "expected_artifacts": ["multimodal role_output.json"],
            "evidence_requirements": ["provider_route_requirements", "blocker_policy"],
            "blocking_conditions": ["provider_claim_without_live_proof", "missing_asset_manifest_requirements"],
            "model_guidance": ["Do not call unavailable APIs.", "Record placeholders as placeholders.", "Require provider-specific proof before verified_ready."],
            "risk_level": "medium",
            "provider_lane": "configured_text_model",
            "execution_mode": "route_planning",
        },
        {
            "task_card_id": f"{base}_m109_role_qa_supervisor_gate",
            "title": "Run QA and supervisor stop or repair decision",
            "description": "Evaluate player-visible evidence and decide whether to continue, repair, stop, or later upgrade a role to a cluster based on actual failure evidence.",
            "goal": "Keep the Cocos trial honest by preventing commercial-ready claims when player-visible build/playtest evidence is missing.",
            "write_set": ["state/pipeline_runs"],
            "read_set": ["role_output:qa_player_perspective_agent", "role_output:supervisor", "cocos_e2e manifest when available"],
            "acceptance_criteria": ["QA checks include player-visible status.", "Supervisor decision includes continue/repair/stop rules.", "Cluster upgrade is conditional, not automatic."],
            "test_commands": ["python -m pytest tests/test_m109_unified_brief.py -q"],
            "expected_artifacts": ["qa role_output.json", "supervisor role_output.json"],
            "evidence_requirements": ["qa_checks", "supervisor_decision", "go_no_go_recommendation"],
            "blocking_conditions": ["commercial_claim_without_playtest", "cluster_upgrade_without_failure_evidence"],
            "model_guidance": ["Prefer stop or repair over optimistic GO.", "Use simple evidence labels that a reviewer can understand."],
            "risk_level": "medium",
            "provider_lane": "codex_or_configured_strong_model",
            "execution_mode": "review_gate",
        },
        {
            "task_card_id": f"{base}_zero_degradation_gate_v2",
            "title": "Repair commercial final gate with no-degradation contract",
            "description": "Replace event-only commercial readiness with a no-degradation contract that blocks scaffold, missing ecosystem, missing live provider proof, missing same-project patch evidence, media runtime errors, and missing human player review.",
            "goal": "Ensure commercial_game_production cannot mark commercial_playable_go true unless all zero-degradation evidence is present.",
            "write_set": ["packages/contributions/games/cocos/no_degradation.py", "packages/contributions/pipelines/registry.py", "tests/test_pipeline_and_automation_cli.py"],
            "read_set": ["docs/development/commercial_game_workflow_next_development_2026_04_28.md", "state/pipeline_runs/*/cocos_project/player_visible_evidence"],
            "acceptance_criteria": ["Feature flags alone cannot pass commercial GO.", "NotSupportedError/audio runtime errors block GO.", "Missing human player review produces AWAITING_HUMAN_REVIEW, not GO."],
            "test_commands": ["python -m pytest tests/test_pipeline_and_automation_cli.py -q"],
            "expected_artifacts": ["no_degradation_contract", "negative_gate_test_output"],
            "evidence_requirements": ["failure_class", "degradation_findings", "recovery_suggestion"],
            "blocking_conditions": ["event_only_gate_passes", "commercial_go_without_human_review"],
            "model_guidance": ["Treat this as workflow gate repair.", "Do not patch game content to satisfy this card.", "Preserve old run artifacts as historical evidence."],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "workflow_infra_bugfix",
        },
        {
            "task_card_id": f"{base}_cocos_ecosystem_bridge_contract",
            "title": "Add Cocos ecosystem bridge contract and strict blocker evidence",
            "description": "Define the Cocos Editor/local MCP/AssetDB/Scene/Prefab/Build API evidence contract and block strict commercial GO when only CLI/filesystem/playtest evidence is available.",
            "goal": "Separate real Cocos ecosystem integration from CLI diagnostics so the pipeline cannot silently downgrade.",
            "write_set": ["packages/contributions/games/cocos/ecosystem_bridge.py", "packages/contributions/pipelines/commercial_game_production.py", "tests/test_cocos_e2e.py"],
            "read_set": ["Cocos Creator install path", "commercial_editor_structure_manifest.json", "cocos_build_stdout.log"],
            "acceptance_criteria": ["Missing bridge evidence returns cocos_ecosystem_bridge_missing.", "AssetDB/Scene/Prefab operations are individually represented.", "CLI/E2E evidence is not accepted as ecosystem integration."],
            "test_commands": ["python -m pytest tests/test_cocos_e2e.py -q"],
            "expected_artifacts": ["cocos_ecosystem_bridge_evidence.json"],
            "evidence_requirements": ["editor_version_or_missing", "assetdb_check", "scene_check", "prefab_check", "license_cost_manifest"],
            "blocking_conditions": ["filesystem_only_bridge_claim", "missing_assetdb_evidence"],
            "model_guidance": ["Implement the bridge as a workflow capability surface.", "Do not call filesystem scaffolding an Editor bridge."],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "capability_contract",
        },
        {
            "task_card_id": f"{base}_commercial_gameplay_levels",
            "title": "Implement eight distinct player-visible level goals",
            "description": "Replace numeric level toggles with at least eight distinct goals such as score, combo, limited moves, collection, and unlock targets on the same Cocos project.",
            "goal": "Make level progression real and visible instead of a feature flag or shallow counter.",
            "write_set": ["state/pipeline_runs/<run>/cocos_project/assets/scripts", "state/pipeline_runs/<run>/cocos_project/assets"],
            "read_set": ["role_output:product_gameplay_agent", "gameplay_interaction_contract.json"],
            "acceptance_criteria": ["Eight distinct goals are visible.", "At least one completion path is proven.", "Unlock state persists during the playtest session."],
            "test_commands": ["python -m pytest tests/test_cocos_e2e.py -q"],
            "expected_artifacts": ["level_manifest.json", "playtest_evidence"],
            "evidence_requirements": ["eightDistinctLevelGoals", "level_completion_screenshot", "repair_patch"],
            "blocking_conditions": ["campaignFirstSevenLevels_constant_only", "no_level_goal_manifest"],
            "model_guidance": ["Patch the same project.", "Do not regenerate a new template project.", "Keep Chinese UI visible."],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
        },
        {
            "task_card_id": f"{base}_commercial_shop_skin_collection",
            "title": "Implement shop skin collection ownership and equip flow",
            "description": "Make skins, backgrounds, and collection panels functional with owned/unowned state, currency cost, unlock, equip, and visible block/background changes.",
            "goal": "Turn the shop/skin/collection buttons into real player-facing systems.",
            "write_set": ["state/pipeline_runs/<run>/cocos_project/assets/scripts", "state/pipeline_runs/<run>/cocos_project/assets/resources"],
            "read_set": ["role_output:ui_experience_agent", "commercial_asset_bindings.json"],
            "acceptance_criteria": ["Owned/unowned state is visible.", "Equipped skin visibly changes blocks.", "Collection/gallery state is clickable and not label-only."],
            "test_commands": ["python -m pytest tests/test_cocos_e2e.py -q"],
            "expected_artifacts": ["shop_state_manifest.json", "skin_equipped_screenshot"],
            "evidence_requirements": ["shopOwnershipStates", "skinEquippedVisualChange", "collection_panel_screenshot"],
            "blocking_conditions": ["skin_panel_event_only", "asset_not_applied_to_runtime"],
            "model_guidance": ["Use generated assets only when they are actually rendered.", "Record visual before/after evidence."],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
        },
        {
            "task_card_id": f"{base}_commercial_audio_runtime",
            "title": "Verify and repair BGM SFX voice and volume runtime",
            "description": "Make BGM, place/clear SFX, reward voice, and volume toggle work in browser playtest with media error capture and no NotSupportedError.",
            "goal": "Treat audio as player experience, not just artifact or binding metadata.",
            "write_set": ["state/pipeline_runs/<run>/cocos_project/assets/scripts", "state/pipeline_runs/<run>/cocos_project/assets/resources/commercial_assets/audio"],
            "read_set": ["commercial_asset_bindings.json", "playtest_evidence"],
            "acceptance_criteria": ["BGM start is verified after user gesture.", "SFX and voice playback are verified.", "Volume toggle is visible and changes audio state."],
            "test_commands": ["python -m pytest tests/test_cocos_e2e.py -q"],
            "expected_artifacts": ["audio_runtime_evidence.json"],
            "evidence_requirements": ["audioPlaybackVerified", "bgmStarted", "volumeToggleUsable", "console/page error capture"],
            "blocking_conditions": ["audio_asset_binding_only", "NotSupportedError", "media_decode_error"],
            "model_guidance": ["Use browser-supported formats.", "Capture play promise failures.", "Do not mark audio pass from asset presence alone."],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
        },
        {
            "task_card_id": f"{base}_commercial_core_loop_rewards",
            "title": "Implement core loop rewards and growth economy",
            "description": "Add score, coins, reward moments, unlock progress, and persistence hooks so the game has a real progression loop instead of isolated button events.",
            "goal": "Make the same Cocos project prove a playable loop with rewards, currency, and unlock progress.",
            "write_set": ["state/pipeline_runs/<run>/cocos_project/assets/scripts", "state/pipeline_runs/<run>/cocos_project/assets/resources"],
            "read_set": ["role_output:product_gameplay_agent", "role_output:technical_plan_agent"],
            "acceptance_criteria": ["Coins or reward currency visibly changes.", "Progress unlock state is represented.", "Reward moments connect to gameplay actions."],
            "test_commands": ["python -m pytest tests/test_cocos_e2e.py -q"],
            "expected_artifacts": ["economy_manifest.json", "reward_flow_evidence.json"],
            "evidence_requirements": ["rewardCurrencyChanges", "unlockProgressVisible", "same_project_patch"],
            "blocking_conditions": ["reward_event_only", "no_currency_or_unlock_state"],
            "model_guidance": ["Patch the same project.", "Connect rewards to gameplay state.", "Do not add label-only economy."],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
        },
        {
            "task_card_id": f"{base}_commercial_scene_prefab_ui",
            "title": "Implement Cocos scene prefab UI with player-visible polish",
            "description": "Use the Cocos bridge evidence and project assets to create or bind real scene and prefab UI surfaces for HUD, modal panels, shop, collection, settings, and feedback states.",
            "goal": "Turn UI from debug-like labels into scene/prefab-backed player-visible surfaces in the same project.",
            "write_set": ["state/pipeline_runs/<run>/cocos_project/assets/scene", "state/pipeline_runs/<run>/cocos_project/assets/resources", "state/pipeline_runs/<run>/cocos_project/assets/scripts"],
            "read_set": ["role_output:ui_experience_agent", "cocos_ecosystem_bridge_evidence.json"],
            "acceptance_criteria": ["Scene or prefab UI artifacts exist.", "HUD and panels are player-visible.", "Text and controls do not overlap in screenshots."],
            "test_commands": ["python -m pytest tests/test_cocos_e2e.py -q"],
            "expected_artifacts": ["ui_prefab_manifest.json", "player_visible_screenshot"],
            "evidence_requirements": ["scenePrefabUiEvidence", "panelVisibilityScreenshots", "same_project_patch"],
            "blocking_conditions": ["debug_canvas_only", "panel_labels_without_prefabs"],
            "model_guidance": ["Use Cocos scene/prefab assets.", "Keep Chinese UI visible.", "Record player-visible evidence."],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
        },
        {
            "task_card_id": f"{base}_commercial_human_player_review",
            "title": "Prepare human player review packet",
            "description": "Collect build, screenshots, feature coverage, audio runtime evidence, known blockers, and a concise operator review checklist without marking the game GO before a human accepts it.",
            "goal": "Stop at AWAITING_HUMAN_REVIEW unless a real reviewer accepts the player-visible result.",
            "write_set": ["state/pipeline_runs/<run>/cocos_project/player_visible_evidence", "state/pipeline_runs/<run>/cocos_project/workflow_commercial_feature_evidence.json"],
            "read_set": ["playtest_evidence", "audio_runtime_evidence.json", "same_project_patch_ledger.json"],
            "acceptance_criteria": ["Review packet lists screenshots and blockers.", "No automatic accepted_by_human flag is fabricated.", "Final gate can detect missing human acceptance."],
            "test_commands": ["python -m pytest tests/test_pipeline_and_automation_cli.py::test_commercial_gate_v2_can_stop_at_human_review_only -q"],
            "expected_artifacts": ["human_player_review_packet.json"],
            "evidence_requirements": ["human_review_packet", "awaiting_human_review_status"],
            "blocking_conditions": ["fabricated_human_acceptance", "missing_review_packet"],
            "model_guidance": ["Do not self-approve.", "Prepare evidence for a human reviewer.", "Keep blockers honest."],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
        },
    ]
    candidates = _attach_requirement_coverage(candidates, brief_manifest)
    return _attach_stage_phase_metadata(candidates, base)


def _universal_game_quality_task_card_candidates(
    *,
    base: str,
    pipeline_goal: str,
    brief_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    active_phase_name = "Universal Game Production Quality And AI Playtest Architecture"
    spec = _game_design_spec_from_brief_manifest(brief_manifest)
    cards = build_game_production_task_cards_from_design_spec(
        run_id=base,
        phase_name=active_phase_name,
        spec=spec,
        status="active",
    )
    candidates = [_candidate_from_task_card(card) for card in cards]
    for index, candidate in enumerate(candidates, start=1):
        metadata = dict(candidate.get("metadata") or {})
        metadata.update(
            {
                "active_phase_name": active_phase_name,
                "stage_phase": "universal_game_quality_ai_playtest",
                "phase_order": 1,
                "depends_on_task_card_ids": [candidates[index - 2]["task_card_id"]] if index > 1 else [],
                "game_design_spec_schema": spec.get("schema_version"),
                "pipeline_goal": pipeline_goal,
            }
        )
        candidate["metadata"] = metadata
    return _attach_requirement_coverage(candidates, brief_manifest)


def _game_design_spec_from_brief_manifest(brief_manifest: dict[str, Any]) -> dict[str, Any]:
    matrix = _load_requirement_matrix_payload(brief_manifest)
    requirements = [item for item in matrix.get("requirements") or [] if isinstance(item, dict) and item.get("req_id")]
    if requirements:
        return build_game_design_spec_from_requirement_matrix(
            title="Commercial Game Brief",
            intake_manifest=brief_manifest,
            requirement_matrix={**matrix, "requirements": requirements},
            source_index=_load_source_index_entries(brief_manifest),
        ).to_dict()
    brief_text = _read_brief_text(brief_manifest, limit=20_000)
    return build_game_design_spec(
        title="Commercial Game Brief",
        genre="brief_defined",
        sources=[{"source_id": "project_brief", "raw_text": brief_text or "Game brief missing source text."}],
    ).to_dict()


def _candidate_from_task_card(card: TaskCard) -> dict[str, Any]:
    return {
        "task_card_id": card.task_card_id,
        "title": card.title,
        "description": card.description,
        "goal": card.goal or card.description,
        "write_set": list(card.write_set),
        "read_set": list(card.read_set),
        "acceptance_criteria": list(card.acceptance_criteria),
        "test_commands": list(card.test_commands),
        "expected_artifacts": list(card.expected_artifacts),
        "evidence_requirements": list(card.evidence_requirements),
        "blocking_conditions": list(card.blocking_conditions),
        "model_guidance": list(card.model_guidance),
        "risk_level": card.risk_level,
        "provider_lane": card.provider_lane or "codex_or_configured_strong_model",
        "execution_mode": card.execution_mode or "same_project_patch",
        "metadata": dict(card.metadata or {}),
    }


def _active_phase_blueprint_task_card_candidates(
    *,
    base: str,
    pipeline_goal: str,
    brief_manifest: dict[str, Any],
    active_phase_name: str,
    stage_phase: str,
) -> list[dict[str, Any]]:
    spec = _game_design_spec_from_brief_manifest(brief_manifest)
    blueprint = build_phase_execution_blueprint(
        run_id=base,
        phase_name=active_phase_name,
        spec=spec,
    )
    cards, compile_report = compile_task_cards_from_phase_execution_blueprint(
        run_id=base,
        phase_name=active_phase_name,
        spec=spec,
        blueprint=blueprint,
        status="active",
    )
    blueprint_payload = blueprint.to_dict()
    compile_report_payload = compile_report.to_dict()
    candidates = [_candidate_from_task_card(card) for card in cards]
    for index, candidate in enumerate(candidates, start=1):
        metadata = dict(candidate.get("metadata") or {})
        metadata.update(
            {
                "active_phase_name": active_phase_name,
                "stage_phase": stage_phase,
                "phase_order": 1,
                "depends_on_task_card_ids": [candidates[index - 2]["task_card_id"]] if index > 1 else [],
                "game_design_spec_schema": spec.get("schema_version"),
                "pipeline_goal": pipeline_goal,
                "task_card_materialization": "phase_execution_blueprint_compiled",
                "_phase_execution_blueprint_artifact": blueprint_payload,
                "_task_card_compile_report_artifact": compile_report_payload,
            }
        )
        candidate["metadata"] = metadata
    return _attach_requirement_coverage(candidates, brief_manifest)


def _product_body_runtime_task_card_candidates(
    *,
    base: str,
    pipeline_goal: str,
    brief_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    return _active_phase_blueprint_task_card_candidates(
        base=base,
        pipeline_goal=pipeline_goal,
        brief_manifest=brief_manifest,
        active_phase_name="Product Body Runtime And Semantic Trace Implementation",
        stage_phase="product_body_runtime_semantic_trace",
    )
    phase = "product_body_runtime_semantic_trace"
    active_phase_name = "Product Body Runtime And Semantic Trace Implementation"
    candidates = [
        {
            "task_card_id": f"{base}_runtime_models",
            "title": "Implement product body runtime models",
            "description": "Convert BoardModel, PieceModel, RuleEngine, CandidateTray, and SemanticTestBridge from baseline component shells into deterministic runtime models in the same Cocos project.",
            "goal": f"Implement real product-body runtime state for {pipeline_goal} before any commercial content phase starts.",
            "write_set": [
                "state/pipeline_runs/<run>/cocos_project/assets/scripts",
                "state/pipeline_runs/<run>/cocos_project/workflow_runtime_evidence",
            ],
            "read_set": ["role_output:technical_plan_agent", "requirement_matrix.json", "workflow_product_body_baseline.json"],
            "acceptance_criteria": [
                "Board, piece, rule, tray, and semantic bridge models hold runtime state.",
                "Runtime model evidence is emitted from model logic rather than DOM or canvas hooks.",
                "Baseline-only manifests remain marked as non-commercial delivery evidence.",
            ],
            "test_commands": [
                "python -m pytest tests/test_cocos_product_body_baseline.py tests/test_commercial_game_evidence_contracts.py -q"
            ],
            "expected_artifacts": ["BoardModel.ts", "PieceModel.ts", "RuleEngine.ts", "CandidateTray.ts", "SemanticTestBridge.ts"],
            "evidence_requirements": [
                "runtime_model_state",
                "gameplay_semantic_evidence",
                "product_body_evidence",
                "requirement_coverage_trace",
            ],
            "blocking_conditions": ["baseline_component_only", "runtime_hook_evidence", "canvas_or_dom_event_only_trace"],
            "model_guidance": [
                "Patch the persistent Cocos project only.",
                "Keep BoardModel and RuleEngine as runtime state sources, not UI event mirrors.",
                "Do not set commercial_playable_go.",
            ],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
            "metadata": {
                "active_phase_name": active_phase_name,
                "stage_phase": phase,
                "phase_order": 1,
                "depends_on_task_card_ids": [],
            },
        },
        {
            "task_card_id": f"{base}_semantic_core_loop_traces",
            "title": "Implement 10x10 semantic core-loop traces",
            "description": "Implement 10x10 board placement, line clear, candidate refresh, game-over, and anti-stall semantic traces sourced from runtime state transitions.",
            "goal": "Make gameplay semantic evidence prove the playable core loop from runtime model transitions, not event coverage.",
            "write_set": [
                "state/pipeline_runs/<run>/cocos_project/assets/scripts",
                "state/pipeline_runs/<run>/cocos_project/workflow_runtime_evidence/semantic_traces",
            ],
            "read_set": ["workflow_runtime_evidence/gameplay_semantic_evidence.raw.json", "role_output:product_gameplay_agent"],
            "acceptance_criteria": [
                "Board evidence proves a 10x10 state.",
                "Placement, line clear, candidate refresh, game-over, and anti-stall traces are emitted.",
                "Trace evidence can satisfy the gameplay semantic contract without DOM or canvas hooks.",
            ],
            "test_commands": [
                "python -m pytest tests/test_cocos_product_body_baseline.py tests/test_commercial_game_evidence_contracts.py -q"
            ],
            "expected_artifacts": ["semantic_traces/*.json", "gameplay_semantic_evidence.json"],
            "evidence_requirements": [
                "semantic_placement_trace",
                "semantic_line_clear_trace",
                "semantic_candidate_refresh_trace",
                "semantic_game_over_trace",
                "semantic_anti_stall_trace",
                "requirement_coverage_trace",
            ],
            "blocking_conditions": ["event_only_gameplay_evidence", "semantic_board_state_missing", "semantic_trace_missing"],
            "model_guidance": [
                "Drive traces from model transitions.",
                "Keep candidate tray size at three.",
                "Reject feature flags as gameplay evidence.",
            ],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
            "metadata": {
                "active_phase_name": active_phase_name,
                "stage_phase": phase,
                "phase_order": 1,
                "depends_on_task_card_ids": [f"{base}_runtime_models"],
            },
        },
        {
            "task_card_id": f"{base}_scene_prefab_component_evidence",
            "title": "Bind scene prefab component evidence",
            "description": "Bind BoardView, InputController, LevelGoalController, ShopSkinController, AudioFeedbackController, HUD, shop, skin, gallery, and audio controls to product-body evidence.",
            "goal": "Connect runtime model evidence to scene and component evidence so the next commercial content phase starts from a real product body.",
            "write_set": [
                "state/pipeline_runs/<run>/cocos_project/assets/scene",
                "state/pipeline_runs/<run>/cocos_project/assets/scripts",
                "state/pipeline_runs/<run>/cocos_project/workflow_runtime_evidence",
            ],
            "read_set": ["role_output:ui_experience_agent", "workflow_runtime_evidence/product_body_evidence.raw.json"],
            "acceptance_criteria": [
                "Required scene nodes and component bindings are present in evidence.",
                "HUD, shop, skin, gallery, and audio controls have component-level bindings.",
                "Product-body evidence passes while commercial playable GO remains false.",
            ],
            "test_commands": [
                "python -m pytest tests/test_cocos_product_body_baseline.py tests/test_pipeline_and_automation_cli.py -q"
            ],
            "expected_artifacts": ["product_body_scene_manifest.json", "product_body_evidence.json"],
            "evidence_requirements": [
                "BoardView",
                "InputController",
                "LevelGoalController",
                "ShopSkinController",
                "AudioFeedbackController",
                "scene_component_binding",
                "requirement_coverage_trace",
            ],
            "blocking_conditions": ["scene_product_body_missing", "cocos_component_binding_missing", "commercial_playable_go_claimed"],
            "model_guidance": [
                "Use component and scene evidence rather than browser event hooks.",
                "Preserve the final human review boundary.",
                "Do not create future-phase task cards.",
            ],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
            "metadata": {
                "active_phase_name": active_phase_name,
                "stage_phase": phase,
                "phase_order": 1,
                "depends_on_task_card_ids": [f"{base}_semantic_core_loop_traces"],
            },
        },
    ]
    return _attach_requirement_coverage(candidates, brief_manifest)


def _commercial_core_content_task_card_candidates(
    *,
    base: str,
    pipeline_goal: str,
    brief_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    return _active_phase_blueprint_task_card_candidates(
        base=base,
        pipeline_goal=pipeline_goal,
        brief_manifest=brief_manifest,
        active_phase_name="Commercial Game Core Content Implementation",
        stage_phase="commercial_game_core_content",
    )
    active_phase_name = "Commercial Game Core Content Implementation"
    phase = "commercial_game_core_content"
    common_write_set = [
        "state/pipeline_runs/<run>/cocos_project/assets/scripts",
        "state/pipeline_runs/<run>/cocos_project/assets/resources",
        "state/pipeline_runs/<run>/cocos_project/workflow_runtime_evidence",
    ]
    candidates = [
        {
            "task_card_id": f"{base}_core_loop_levels",
            "title": "Implement commercial core loop and level content",
            "description": "Implement player-facing 10x10 block-puzzle levels, goals, scoring, failure, revive, and progression on top of the real runtime model.",
            "goal": f"Turn {pipeline_goal} into playable core-loop and level content without claiming final commercial completion.",
            "write_set": common_write_set,
            "read_set": ["requirement_matrix.json", "workflow_runtime_evidence/gameplay_semantic_evidence.json", "role_output:product_gameplay_agent"],
            "acceptance_criteria": [
                "Core loop uses BoardModel, RuleEngine, and CandidateTray state transitions.",
                "Level goals, scoring, revive/failure, and progression are player-visible.",
                "Semantic evidence remains model-sourced and commercial_playable_go stays false.",
            ],
            "test_commands": ["python -m pytest tests/test_cocos_product_body_baseline.py tests/test_commercial_game_evidence_contracts.py -q"],
            "expected_artifacts": ["assets/scripts/*Level*.ts", "workflow_runtime_evidence/gameplay_semantic_evidence.json"],
            "evidence_requirements": ["core_loop_runtime_evidence", "level_goal_evidence", "human_visible_cli_session"],
            "blocking_conditions": ["event_only_gameplay_evidence", "baseline_only", "commercial_playable_go_claimed"],
            "model_guidance": ["Patch the persistent Cocos project only.", "Use human_visible_cli_enforced.", "Do not set commercial_playable_go."],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
            "metadata": {"active_phase_name": active_phase_name, "stage_phase": phase, "phase_order": 1},
        },
        {
            "task_card_id": f"{base}_shop_skin_gallery",
            "title": "Implement commercial shop skin and gallery content",
            "description": "Implement shop ownership, skin equip visual state, gallery collection, and player-readable unlock paths.",
            "goal": "Make monetization-adjacent content real and player-visible without using feature flags as evidence.",
            "write_set": common_write_set,
            "read_set": ["requirement_matrix.json", "role_output:ui_experience_agent", "workflow_runtime_evidence/product_body_evidence.json"],
            "acceptance_criteria": [
                "Shop and skin ownership states are stored and visible.",
                "Equipped skin changes the board or piece presentation.",
                "Gallery or collection state is inspectable in evidence.",
            ],
            "test_commands": ["python -m pytest tests/test_commercial_game_evidence_contracts.py tests/test_pipeline_and_automation_cli.py -q"],
            "expected_artifacts": ["assets/scripts/*Shop*.ts", "assets/scripts/*Skin*.ts", "assets/scripts/*Gallery*.ts"],
            "evidence_requirements": ["shop_ownership_state", "skin_equipped_visual_change", "gallery_collection_state", "human_visible_cli_session"],
            "blocking_conditions": ["feature_flag_only_evidence", "scene_product_body_missing", "commercial_playable_go_claimed"],
            "model_guidance": ["Bind UI state to Cocos components.", "Use human_visible_cli_enforced.", "Record player-visible evidence paths."],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
            "metadata": {"active_phase_name": active_phase_name, "stage_phase": phase, "phase_order": 1},
        },
        {
            "task_card_id": f"{base}_audio_feedback_polish",
            "title": "Implement commercial audio feedback and polish content",
            "description": "Implement SFX/BGM/volume controls, placement/clear/failure feedback, animation hooks, and polished HUD signals.",
            "goal": "Make audio, feedback, and polish evidence runtime-bound and player-visible.",
            "write_set": common_write_set,
            "read_set": ["requirement_matrix.json", "role_output:multimodal_generation_agent", "role_output:qa_player_perspective_agent"],
            "acceptance_criteria": [
                "Placement, line-clear, failure, and success feedback are bound to runtime events.",
                "BGM/SFX and volume controls produce auditable evidence.",
                "Polish evidence is not represented by flags alone.",
            ],
            "test_commands": ["python -m pytest tests/test_commercial_game_evidence_contracts.py tests/test_cocos_product_body_baseline.py -q"],
            "expected_artifacts": ["assets/scripts/*Audio*.ts", "assets/scripts/*Feedback*.ts", "workflow_runtime_evidence/product_depth_evidence.json"],
            "evidence_requirements": ["audio_runtime_evidence", "feedback_animation_evidence", "human_visible_cli_session"],
            "blocking_conditions": ["audio_runtime_not_verified", "animation_feedback_missing", "commercial_playable_go_claimed"],
            "model_guidance": ["Bind feedback to runtime model events.", "Use human_visible_cli_enforced.", "Keep final human review pending."],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
            "metadata": {"active_phase_name": active_phase_name, "stage_phase": phase, "phase_order": 1},
        },
    ]
    return _attach_requirement_coverage(candidates, brief_manifest)


def _commercial_machine_evidence_task_card_candidates(
    *,
    base: str,
    pipeline_goal: str,
    brief_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    active_phase_name = "Commercial Machine Evidence And Player Visible Completion"
    phase = "commercial_machine_evidence_player_visible_completion"
    common_write_set = [
        "state/pipeline_runs/<run>/cocos_project/assets/scripts",
        "state/pipeline_runs/<run>/cocos_project/assets/scene",
        "state/pipeline_runs/<run>/cocos_project/assets/resources",
        "state/pipeline_runs/<run>/cocos_project/workflow_runtime_evidence",
        "state/pipeline_runs/<run>/cocos_project/player_visible_evidence",
    ]
    candidates = [
        {
            "task_card_id": f"{base}_product_depth_chinese_ui",
            "title": "Complete product depth and Chinese UI evidence",
            "description": "Patch the persistent Cocos project so product-depth evidence proves at least eight distinct level goals and real Chinese HUD, shop, gallery, settings, and failure/revive panels.",
            "goal": f"Resolve product-depth blockers for {pipeline_goal} without creating a new project or declaring final commercial playable GO.",
            "write_set": common_write_set,
            "read_set": [
                "requirement_matrix.json",
                "workflow_runtime_evidence/product_depth_evidence.json",
                "workflow_runtime_evidence/level_goal_evidence.json",
                "role_output:product_gameplay_agent",
                "role_output:ui_experience_agent",
            ],
            "acceptance_criteria": [
                "Product-depth evidence reports at least eight distinct player-visible level goals.",
                "Chinese UI panels for HUD, shop, gallery, settings, and failure/revive are represented in scene or component evidence.",
                "Evidence remains runtime/player-visible and commercial_playable_go remains false.",
            ],
            "test_commands": [
                "python -m pytest tests/test_commercial_game_evidence_contracts.py tests/test_cocos_product_body_baseline.py -q"
            ],
            "expected_artifacts": ["workflow_runtime_evidence/level_goal_evidence.json", "workflow_runtime_evidence/product_depth_evidence.json"],
            "evidence_requirements": ["eightDistinctLevelGoals", "chineseUiPanelsVisible", "levelFlowPlayable", "failureReviveFeedback"],
            "blocking_conditions": ["levels_not_distinct_or_less_than_eight", "chinese_ui_panels_missing", "debug_canvas_only"],
            "model_guidance": ["Patch only the persistent Cocos project.", "Write product-depth evidence from real runtime/scene state.", "Keep final human review pending."],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
            "metadata": {"active_phase_name": active_phase_name, "stage_phase": phase, "phase_order": 1},
        },
        {
            "task_card_id": f"{base}_build_browser_machine_evidence",
            "title": "Produce Cocos build and browser playtest machine evidence",
            "description": "Repair the same project until Cocos build, local HTTP launch, desktop/mobile browser screenshots, audio runtime, and Cocos bridge evidence can be collected as machine-readable evidence.",
            "goal": "Turn build/playtest/browser/audio blockers into real machine evidence, never build-only or event-only proof.",
            "write_set": common_write_set + ["state/pipeline_runs/<run>/cocos_project/build", "state/pipeline_runs/<run>/cocos_project/playtest_evidence"],
            "read_set": [
                "Cocos Creator executable",
                "workflow_runtime_evidence/build_ledger.json",
                "workflow_runtime_evidence/browser_playtest_ledger.json",
                "workflow_runtime_evidence/gameplay_semantic_evidence.json",
                "workflow_runtime_evidence/product_body_evidence.json",
            ],
            "acceptance_criteria": [
                "Cocos build ledger is based on a real Creator command and successful artifact path.",
                "Browser playtest ledger includes HTTP URL, screenshots, mobile viewport proof, and audio runtime proof or honest blockers.",
                "Cocos ecosystem bridge evidence is preserved as blocker or GO without filesystem-only downgrade.",
            ],
            "test_commands": ["python -m pytest tests/test_pipeline_and_automation_cli.py tests/test_commercial_game_evidence_contracts.py -q"],
            "expected_artifacts": ["workflow_runtime_evidence/build_ledger.json", "workflow_runtime_evidence/browser_playtest_ledger.json", "playtest_evidence/*"],
            "evidence_requirements": ["cocos_build_artifact", "browser_http_launch", "mobile_viewport_screenshot", "audio_runtime_proof", "cocos_ecosystem_bridge_evidence"],
            "blocking_conditions": ["cocos_build_missing", "browser_playtest_missing", "mobile_viewport_evidence_missing", "audio_runtime_not_verified"],
            "model_guidance": ["Use real build and playtest evidence where available.", "Do not synthesize screenshots or Cocos bridge success.", "Record blockers honestly when the environment cannot complete a machine step."],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
            "metadata": {"active_phase_name": active_phase_name, "stage_phase": phase, "phase_order": 1, "depends_on_task_card_ids": [f"{base}_product_depth_chinese_ui"]},
        },
        {
            "task_card_id": f"{base}_human_review_packet_gate",
            "title": "Prepare AWAITING_HUMAN_REVIEW packet and final gate evidence",
            "description": "Collect player-visible review evidence, known blockers, screenshots, runtime contracts, and a final gate packet that stops at AWAITING_HUMAN_REVIEW unless an actual human reviewer accepts.",
            "goal": "Make the commercial game reviewable without unattended self-approval or commercial_playable_go fabrication.",
            "write_set": [
                "state/pipeline_runs/<run>/cocos_project/player_visible_evidence",
                "state/pipeline_runs/<run>/cocos_project/workflow_commercial_feature_evidence.json",
                "state/pipeline_runs/<run>/cocos_project/workflow_runtime_evidence",
            ],
            "read_set": [
                "workflow_runtime_evidence/product_depth_evidence.json",
                "workflow_runtime_evidence/build_ledger.json",
                "workflow_runtime_evidence/browser_playtest_ledger.json",
                "task_card_worker/same_project_patch_ledger.json",
            ],
            "acceptance_criteria": [
                "Human review packet lists screenshots, machine contracts, and remaining blockers.",
                "accepted_by_human remains false unless external human evidence exists.",
                "Final gate can reach AWAITING_HUMAN_REVIEW only after machine evidence passes.",
            ],
            "test_commands": [
                "python -m pytest tests/test_pipeline_and_automation_cli.py::test_commercial_gate_v2_can_stop_at_human_review_only -q"
            ],
            "expected_artifacts": ["player_visible_evidence/human_player_review_packet.json"],
            "evidence_requirements": ["human_review_packet", "awaiting_human_review_status", "no_self_approval"],
            "blocking_conditions": ["fabricated_human_acceptance", "missing_review_packet", "commercial_playable_go_claimed"],
            "model_guidance": ["Do not self-approve commercial playable GO.", "Prepare the packet for external human player review.", "Keep blockers and machine evidence status explicit."],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
            "metadata": {
                "active_phase_name": active_phase_name,
                "stage_phase": phase,
                "phase_order": 1,
                "depends_on_task_card_ids": [f"{base}_product_depth_chinese_ui", f"{base}_build_browser_machine_evidence"],
            },
        },
    ]
    return _attach_requirement_coverage(candidates, brief_manifest)


def _commercial_asset_browser_runtime_task_card_candidates(
    *,
    base: str,
    pipeline_goal: str,
    brief_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    active_phase_name = "Commercial Asset And Browser Runtime Proof Implementation"
    phase = "commercial_asset_browser_runtime_proof"
    common_write_set = [
        "state/pipeline_runs/<run>/cocos_project/assets/scripts",
        "state/pipeline_runs/<run>/cocos_project/assets/resources",
        "state/pipeline_runs/<run>/cocos_project/workflow_runtime_evidence",
        "state/pipeline_runs/<run>/cocos_project/playtest_evidence",
        "state/pipeline_runs/<run>/cocos_project/player_visible_evidence",
    ]
    candidates = [
        {
            "task_card_id": f"{base}_non_placeholder_asset_graph",
            "title": "Prove non-placeholder commercial asset graph",
            "description": "Generate, import, or bind non-placeholder commercial art/audio assets and write machine-readable provenance that blocks placeholder-only packs from commercial GO.",
            "goal": f"Resolve placeholder asset blockers for {pipeline_goal} without accepting local placeholder packs as commercial assets.",
            "write_set": common_write_set + ["state/pipeline_runs/<run>/assets"],
            "read_set": [
                "commercial_game_assets",
                "workflow_runtime_evidence/product_body_evidence.json",
                "role_output:multimodal_generation_agent",
            ],
            "acceptance_criteria": [
                "Asset manifest is not placeholder_only and lists required art/audio assets.",
                "Each required asset has provider or generation provenance, artifact paths, and binding evidence.",
                "Asset graph blockers are recorded honestly when real providers or imports are unavailable.",
            ],
            "test_commands": ["python -m pytest tests/test_commercial_game_evidence_contracts.py tests/test_pipeline_and_automation_cli.py -q"],
            "expected_artifacts": ["assets/commercial_game_asset_stage.json", "workflow_runtime_evidence/asset_binding_evidence.json"],
            "evidence_requirements": ["non_placeholder_asset_manifest", "asset_binding_evidence", "provider_or_import_provenance"],
            "blocking_conditions": ["placeholder_assets_only", "required_asset_missing", "provider_or_import_provenance_missing"],
            "model_guidance": [
                "Do not relabel local stable placeholders as commercial assets.",
                "Bind assets into the persistent Cocos project when available.",
                "Keep commercial_playable_go false without human acceptance.",
            ],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
            "metadata": {"active_phase_name": active_phase_name, "stage_phase": phase, "phase_order": 1},
        },
        {
            "task_card_id": f"{base}_browser_interaction_runtime_proof",
            "title": "Prove browser player interaction runtime",
            "description": "Make the built Cocos output expose player-visible interaction proof from runtime/model state and screenshots, not DOM-only or canvas-only evidence.",
            "goal": "Turn browser playtest into real player-visible runtime evidence with interaction screenshots and model-backed state changes.",
            "write_set": common_write_set + ["state/pipeline_runs/<run>/cocos_project/build"],
            "read_set": [
                "workflow_runtime_evidence/build_ledger.json",
                "workflow_runtime_evidence/browser_playtest_ledger.json",
                "workflow_runtime_evidence/gameplay_semantic_evidence.json",
                "workflow_runtime_evidence/product_depth_evidence.json",
            ],
            "acceptance_criteria": [
                "Browser playtest records HTTP URL, mobile and desktop screenshots, and runtime state before/after interaction.",
                "Interaction proof is model/runtime backed and not only canvas presence or DOM event logs.",
                "Browser blockers remain explicit when the built output cannot be interacted with.",
            ],
            "test_commands": ["python -m pytest tests/test_cocos_e2e.py tests/test_commercial_game_evidence_contracts.py -q"],
            "expected_artifacts": ["playtest_evidence/cocos_playtest_result.json", "workflow_runtime_evidence/browser_playtest_ledger.json"],
            "evidence_requirements": ["browser_http_launch", "mobile_viewport_screenshot", "runtime_interaction_state", "model_backed_browser_trace"],
            "blocking_conditions": ["browser_playtest_no_go", "canvas_only_browser_evidence", "runtime_interaction_state_missing"],
            "model_guidance": [
                "Expose a test bridge only as a view into runtime/model state.",
                "Do not treat canvas visibility or click events as product completion.",
                "Preserve screenshots and blockers for human review.",
            ],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
            "metadata": {
                "active_phase_name": active_phase_name,
                "stage_phase": phase,
                "phase_order": 1,
                "depends_on_task_card_ids": [f"{base}_non_placeholder_asset_graph"],
            },
        },
        {
            "task_card_id": f"{base}_browser_audio_volume_runtime_proof",
            "title": "Prove browser audio BGM SFX and volume runtime",
            "description": "Bind BGM, SFX, and volume controls into the Cocos runtime and browser playtest evidence without replacing proof with feature flags.",
            "goal": "Resolve browser audio, BGM, SFX, and volume-toggle blockers using runtime audio state and player-visible controls.",
            "write_set": common_write_set,
            "read_set": [
                "workflow_runtime_evidence/audio_feedback_polish_evidence.json",
                "workflow_runtime_evidence/browser_playtest_ledger.json",
                "role_output:multimodal_generation_agent",
                "playtest_evidence/cocos_playtest_result.json",
            ],
            "acceptance_criteria": [
                "BGM start, SFX playback, and volume toggle are proven in browser runtime evidence.",
                "Audio proof is tied to runtime controls and no console/page audio errors are present.",
                "If browser audio is blocked by autoplay or environment policy, the blocker is preserved rather than downgraded.",
            ],
            "test_commands": ["python -m pytest tests/test_pipeline_and_automation_cli.py tests/test_commercial_game_evidence_contracts.py tests/test_cocos_e2e.py -q"],
            "expected_artifacts": ["workflow_runtime_evidence/audio_feedback_polish_evidence.json", "playtest_evidence/cocos_playtest_result.json"],
            "evidence_requirements": ["audio_runtime_proof", "bgm_runtime_proof", "sfx_runtime_proof", "volume_toggle_runtime_proof"],
            "blocking_conditions": ["audio_runtime_not_verified", "bgm_runtime_not_verified", "sfx_runtime_not_verified", "volume_toggle_missing"],
            "model_guidance": [
                "Use real browser runtime state and player-visible controls.",
                "Do not satisfy audio proof with metadata-only flags.",
                "Stop at AWAITING_HUMAN_REVIEW if all machine evidence passes.",
            ],
            "risk_level": "high",
            "provider_lane": "codex_cli",
            "execution_mode": "same_project_patch",
            "metadata": {
                "active_phase_name": active_phase_name,
                "stage_phase": phase,
                "phase_order": 1,
                "depends_on_task_card_ids": [
                    f"{base}_non_placeholder_asset_graph",
                    f"{base}_browser_interaction_runtime_proof",
                ],
            },
        },
    ]
    return _attach_requirement_coverage(candidates, brief_manifest)


def _stage_internal_phase_graph(
    pipeline_id: str,
    *,
    pipeline_goal: str = "",
    brief_manifest: dict[str, Any] | None = None,
    pipeline_template: str | None = None,
) -> dict[str, Any]:
    base = _safe_id(pipeline_id)
    if _is_universal_game_quality_phase(pipeline_goal):
        spec = _game_design_spec_from_brief_manifest(brief_manifest or {})
        cards = build_game_production_task_cards_from_design_spec(
            run_id=base,
            phase_name="Universal Game Production Quality And AI Playtest Architecture",
            spec=spec,
            status="active",
        )
        return {
            "schema_version": "commercial_game_stage_internal_phase_graph_v1",
            "pipeline_id": pipeline_id,
            "active_materialization_policy": "only_open_active_phase_task_cards",
            "task_card_materialization": "phase_execution_blueprint_compiled",
            "phase_execution_blueprint_required": True,
            "future_phase_task_cards_materialized": False,
            "phases": [
                {
                    "phase_id": f"{base}_universal_game_production_quality_ai_playtest",
                    "order": 1,
                    "title": "Universal Game Production Quality And AI Playtest Architecture",
                    "task_card_ids": [card.task_card_id for card in cards],
                }
            ],
        }
    if _is_product_body_runtime_phase(pipeline_goal):
        candidates = _active_phase_blueprint_task_card_candidates(
            base=base,
            pipeline_goal=pipeline_goal,
            brief_manifest=brief_manifest or {},
            active_phase_name="Product Body Runtime And Semantic Trace Implementation",
            stage_phase="product_body_runtime_semantic_trace",
        )
        return {
            "schema_version": "commercial_game_stage_internal_phase_graph_v1",
            "pipeline_id": pipeline_id,
            "active_materialization_policy": "only_open_active_phase_task_cards",
            "task_card_materialization": "phase_execution_blueprint_compiled",
            "phase_execution_blueprint_required": True,
            "future_phase_task_cards_materialized": False,
            "phases": [
                {
                    "phase_id": f"{base}_product_body_runtime_semantic_trace",
                    "order": 1,
                    "title": "Product Body Runtime And Semantic Trace Implementation",
                    "task_card_ids": [candidate["task_card_id"] for candidate in candidates],
                }
            ],
        }
    if _is_commercial_core_content_phase(pipeline_goal):
        candidates = _active_phase_blueprint_task_card_candidates(
            base=base,
            pipeline_goal=pipeline_goal,
            brief_manifest=brief_manifest or {},
            active_phase_name="Commercial Game Core Content Implementation",
            stage_phase="commercial_game_core_content",
        )
        return {
            "schema_version": "commercial_game_stage_internal_phase_graph_v1",
            "pipeline_id": pipeline_id,
            "active_materialization_policy": "only_open_active_phase_task_cards",
            "task_card_materialization": "phase_execution_blueprint_compiled",
            "phase_execution_blueprint_required": True,
            "future_phase_task_cards_materialized": False,
            "phases": [
                {
                    "phase_id": f"{base}_commercial_game_core_content",
                    "order": 1,
                    "title": "Commercial Game Core Content Implementation",
                    "task_card_ids": [candidate["task_card_id"] for candidate in candidates],
                }
            ],
        }
    if _is_commercial_machine_evidence_phase(pipeline_goal):
        return {
            "schema_version": "commercial_game_stage_internal_phase_graph_v1",
            "pipeline_id": pipeline_id,
            "active_materialization_policy": "only_open_active_phase_task_cards",
            "future_phase_task_cards_materialized": False,
            "phases": [
                {
                    "phase_id": f"{base}_commercial_machine_evidence_player_visible_completion",
                    "order": 1,
                    "title": "Commercial Machine Evidence And Player Visible Completion",
                    "task_card_ids": [
                        f"{base}_product_depth_chinese_ui",
                        f"{base}_build_browser_machine_evidence",
                        f"{base}_human_review_packet_gate",
                    ],
                }
            ],
        }
    if _is_commercial_asset_browser_runtime_phase(pipeline_goal):
        return {
            "schema_version": "commercial_game_stage_internal_phase_graph_v1",
            "pipeline_id": pipeline_id,
            "active_materialization_policy": "only_open_active_phase_task_cards",
            "future_phase_task_cards_materialized": False,
            "phases": [
                {
                    "phase_id": f"{base}_commercial_asset_browser_runtime_proof",
                    "order": 1,
                    "title": "Commercial Asset And Browser Runtime Proof Implementation",
                    "task_card_ids": [
                        f"{base}_non_placeholder_asset_graph",
                        f"{base}_browser_interaction_runtime_proof",
                        f"{base}_browser_audio_volume_runtime_proof",
                    ],
                }
            ],
        }
    if _is_commercial_game_production_template(pipeline_template):
        candidates = _active_phase_blueprint_task_card_candidates(
            base=base,
            pipeline_goal=pipeline_goal,
            brief_manifest=brief_manifest or {},
            active_phase_name="Commercial Game Core Content Implementation",
            stage_phase="commercial_game_core_content",
        )
        return {
            "schema_version": "commercial_game_stage_internal_phase_graph_v1",
            "pipeline_id": pipeline_id,
            "active_materialization_policy": "only_open_active_phase_task_cards",
            "task_card_materialization": "phase_execution_blueprint_compiled",
            "phase_execution_blueprint_required": True,
            "future_phase_task_cards_materialized": False,
            "phases": [
                {
                    "phase_id": f"{base}_commercial_game_core_content",
                    "order": 1,
                    "title": "Commercial Game Core Content Implementation",
                    "task_card_ids": [candidate["task_card_id"] for candidate in candidates],
                }
            ],
        }
    return {
        "schema_version": "commercial_game_stage_internal_phase_graph_v1",
        "pipeline_id": pipeline_id,
        "active_materialization_policy": "only_open_active_phase_task_cards",
        "future_phase_task_cards_materialized": False,
        "phases": [
            {
                "phase_id": f"{base}_product_depth",
                "order": 1,
                "title": "Product depth implementation",
                "task_card_ids": [
                    f"{base}_commercial_gameplay_levels",
                    f"{base}_commercial_core_loop_rewards",
                ],
            },
            {
                "phase_id": f"{base}_player_visible_ui_assets",
                "order": 2,
                "title": "Player-visible UI assets and shop flow",
                "task_card_ids": [
                    f"{base}_commercial_shop_skin_collection",
                    f"{base}_commercial_scene_prefab_ui",
                ],
            },
            {
                "phase_id": f"{base}_runtime_audio_review",
                "order": 3,
                "title": "Runtime audio and human review packet",
                "task_card_ids": [
                    f"{base}_commercial_audio_runtime",
                    f"{base}_commercial_human_player_review",
                ],
            },
        ],
    }


def _attach_requirement_coverage(candidates: list[dict[str, Any]], brief_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    requirements = _load_requirement_entries(brief_manifest)
    requirement_matrix_path = brief_manifest.get("requirement_matrix_path")
    for candidate in candidates:
        metadata = dict(candidate.get("metadata") or {})
        covered_ids: list[str] = []
        metadata["source_material_policy"] = SOURCE_MATERIAL_POLICY
        metadata["omitted_requirement_ids"] = []
        metadata["source_requirement_count"] = len(requirements)
        if requirements:
            covered_ids = _candidate_requirement_ids(candidate, requirements)
            metadata.update(
                {
                    "requirement_matrix_path": requirement_matrix_path,
                    "covered_requirement_ids": covered_ids,
                }
            )
        if str(candidate.get("execution_mode") or "") == "same_project_patch":
            metadata["human_visible_cli_required"] = True
            metadata["execution_visibility_mode"] = "human_visible_cli_enforced"
            metadata["control_plane_visibility"] = "resident"
            metadata["provider_visibility"] = "direct_visible"
            metadata["provider_output_mode"] = "human_readable"
            candidate["evidence_requirements"] = _append_unique(
                candidate.get("evidence_requirements", []),
                "human_visible_cli_session",
            )
            candidate["evidence_requirements"] = _append_unique(
                candidate.get("evidence_requirements", []),
                "direct_provider_visible_cli_session",
            )
            candidate["model_guidance"] = _append_unique(
                candidate.get("model_guidance", []),
                "Run through human_visible_cli_enforced with resident control plane and direct visible provider CLI for high-risk commercial implementation.",
            )
            if requirements:
                metadata["requirement_coverage_required"] = True
                metadata["required_requirement_ids"] = covered_ids
                candidate["read_set"] = _append_unique(candidate.get("read_set", []), str(requirement_matrix_path))
                candidate["evidence_requirements"] = _append_unique(
                    candidate.get("evidence_requirements", []),
                    "requirement_coverage_trace",
                )
                candidate["model_guidance"] = _append_unique(
                    candidate.get("model_guidance", []),
                    "Cite covered_requirement_ids in implementation evidence.",
                )
        candidate["metadata"] = metadata
    return candidates


def _candidate_requirement_ids(candidate: dict[str, Any], requirements: list[dict[str, Any]]) -> list[str]:
    task_card_id = str(candidate.get("task_card_id") or "").lower()
    candidate_text = json.dumps(candidate, ensure_ascii=False).lower()
    if "human_player_review" in task_card_id or "review" in candidate_text:
        return _requirement_ids(requirements)
    category_hints: set[str] = set()
    if any(token in candidate_text for token in ("audio", "bgm", "sfx", "voice", "音频", "音乐", "音效", "语音")):
        category_hints.update({"multimodal", "qa"})
    if any(token in candidate_text for token in ("ui", "panel", "button", "prefab", "shop", "skin", "collection", "界面", "面板", "按钮", "皮肤", "画廊")):
        category_hints.update({"ui", "multimodal"})
    if any(token in candidate_text for token in ("gameplay", "level", "reward", "economy", "loop", "玩法", "关卡", "奖励", "成长", "循环")):
        category_hints.add("product")
    if any(token in candidate_text for token in ("build", "bridge", "cocos", "runtime", "构建", "工程", "技术")):
        category_hints.add("technical")
    selected = [item for item in requirements if str(item.get("category") or "") in category_hints]
    if not selected:
        selected = [item for item in requirements if str(item.get("priority") or "") == "high"]
    return _requirement_ids(selected or requirements)


def _append_unique(values: Any, item: str) -> list[str]:
    result = [str(value) for value in values] if isinstance(values, list) else []
    if item and item not in result:
        result.append(item)
    return result


def _attach_stage_phase_metadata(candidates: list[dict[str, Any]], base: str) -> list[dict[str, Any]]:
    phase_metadata = {
        f"{base}_commercial_gameplay_levels": {
            "stage_phase": "product_depth",
            "phase_order": 1,
            "depends_on_task_card_ids": [],
        },
        f"{base}_commercial_core_loop_rewards": {
            "stage_phase": "product_depth",
            "phase_order": 1,
            "depends_on_task_card_ids": [f"{base}_commercial_gameplay_levels"],
        },
        f"{base}_commercial_shop_skin_collection": {
            "stage_phase": "player_visible_ui_assets",
            "phase_order": 2,
            "depends_on_task_card_ids": [f"{base}_commercial_core_loop_rewards"],
        },
        f"{base}_commercial_scene_prefab_ui": {
            "stage_phase": "player_visible_ui_assets",
            "phase_order": 2,
            "depends_on_task_card_ids": [f"{base}_commercial_shop_skin_collection"],
        },
        f"{base}_commercial_audio_runtime": {
            "stage_phase": "runtime_audio_review",
            "phase_order": 3,
            "depends_on_task_card_ids": [f"{base}_commercial_scene_prefab_ui"],
        },
        f"{base}_commercial_human_player_review": {
            "stage_phase": "runtime_audio_review",
            "phase_order": 3,
            "depends_on_task_card_ids": [
                f"{base}_commercial_gameplay_levels",
                f"{base}_commercial_shop_skin_collection",
                f"{base}_commercial_audio_runtime",
                f"{base}_commercial_scene_prefab_ui",
            ],
        },
    }
    for candidate in candidates:
        metadata = dict(candidate.get("metadata") or {})
        metadata.update(phase_metadata.get(candidate["task_card_id"], {}))
        if metadata:
            candidate["metadata"] = metadata
    return candidates


def _persist_task_card_candidates(
    *,
    candidates: list[dict[str, Any]],
    db_path: Path,
    target_dir: Path,
    pipeline_id: str,
    pipeline_goal: str,
    pipeline_template: str | None,
    pipeline_name: str | None,
) -> dict[str, Any]:
    migrate(db_path)
    run_repo = RunRepository(db_path)
    task_repo = TaskRepository(db_path)
    if run_repo.get(pipeline_id) is None:
        run_repo.create(
            Run(
                run_id=pipeline_id,
                goal=pipeline_goal,
                preset_id=pipeline_template or pipeline_name or "m109_single_agent_role_pipeline",
                status="prepared",
            )
    )
    stored: list[TaskCard] = []
    blueprint_paths: dict[str, str] = {}
    compile_report_paths: dict[str, str] = {}
    artifact_root = target_dir / "phase_execution_blueprints"
    for candidate in candidates:
        candidate_metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
        candidate_metadata = dict(candidate_metadata)
        blueprint_payload = candidate_metadata.pop("_phase_execution_blueprint_artifact", None)
        compile_report_payload = candidate_metadata.pop("_task_card_compile_report_artifact", None)
        phase_id = str(
            candidate_metadata.get("phase_execution_blueprint_id")
            or candidate_metadata.get("active_phase_name")
            or "active_phase"
        )
        if isinstance(blueprint_payload, dict) and phase_id not in blueprint_paths:
            artifact_root.mkdir(parents=True, exist_ok=True)
            blueprint_path = artifact_root / f"{_safe_id(phase_id)}.json"
            blueprint_path.write_text(json.dumps(blueprint_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            blueprint_paths[phase_id] = blueprint_path.as_posix()
        if isinstance(compile_report_payload, dict) and phase_id not in compile_report_paths:
            artifact_root.mkdir(parents=True, exist_ok=True)
            report_path = artifact_root / f"{_safe_id(phase_id)}.compile_report.json"
            report_path.write_text(json.dumps(compile_report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            compile_report_paths[phase_id] = report_path.as_posix()
        if phase_id in blueprint_paths:
            candidate_metadata["phase_execution_blueprint_path"] = blueprint_paths[phase_id]
        if phase_id in compile_report_paths:
            candidate_metadata["task_card_compile_report_path"] = compile_report_paths[phase_id]
        task_card = TaskCard(
            task_card_id=str(candidate["task_card_id"]),
            run_id=pipeline_id,
            title=str(candidate["title"]),
            description=str(candidate["description"]),
            acceptance_criteria=list(candidate["acceptance_criteria"]),
            milestone="M109",
            phase_name=str(candidate_metadata.get("active_phase_name") or "M109.5 Task Card Quality Gate"),
            goal=str(candidate["goal"]),
            write_set=list(candidate["write_set"]),
            read_set=list(candidate["read_set"]),
            test_commands=list(candidate["test_commands"]),
            expected_artifacts=list(candidate["expected_artifacts"]),
            evidence_requirements=list(candidate["evidence_requirements"]),
            blocking_conditions=list(candidate["blocking_conditions"]),
            model_guidance=list(candidate["model_guidance"]),
            risk_level=str(candidate["risk_level"]),
            provider_lane=str(candidate["provider_lane"]),
            execution_mode=str(candidate["execution_mode"]),
            status="active",
            metadata={
                "generated_by": "task_card_generation_agent",
                "pipeline_template": pipeline_template,
                "authority_source": "sqlite_task_cards",
                **candidate_metadata,
            },
        )
        existing = task_repo.get_task_card(task_card.task_card_id)
        stored.append(existing if existing is not None else task_repo.create_task_card(task_card))
    output_path = export_task_cards_markdown(stored, target_dir / "task_cards.md", title=f"M109 Task Cards for {pipeline_id}")
    quality = task_card_quality_report(stored)
    quality_path = target_dir / "task_card_quality.json"
    quality_path.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "schema_version": "m109_task_card_persistence_v1",
        "db_path": db_path.as_posix(),
        "run_id": pipeline_id,
        "task_card_count": len(stored),
        "task_card_ids": [card.task_card_id for card in stored],
        "markdown_snapshot_path": output_path.as_posix(),
        "quality_report_path": quality_path.as_posix(),
        "phase_execution_blueprint_paths": sorted(blueprint_paths.values()),
        "task_card_compile_report_paths": sorted(compile_report_paths.values()),
        "quality": quality,
    }


def _safe_id(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_") or "pipeline"


def _is_universal_game_quality_phase(value: str) -> bool:
    normalized = str(value or "").lower()
    return "universal game production quality" in normalized and "ai playtest" in normalized


def _is_product_body_runtime_phase(value: str) -> bool:
    normalized = str(value or "").lower()
    return "product body runtime" in normalized and "semantic trace" in normalized


def _is_commercial_core_content_phase(value: str) -> bool:
    normalized = str(value or "").lower()
    return "commercial game core content" in normalized and "implementation" in normalized


def _is_commercial_machine_evidence_phase(value: str) -> bool:
    normalized = str(value or "").lower()
    return "commercial machine evidence" in normalized and "player visible completion" in normalized


def _is_commercial_asset_browser_runtime_phase(value: str) -> bool:
    normalized = str(value or "").lower()
    return "commercial asset" in normalized and "browser runtime proof" in normalized


def _is_commercial_game_production_template(value: str | None) -> bool:
    return str(value or "").strip() == "commercial_game_production"


def _packet_path_for_role(role_id: str, brief_manifest: dict[str, Any]) -> str | None:
    packets = brief_manifest.get("agent_packets") if isinstance(brief_manifest, dict) else None
    if not isinstance(packets, dict):
        return None
    mapping = {
        "intake_packaging_agent": "product_agent",
        "product_gameplay_agent": "product_agent",
        "mechanics_system_designer_agent": "product_agent",
        "level_economy_designer_agent": "product_agent",
        "ui_experience_agent": "ui_agent",
        "ui_ux_polish_agent": "ui_agent",
        "art_direction_agent": "multimodal_agent",
        "animation_vfx_feedback_agent": "multimodal_agent",
        "audio_feedback_designer_agent": "multimodal_agent",
        "technical_plan_agent": "tech_agent",
        "multimodal_generation_agent": "multimodal_agent",
        "ai_playtest_oracle_agent": "qa_agent",
        "task_card_generation_agent": "tech_agent",
        "qa_player_perspective_agent": "qa_agent",
        "commercial_quality_score_agent": "qa_agent",
        "supervisor": "qa_agent",
    }
    return packets.get(mapping.get(role_id, "product_agent"))


def _read_preview(packet_path: str | None, limit: int = 2000) -> str:
    if not packet_path:
        return ""
    path = Path(packet_path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:limit]


def _deliverables_for_role(role_id: str) -> list[str]:
    return {
        "intake_packaging_agent": ["unified_project_brief", "source_index", "agent_packets"],
        "product_gameplay_agent": ["gameplay_goals", "core_loop", "acceptance_outline"],
        "mechanics_system_designer_agent": ["mechanic_contract", "feel_requirements", "state_invariants"],
        "level_economy_designer_agent": ["level_progression_plan", "economy_balance_plan", "content_depth_checks"],
        "ui_experience_agent": ["screen_flow", "panel_requirements", "mobile_ux_constraints"],
        "ui_ux_polish_agent": ["commercial_ui_polish_rubric", "visual_hierarchy_rules", "evidence_expectations"],
        "art_direction_agent": ["asset_style_bible", "art_review_gates"],
        "animation_vfx_feedback_agent": ["motion_feedback_plan", "vfx_quality_checks"],
        "audio_feedback_designer_agent": ["audio_design_sheet", "runtime_audio_evidence"],
        "technical_plan_agent": ["implementation_plan", "write_set_boundaries", "test_plan"],
        "multimodal_generation_agent": ["asset_manifest_requirements", "style_requirements", "provider_route_requirements"],
        "ai_playtest_oracle_agent": ["playtest_modes", "quality_rubric", "repair_loop_triggers"],
        "task_card_generation_agent": ["database_task_card_inputs", "quality_gate_requirements"],
        "qa_player_perspective_agent": ["player_visible_checks", "repair_findings", "go_no_go_recommendation"],
        "commercial_quality_score_agent": ["commercial_quality_scorecard", "hard_blockers", "repair_findings"],
        "supervisor": ["continue_repair_stop_decision", "cluster_upgrade_recommendation"],
    }.get(role_id, ["role_artifact"])


def _next_handoff_for_role(role_id: str) -> str:
    return {
        "intake_packaging_agent": "product_gameplay_agent",
        "product_gameplay_agent": "mechanics_system_designer_agent and ui_experience_agent",
        "mechanics_system_designer_agent": "level_economy_designer_agent and animation_vfx_feedback_agent",
        "level_economy_designer_agent": "art_direction_agent",
        "ui_experience_agent": "ui_ux_polish_agent",
        "ui_ux_polish_agent": "art_direction_agent and audio_feedback_designer_agent",
        "art_direction_agent": "animation_vfx_feedback_agent and multimodal_generation_agent",
        "animation_vfx_feedback_agent": "technical_plan_agent",
        "audio_feedback_designer_agent": "technical_plan_agent and multimodal_generation_agent",
        "technical_plan_agent": "multimodal_generation_agent and task_card_generation_agent",
        "multimodal_generation_agent": "ai_playtest_oracle_agent and task_card_generation_agent",
        "ai_playtest_oracle_agent": "task_card_generation_agent",
        "task_card_generation_agent": "workflow_worker",
        "qa_player_perspective_agent": "commercial_quality_score_agent",
        "commercial_quality_score_agent": "supervisor",
        "supervisor": "workflow_gate",
    }.get(role_id, "workflow_gate")


def _render_role_output_markdown(output: dict[str, Any]) -> str:
    lines = [
        f"# {output['role_id']} Role Output",
        "",
        f"- stage: `{output['stage_name']}`",
        f"- backend: `single_agent_role_protocol_v1`",
        f"- llm_call_status: `{output['llm_call_status']}`",
        f"- agent_packet_path: `{output.get('agent_packet_path') or '-'}`",
        "",
        "## Deliverables",
        "",
    ]
    lines.extend(f"- {item}" for item in output.get("deliverables", []))
    lines.extend(["", "## Next Handoff", "", str(output.get("next_handoff") or "-"), ""])
    return "\n".join(lines)
