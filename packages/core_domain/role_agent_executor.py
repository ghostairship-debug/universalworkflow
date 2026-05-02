from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contracts import PipelineStage, Run, TaskCard
from packages.core_domain.db import migrate
from packages.core_domain.multimodal_route_plan import build_multimodal_route_plan
from packages.core_domain.repositories import RunRepository, TaskRepository
from packages.core_domain.task_card_store import export_task_cards_markdown, task_card_quality_report
from packages.core_domain.unified_project_brief import build_unified_project_brief


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
    "ui_experience_agent": {
        "model_tier": "medium_strong",
        "default_lane": "configured_text_model",
        "reason": "needs visual and interaction judgment",
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
    "qa_player_perspective_agent": {
        "model_tier": "medium_strong",
        "default_lane": "configured_text_or_visual_review_model",
        "reason": "reviews player-visible usability and quality",
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
        f"role_id: {role_id}\n"
        f"stage: {stage.name}\n"
        f"goal: {stage.goal}\n"
        f"brief_manifest: {json.dumps(_compact_manifest(brief_manifest), ensure_ascii=False)}\n"
        f"structured_draft: {json.dumps(structured_output, ensure_ascii=False)[:6000]}\n"
    )
    try:
        chunks = list(
            runtime.stream_reply(
                content=prompt,
                context={"role_id": role_id, "stage_id": stage.stage_id},
                decision=ChatActionDecision(action_type="answer_only", confidence=0.8),
            )
        )
    except Exception as exc:
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
    return {
        "status": "completed",
        "failure_class": None,
        "output_updates": {
            "llm_call_status": "called",
            "generation_mode": "live_llm_augmented_role_builder",
            "llm_provider_evidence": description,
            "llm_response_preview": "".join(chunks)[:4000],
        },
    }


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
        "schema_version": "m109_single_agent_role_output_v1",
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
        "structured_output": structured_output,
        "deliverables": _deliverables_for_role(role_id),
        "evidence_requirements": [
            "role_output_json",
            "role_output_markdown",
            "input_brief_manifest",
            "agent_packet_path",
        ],
        "blocking_conditions": [
            "missing_unified_brief",
            "agent_packet_unreadable",
            "provider_policy_disallows_live_llm_when_required",
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
    source_counts = {
        "source_count": int(brief_manifest.get("source_count") or 0),
        "chunk_count": int(brief_manifest.get("chunk_count") or 0),
        "media_count": int(brief_manifest.get("media_count") or 0),
    }
    context = {
        "pipeline_id": pipeline_id,
        "pipeline_goal": pipeline_goal or stage.goal,
        "pipeline_template": pipeline_template or stage.metadata.get("template"),
        "brief_policy": "source_preserving_unified_brief",
        **source_counts,
    }
    if role_id == "intake_packaging_agent":
        return {
            "context": context,
            "normalized_materials": {
                "project_brief_path": brief_manifest.get("project_brief_path"),
                "source_index_path": brief_manifest.get("source_index_path"),
                "media_manifest_path": brief_manifest.get("media_manifest_path"),
                "agent_packets": brief_manifest.get("agent_packets", {}),
            },
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
            "brief_signal": _brief_signal(brief_text, packet_preview),
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
        }
    if role_id == "task_card_generation_agent":
        return {
            "context": context,
            "stage_internal_phase_graph": _stage_internal_phase_graph(pipeline_id or stage.stage_id),
            "task_card_candidates": _task_card_candidate_payloads(
                pipeline_id=pipeline_id or stage.stage_id,
                pipeline_goal=pipeline_goal or stage.goal,
                pipeline_template=pipeline_template or str(stage.metadata.get("pipeline_recipe") or "commercial_game_production"),
            ),
            "quality_gate": {
                "authority_source": "sqlite_task_cards_table",
                "markdown_role": "human_snapshot_only",
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
            "repair_findings": [],
            "go_no_go_recommendation": "NO-GO until Cocos build/playtest evidence exists",
        }
    if role_id == "supervisor":
        return {
            "context": context,
            "decision": "continue_to_next_honest_handoff_if_current_gate_passes",
            "repair_or_stop_rules": [
                "Repair workflow/runtime bugs before business feature expansion.",
                "Stop commercial-ready claims when evidence is prototype-only.",
                "Upgrade a role to cluster only after repeated single-agent failure evidence.",
            ],
            "cluster_upgrade_recommendation": {
                "default": "keep_single_agent",
                "upgrade_candidates": ["multimodal_generation_agent", "qa_player_perspective_agent"],
                "trigger": "upgrade only if one role repeatedly fails despite clear task cards and evidence",
            },
        }
    return {"context": context, "role_note": "No specialized structured output registered for this role."}


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
    playtest = payload.get("playtest") if isinstance(payload.get("playtest"), dict) else {}
    commercial_playable_go = bool(payload.get("commercial_playable_go") or readiness.get("commercial_playable_go"))
    return {
        "context": context,
        "evidence_source": "shared_outputs.cocos_e2e",
        "player_visible_checks": normalized_checks,
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


def _task_card_candidate_payloads(
    *,
    pipeline_id: str,
    pipeline_goal: str,
    pipeline_template: str,
) -> list[dict[str, Any]]:
    base = _safe_id(pipeline_id)
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
    return _attach_stage_phase_metadata(candidates, base)


def _stage_internal_phase_graph(pipeline_id: str) -> dict[str, Any]:
    base = _safe_id(pipeline_id)
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
    for candidate in candidates:
        task_card = TaskCard(
            task_card_id=str(candidate["task_card_id"]),
            run_id=pipeline_id,
            title=str(candidate["title"]),
            description=str(candidate["description"]),
            acceptance_criteria=list(candidate["acceptance_criteria"]),
            milestone="M109",
            phase_name="M109.5 Task Card Quality Gate",
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
            metadata={
                "generated_by": "task_card_generation_agent",
                "pipeline_template": pipeline_template,
                "authority_source": "sqlite_task_cards",
                **(candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}),
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
        "quality": quality,
    }


def _safe_id(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_") or "pipeline"


def _packet_path_for_role(role_id: str, brief_manifest: dict[str, Any]) -> str | None:
    packets = brief_manifest.get("agent_packets") if isinstance(brief_manifest, dict) else None
    if not isinstance(packets, dict):
        return None
    mapping = {
        "intake_packaging_agent": "product_agent",
        "product_gameplay_agent": "product_agent",
        "ui_experience_agent": "ui_agent",
        "technical_plan_agent": "tech_agent",
        "multimodal_generation_agent": "multimodal_agent",
        "task_card_generation_agent": "tech_agent",
        "qa_player_perspective_agent": "qa_agent",
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
        "ui_experience_agent": ["screen_flow", "panel_requirements", "mobile_ux_constraints"],
        "technical_plan_agent": ["implementation_plan", "write_set_boundaries", "test_plan"],
        "multimodal_generation_agent": ["asset_manifest_requirements", "style_requirements", "provider_route_requirements"],
        "task_card_generation_agent": ["database_task_card_inputs", "quality_gate_requirements"],
        "qa_player_perspective_agent": ["player_visible_checks", "repair_findings", "go_no_go_recommendation"],
        "supervisor": ["continue_repair_stop_decision", "cluster_upgrade_recommendation"],
    }.get(role_id, ["role_artifact"])


def _next_handoff_for_role(role_id: str) -> str:
    return {
        "intake_packaging_agent": "product_gameplay_agent",
        "product_gameplay_agent": "ui_experience_agent",
        "ui_experience_agent": "technical_plan_agent",
        "technical_plan_agent": "multimodal_generation_agent",
        "multimodal_generation_agent": "task_card_generation_agent",
        "task_card_generation_agent": "workflow_worker",
        "qa_player_perspective_agent": "supervisor",
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
