from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

from packages.contracts import TaskCard
from packages.contributions.games.game_design_ir import GameDesignSpec


GAME_PRODUCTION_TASK_CARD_SCHEMA = "universal_game_production_task_cards_v1"
PRODUCT_PHASE_CANDIDATE_SCHEMA = "universal_game_product_phase_candidate_v1"
PHASE_EXECUTION_BLUEPRINT_SCHEMA = "universal_game_phase_execution_blueprint_v1"
TASK_CARD_COMPILE_REPORT_SCHEMA = "universal_game_task_card_compile_report_v1"


@dataclass(frozen=True)
class ProductPhaseCandidate:
    phase_id: str
    title: str
    depends_on: list[str] = field(default_factory=list)
    parallel_group: str | None = None
    source_requirement_ids: list[str] = field(default_factory=list)
    deliverables: list[str] = field(default_factory=list)
    risk_level: str = "high"
    suggested_task_groups: list[str] = field(default_factory=list)
    schema_version: str = PRODUCT_PHASE_CANDIDATE_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PhaseExecutionBlueprint:
    phase_id: str
    phase_name: str
    source_requirement_ids: list[str]
    slices: list[dict[str, Any]]
    generation_mode: str = "agent_phase_blueprint_then_rule_compiler"
    source_material_policy: str = "no_delete_no_merge_no_rename_only_augment"
    schema_version: str = PHASE_EXECUTION_BLUEPRINT_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaskCardCompileReport:
    go: bool
    blockers: list[str]
    phase_id: str
    task_card_ids: list[str]
    covered_requirement_ids: list[str]
    missing_requirement_ids: list[str]
    schema_version: str = TASK_CARD_COMPILE_REPORT_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_game_production_task_cards_from_design_spec(
    *,
    run_id: str,
    phase_name: str,
    spec: GameDesignSpec | dict[str, Any],
    status: str = "draft",
) -> list[TaskCard]:
    blueprint = build_phase_execution_blueprint(
        run_id=run_id,
        phase_name=phase_name,
        spec=spec,
    )
    cards, _report = compile_task_cards_from_phase_execution_blueprint(
        run_id=run_id,
        phase_name=phase_name,
        spec=spec,
        blueprint=blueprint,
        status=status,
    )
    return cards


def build_product_phase_candidates_from_design_spec(
    *,
    run_id: str,
    spec: GameDesignSpec | dict[str, Any],
) -> list[ProductPhaseCandidate]:
    payload = spec.to_dict() if isinstance(spec, GameDesignSpec) else dict(spec)
    all_req_ids = [str(item) for item in payload.get("preserved_requirement_ids") or []]
    return [
        ProductPhaseCandidate(
            phase_id=f"{run_id}_source_truth_and_design_spec",
            title="Source Truth And GameDesignSpec",
            source_requirement_ids=all_req_ids,
            deliverables=["lossless_intake_receipts", "GameDesignSpec", "source_requirement_matrix"],
            risk_level="medium",
            suggested_task_groups=["source_validation", "semantic_design_ir"],
        ),
        ProductPhaseCandidate(
            phase_id=f"{run_id}_engine_native_product_body",
            title="Engine Native Product Body Implementation",
            depends_on=[f"{run_id}_source_truth_and_design_spec"],
            source_requirement_ids=all_req_ids,
            deliverables=["runtime_state_model", "scene_prefab_bindings", "semantic_transition_traces"],
            risk_level="high",
            suggested_task_groups=["runtime", "scene_binding", "semantic_trace"],
        ),
        ProductPhaseCandidate(
            phase_id=f"{run_id}_commercial_content_and_assets",
            title="Commercial Content Assets And Experience",
            depends_on=[f"{run_id}_engine_native_product_body"],
            source_requirement_ids=all_req_ids,
            deliverables=["content_depth", "non_placeholder_assets", "audio_feedback", "ui_ux_polish"],
            risk_level="high",
            suggested_task_groups=["content", "art", "audio", "ui"],
        ),
        ProductPhaseCandidate(
            phase_id=f"{run_id}_ai_playtest_red_team_repair",
            title="AI Playtest Red-Team And Repair Loop",
            depends_on=[f"{run_id}_commercial_content_and_assets"],
            source_requirement_ids=all_req_ids,
            deliverables=["ai_playtest_report", "quality_scorecard", "repair_cards", "human_review_packet"],
            risk_level="medium",
            suggested_task_groups=["playtest", "red_team", "repair"],
        ),
    ]


def build_phase_execution_blueprint(
    *,
    run_id: str,
    phase_name: str,
    spec: GameDesignSpec | dict[str, Any],
) -> PhaseExecutionBlueprint:
    payload = spec.to_dict() if isinstance(spec, GameDesignSpec) else dict(spec)
    requirements = payload.get("requirements") if isinstance(payload.get("requirements"), list) else []
    by_category: dict[str, list[str]] = defaultdict(list)
    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        by_category[str(requirement.get("category") or "design")].append(str(requirement.get("req_id")))
    all_req_ids = [str(item) for item in payload.get("preserved_requirement_ids") or []]
    slices: list[dict[str, Any]] = [
        {
            "slug": "runtime_state_core_loop",
            "title": "Implement engine-native runtime state and core loop",
            "goal": (
                "Implement the authoritative runtime state, core player verbs, win/fail/retry transitions, "
                "save/load fields, and semantic traces defined by the GameDesignSpec."
            ),
            "write_set": [
                "assets/scripts/runtime/gameplay/**",
                "assets/scripts/runtime/model/**",
                "assets/scripts/runtime/input/**",
                "workflow_runtime_evidence/core_loop_runtime_evidence.json",
                "workflow_runtime_evidence/gameplay_semantic_evidence.raw.json",
                "workflow_runtime_evidence/product_body_evidence.raw.json",
            ],
            "read_set": ["GameDesignSpec", "MechanicGraph", "StateModelContract", "InteractionMap"],
            "requirement_ids": _category_ids(by_category, {"mechanic", "rule", "progression", "design"}, fallback=all_req_ids),
            "risk_level": "high",
            "evidence": [
                "engine_native_runtime_state",
                "semantic_model_transition_trace",
                "workflow_runtime_evidence/gameplay_semantic_evidence.raw.json must include board_size, candidate_count or equivalent runtime state, and model_transition_traces/semantic_traces",
                "scripted_core_loop_replay",
                "workflow_runtime_evidence/core_loop_runtime_evidence.json",
                "workflow_runtime_evidence/gameplay_semantic_evidence.raw.json",
                "workflow_runtime_evidence/product_body_evidence.raw.json",
            ],
        },
        {
            "slug": "scene_prefab_component_binding",
            "title": "Bind player-visible scene prefab shell and component evidence",
            "goal": (
                "Bind the current game's runtime model to player-visible Cocos scene, prefab, HUD shell, settings shell, "
                "and review surfaces without relying on a fixed gameplay template."
            ),
            "write_set": [
                "assets/scripts/workflow-e2e-runtime-bridge.js",
                "assets/scene/**",
                "assets/prefabs/**",
                "settings/v2/packages/scene.json",
                "workflow_runtime_evidence/scene_prefab_binding_evidence.json",
                "workflow_runtime_evidence/product_body_evidence.raw.json",
            ],
            "read_set": ["GameDesignSpec", "UIFlowGraph", "AssetStyleBible"],
            "requirement_ids": _category_ids(by_category, {"ui", "art", "design"}, fallback=all_req_ids),
            "risk_level": "high",
            "evidence": [
                "scene_prefab_binding_evidence",
                "actual Cocos scene files and prefab/component files referenced by evidence must exist in the same patch",
                "launch .scene must contain an actual runtime component instance object referenced from a cc.Node _components list, not only cc.CompPrefabInfo or text metadata",
                "assets/scripts/workflow-e2e-runtime-bridge.js project-provided playtest hook derived from runtime model state",
                "settings/v2/packages/scene.json must bind current-scene to the generated player-visible scene uuid",
                "workflow_runtime_evidence/scene_prefab_binding_evidence.json",
                "workflow_runtime_evidence/product_body_evidence.raw.json",
            ],
        },
        {
            "slug": "scene_input_feedback_binding",
            "title": "Bind scene input feedback and player-visible capture contract",
            "goal": (
                "Bind pointer/touch input feedback, invalid target feedback, drag-follow behavior, and the player-visible "
                "screenshot capture contract to the scene runtime."
            ),
            "write_set": [
                "assets/scripts/runtime/input/SceneInputFeedbackBinder.ts",
                "workflow_runtime_evidence/input_feedback_trace.json",
                "workflow_runtime_evidence/player_visible_screenshots.json",
            ],
            "read_set": [
                "GameDesignSpec",
                "InteractionMap",
                "TestOracleSpec",
                "workflow_runtime_evidence/scene_prefab_binding_evidence.json",
                "settings/v2/packages/scene.json",
                "assets/scene/**",
            ],
            "requirement_ids": _category_ids(by_category, {"performance", "ui", "design"}, fallback=all_req_ids),
            "risk_level": "high",
            "evidence": [
                "player_visible_screenshots",
                "input_feedback_trace",
                "assets/scripts/runtime/input/SceneInputFeedbackBinder.ts",
                "workflow_runtime_evidence/input_feedback_trace.json",
                "workflow_runtime_evidence/player_visible_screenshots.json",
                "input feedback evidence must reference the existing generated launch scene from workflow_runtime_evidence/scene_prefab_binding_evidence.json or settings/v2/packages/scene.json; do not invent assets/scene/WorkflowCommercialGame.scene",
            ],
        },
    ]
    slices.extend(_implementation_groups(by_category, all_req_ids))
    slices.append(
        {
            "slug": "ai_surrogate_playtest_quality_gate",
            "title": "Run AI surrogate playtest and generate repair findings",
            "goal": (
                "Run scripted, exploratory, persona, vision, design red-team, performance, device matrix, "
                "and regression playtests; produce quality scorecard and repair task-card findings."
            ),
            "write_set": ["state/ai_playtest/**", "state/task_cards/**"],
            "read_set": ["TestOracleSpec", "QualityRubric", "latest_build_artifacts"],
            "requirement_ids": all_req_ids,
            "risk_level": "medium",
            "evidence": ["ai_playtest_replays", "screenshots", "ai_quality_scorecard", "repair_task_card_batch"],
        }
    )
    return PhaseExecutionBlueprint(
        phase_id=f"{run_id}_{_safe_slug(phase_name)}",
        phase_name=phase_name,
        source_requirement_ids=all_req_ids,
        slices=slices,
    )


def compile_task_cards_from_phase_execution_blueprint(
    *,
    run_id: str,
    phase_name: str,
    spec: GameDesignSpec | dict[str, Any],
    blueprint: PhaseExecutionBlueprint | dict[str, Any],
    status: str = "draft",
) -> tuple[list[TaskCard], TaskCardCompileReport]:
    payload = spec.to_dict() if isinstance(spec, GameDesignSpec) else dict(spec)
    blueprint_payload = blueprint.to_dict() if isinstance(blueprint, PhaseExecutionBlueprint) else dict(blueprint)
    all_req_ids = [str(item) for item in payload.get("preserved_requirement_ids") or []]
    cards: list[TaskCard] = []
    for blueprint_slice in blueprint_payload.get("slices") or []:
        if not isinstance(blueprint_slice, dict):
            continue
        cards.append(
            _task_card(
                run_id=run_id,
                phase_name=phase_name,
                status=status,
                slug=str(blueprint_slice.get("slug") or "phase_slice"),
                title=str(blueprint_slice.get("title") or "Implement active phase slice"),
                goal=str(blueprint_slice.get("goal") or "Implement the active phase slice from the PhaseExecutionBlueprint."),
                write_set=_string_list(blueprint_slice.get("write_set")),
                read_set=_string_list(blueprint_slice.get("read_set")),
                requirement_ids=_string_list(blueprint_slice.get("requirement_ids")) or all_req_ids,
                risk_level=str(blueprint_slice.get("risk_level") or "high"),
                evidence=_string_list(blueprint_slice.get("evidence")),
                blueprint=blueprint_payload,
            )
        )
    covered = sorted(
        {
            str(req_id)
            for card in cards
            for req_id in (card.metadata.get("covered_requirement_ids") or [])
            if str(req_id).strip()
        }
    )
    missing = sorted(set(all_req_ids) - set(covered))
    blockers = []
    if not cards:
        blockers.append("phase_execution_blueprint_slices_missing")
    if missing:
        blockers.append("blueprint_requirement_coverage_missing")
    report = TaskCardCompileReport(
        go=not blockers,
        blockers=blockers,
        phase_id=str(blueprint_payload.get("phase_id") or ""),
        task_card_ids=[card.task_card_id for card in cards],
        covered_requirement_ids=covered,
        missing_requirement_ids=missing,
    )
    for card in cards:
        card.metadata["task_card_compile_report_schema"] = TASK_CARD_COMPILE_REPORT_SCHEMA
        card.metadata["task_card_compile_go"] = report.go
        card.metadata["task_card_compile_blockers"] = report.blockers
        card.metadata["missing_requirement_ids"] = report.missing_requirement_ids
    return cards, report


def game_task_card_generation_report(cards: list[TaskCard]) -> dict[str, Any]:
    return {
        "schema_version": GAME_PRODUCTION_TASK_CARD_SCHEMA,
        "task_card_count": len(cards),
        "task_card_ids": [card.task_card_id for card in cards],
        "covered_requirement_ids": sorted(
            {
                str(req_id)
                for card in cards
                for req_id in (card.metadata.get("covered_requirement_ids") or [])
                if str(req_id).strip()
            }
        ),
        "workflow_generated_product_proof_required": True,
        "codex_local_patch_repair_counts_as_product": False,
        "task_card_generation_source": "active_phase_execution_blueprint",
        "phase_execution_blueprint_required": True,
        "all_cards_blueprint_compiled": all(
            card.metadata.get("task_card_generation_source") == "active_phase_execution_blueprint"
            for card in cards
        ),
    }


def _task_card(
    *,
    run_id: str,
    phase_name: str,
    status: str,
    slug: str,
    title: str,
    goal: str,
    write_set: list[str],
    read_set: list[str],
    requirement_ids: list[str],
    risk_level: str,
    evidence: list[str],
    blueprint: dict[str, Any],
) -> TaskCard:
    return TaskCard(
        run_id=run_id,
        task_card_id=f"{run_id}_{slug}",
        title=title,
        description=goal,
        goal=goal,
        milestone="Universal Game Production Quality",
        phase_name=phase_name,
        write_set=write_set,
        read_set=["UNIVERSAL_GAME_PRODUCTION_AI_PLAYTEST_UPGRADE_PLAN_2026_05_03.md", *read_set],
        test_commands=[
            "python -m pytest tests/test_game_design_ir.py tests/test_ai_playtest_quality_gate.py tests/test_game_task_card_generation.py -q",
            "python -m infra.scripts.check_doc_links",
        ],
        expected_artifacts=_path_like_items([*write_set, *evidence]),
        acceptance_criteria=[
            "All covered source requirements are implemented or explicitly blocked",
            "Evidence comes from workflow worker execution, not Codex/local rescue",
            "AI surrogate playtest reports no unresolved P0/P1 findings",
        ],
        evidence_requirements=[
            *evidence,
            "fresh_worker_receipt",
            "changed_files",
            "passing_tests",
            *(["human_visible_cli_session"] if risk_level == "high" else []),
            *(["direct_provider_visible_cli_session"] if risk_level == "high" else []),
        ],
        blocking_conditions=[
            "requirement_coverage_missing",
            "browser_bridge_or_runtime_hook_counts_as_product_body",
            "codex_local_patch_repair_used_as_product_proof",
            "ai_surrogate_playtest_no_go",
        ],
        model_guidance=[
            "Use the GameDesignSpec and TestOracleSpec as the source of truth.",
            "Implement behavior and player-visible quality, not only feature flags or screenshots.",
            "For the Cocos commercial path, mutate the project root directly: use assets/scripts, assets/scene, assets/resources, and workflow_runtime_evidence rather than detached project/runtime folders.",
            "Cocos .scene artifacts must be real Cocos Creator serialized scene assets with cc.SceneAsset/cc.Scene entries; do not write contract-only JSON into a .scene file.",
            "Bind the generated player-visible scene as the launch scene: settings/v2/packages/scene.json current-scene must match the generated scene .meta uuid.",
            "A scene/component binding is only valid when a cc.Node _components list references an actual exported runtime component instance object (for example __type__ equal to the @ccclass name); cc.CompPrefabInfo, script path text, or evidence metadata alone is not a live component binding.",
            "The runtime controller must register with the project E2E bridge and expose a playtest-compatible runtime packet through window.__UNIVERSAL_GAME_E2E__ or window.__workflowE2ERuntimeBridge.",
            "Player-visible Chinese UI/localization artifacts must contain readable Simplified Chinese, not mojibake or escaped corrupted text.",
            "Do not write raw mojibake examples into product artifacts; if a scanner needs forbidden marker metadata, use ASCII marker names such as utf8_as_gbk_mojibake.",
            "Emit machine-readable runtime evidence JSON under workflow_runtime_evidence and keep it synchronized with the implemented Cocos scene/component bindings.",
            "Evidence-only references are invalid: every scene_path, prefab_path, component path, asset path, and runtime evidence path named in JSON must exist in the generated Cocos project.",
            "Do not write multiple JSON documents into one evidence file; each evidence artifact must be one valid JSON object.",
        ],
        risk_level=risk_level,
        execution_mode="same_project_patch",
        status=status,
        metadata={
            "schema_version": GAME_PRODUCTION_TASK_CARD_SCHEMA,
            "task_card_generation_source": "active_phase_execution_blueprint",
            "phase_execution_blueprint_schema": PHASE_EXECUTION_BLUEPRINT_SCHEMA,
            "phase_execution_blueprint_id": blueprint.get("phase_id"),
            "product_phase_candidate_schema": PRODUCT_PHASE_CANDIDATE_SCHEMA,
            "requirement_coverage_required": True,
            "required_requirement_ids": requirement_ids,
            "covered_requirement_ids": requirement_ids,
            "human_visible_cli_required": risk_level == "high",
            "execution_visibility_mode": "human_visible_cli_enforced" if risk_level == "high" else "headless_allowed",
            "control_plane_visibility": "resident" if risk_level == "high" else "headless",
            "provider_visibility": "direct_visible" if risk_level == "high" else "headless",
            "provider_output_mode": "human_readable" if risk_level == "high" else "machine_readable",
            "workflow_generated_product_required": True,
            "codex_local_patch_repair_counts_as_product": False,
        },
    )


def _safe_slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value)).strip("_") or "active_phase"


def _path_like_items(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        normalized = text.replace("\\", "/")
        if " " in normalized:
            continue
        if normalized == "workflow_commercial_feature_evidence.json":
            pass
        elif "/" not in normalized:
            continue
        if not normalized.startswith(
            (
                "assets/",
                "settings/",
                "workflow_runtime_evidence/",
                "player_visible_evidence/",
                "state/",
                "workflow_commercial_feature_evidence.json",
            )
        ):
            continue
        if text not in result:
            result.append(text)
    return result


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _category_ids(by_category: dict[str, list[str]], categories: set[str], *, fallback: list[str]) -> list[str]:
    values: list[str] = []
    for category in sorted(categories):
        values.extend(by_category.get(category, []))
    return values or list(fallback)


def _implementation_groups(by_category: dict[str, list[str]], all_req_ids: list[str]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    definitions = [
        {
            "categories": {"ui"},
            "slug": "player_visible_ui_flow",
            "title": "Implement localized player-visible UI flows",
            "goal": "Implement localized first-session UI, HUD, menus, modal states, layout, readable text, and target-platform interaction surfaces.",
            "write_set": [
                "assets/scripts/runtime/ui/CommercialHud.ts",
                "assets/scripts/runtime/ui/CommercialPanels.ts",
                "assets/resources/localization/zh-CN.json",
                "workflow_runtime_evidence/chinese_ui_panels_evidence.json",
                "workflow_runtime_evidence/ui_flow_state_trace.json",
            ],
            "read_set": ["UIFlowGraph", "InteractionMap"],
            "risk_level": "high",
            "evidence": [
                "localized_screenshots",
                "layout_overlap_report",
                "ui_flow_state_trace",
                "workflow_runtime_evidence/chinese_ui_panels_evidence.json must include chinese_ui_panels for hud_panel, shop_panel, gallery_panel, settings_panel, and failure_revive_panel with readable Simplified Chinese labels",
                "assets/resources/localization/zh-CN.json must contain readable Simplified Chinese player text, not mojibake",
                "assets/resources/localization/zh-CN.json",
                "workflow_runtime_evidence/chinese_ui_panels_evidence.json",
                "workflow_runtime_evidence/ui_flow_state_trace.json",
            ],
        },
        {
            "categories": {"art", "multimodal"},
            "slug": "art_animation_asset_direction",
            "title": "Implement non-placeholder art direction and animation feedback",
            "goal": "Implement coherent non-placeholder visual assets, animation feedback, effects, and asset bindings required by the source brief.",
            "write_set": [
                "assets/resources/commercial_assets/art/art_direction_manifest.json",
                "assets/resources/commercial_assets/art/board_cell_material.json",
                "assets/resources/commercial_assets/art/block_palette_set.json",
                "assets/resources/commercial_assets/art/feedback_text_tokens.json",
                "assets/resources/commercial_assets/art/reward_gallery_shards.json",
                "assets/scripts/runtime/effects/CommercialFeedbackAnimator.ts",
                "workflow_runtime_evidence/feedback_animation_evidence.json",
                "workflow_commercial_feature_evidence.json",
            ],
            "read_set": ["AssetStyleBible", "ContentMatrix"],
            "risk_level": "high",
            "evidence": [
                "asset_graph",
                "vision_review_screenshots",
                "animation_feedback_trace",
                "assets/scripts/runtime/effects/CommercialFeedbackAnimator.ts",
                "assets/resources/commercial_assets/art/art_direction_manifest.json",
                "assets/resources/commercial_assets/art/feedback_text_tokens.json must be valid JSON and contain readable Simplified Chinese feedback labels, not mojibake",
                "assets/resources/commercial_assets/art/block_palette_set.json and reward_gallery_shards.json must not contain mojibake in player-visible names or labels",
                "workflow_runtime_evidence/feedback_animation_evidence.json",
                "generatedArtAssets",
                "particleEffects",
            ],
        },
        {
            "categories": {"audio", "multimodal"},
            "slug": "audio_asset_manifest_generation",
            "title": "Generate commercial audio asset manifest",
            "goal": (
                "Generate the current game's BGM/SFX design sheet, commercial audio manifest, procedural or provider-backed "
                "audio bank, and machine-readable proof that the audio assets come from the active GameDesignSpec."
            ),
            "write_set": [
                "assets/resources/commercial_assets/audio/audio_design_sheet.json",
                "assets/resources/commercial_assets/audio/commercial_audio_manifest.json",
                "assets/resources/commercial_assets/audio/procedural_audio_bank.json",
                "workflow_runtime_evidence/audio_asset_manifest_evidence.json",
            ],
            "read_set": ["AudioDesignSheet", "AssetStyleBible", "GameDesignSpec"],
            "risk_level": "high",
            "evidence": [
                "workflow_runtime_evidence/audio_asset_manifest_evidence.json",
                "assets/resources/commercial_assets/audio/audio_design_sheet.json",
                "assets/resources/commercial_assets/audio/commercial_audio_manifest.json",
                "assets/resources/commercial_assets/audio/procedural_audio_bank.json",
            ],
        },
        {
            "categories": {"audio", "multimodal"},
            "slug": "runtime_audio_bgm_sfx_controls",
            "title": "Bind runtime BGM SFX mix and volume controls",
            "goal": (
                "Bind browser/engine runtime BGM, SFX trigger timing, mix state, mute/volume controls, audio errors, and "
                "player-visible audio feedback to the generated commercial audio asset manifest."
            ),
            "write_set": [
                "assets/scripts/runtime/audio/CommercialAudioRuntime.ts",
                "workflow_runtime_evidence/audio_feedback_polish_evidence.json",
                "workflow_commercial_feature_evidence.json",
            ],
            "read_set": [
                "AudioDesignSheet",
                "assets/resources/commercial_assets/audio/audio_design_sheet.json",
                "assets/resources/commercial_assets/audio/commercial_audio_manifest.json",
                "assets/resources/commercial_assets/audio/procedural_audio_bank.json",
            ],
            "risk_level": "high",
            "evidence": [
                "assets/scripts/runtime/audio/CommercialAudioRuntime.ts",
                "workflow_runtime_evidence/audio_feedback_polish_evidence.json",
                "workflow_commercial_feature_evidence.json",
                "bgm_sfx_trigger_trace",
                "volume_state_evidence",
                "audioPlaybackVerified",
                "bgmStarted",
                "sfxPlaybackVerified",
                "volumeToggleUsable",
            ],
        },
        {
            "categories": {"progression", "economy", "product"},
            "slug": "product_rules_progression_content_depth",
            "title": "Implement product rules progression and content depth",
            "goal": (
                "Implement brief-specific scoring, fail/win/revive rules, level objectives, rewards, unlocks, content matrix rows, "
                "and persistence required by the source brief."
            ),
            "write_set": [
                "assets/scripts/runtime/systems/CommercialRulesAndScoring.ts",
                "assets/scripts/runtime/systems/CommercialProgression.ts",
                "assets/scripts/runtime/save/CommercialSaveState.ts",
                "assets/resources/content/level_goal_matrix.json",
                "assets/resources/content/reward_gallery_matrix.json",
                "workflow_runtime_evidence/level_goal_evidence.json",
                "workflow_runtime_evidence/commercial_shop_skin_gallery_evidence.json",
                "workflow_runtime_evidence/product_depth_evidence.raw.json",
            ],
            "read_set": ["ContentMatrix", "StateModelContract"],
            "risk_level": "high",
            "evidence": [
                "content_matrix_state_proof",
                "progression_replay",
                "save_load_state_trace",
                "assets/resources/content/level_goal_matrix.json",
                "assets/resources/content/reward_gallery_matrix.json",
                "workflow_runtime_evidence/level_goal_evidence.json",
                "workflow_runtime_evidence/commercial_shop_skin_gallery_evidence.json",
            ],
        },
        {
            "categories": {"performance"},
            "slug": "performance_device_input_feel",
            "title": "Implement performance device and input-feel requirements",
            "goal": "Implement input latency, responsive device layouts, frame pacing, low-performance handling, and device-matrix behavior required by the brief.",
            "write_set": [
                "assets/scripts/runtime/input/InputFeelMetrics.ts",
                "assets/scripts/runtime/performance/DevicePerformanceProfile.ts",
                "workflow_runtime_evidence/input_polish_evidence.json",
                "workflow_runtime_evidence/performance_device_matrix.json",
            ],
            "read_set": ["InteractionMap", "TestOracleSpec"],
            "risk_level": "high",
            "evidence": [
                "device_matrix_report",
                "input_latency_report",
                "frame_pacing_report",
                "workflow_runtime_evidence/input_polish_evidence.json",
                "workflow_runtime_evidence/performance_device_matrix.json",
            ],
        },
    ]
    covered: set[str] = set()
    for definition in definitions:
        req_ids = _category_ids(by_category, set(definition["categories"]), fallback=[])
        if not req_ids:
            continue
        covered.update(req_ids)
        group = {key: value for key, value in definition.items() if key != "categories"}
        group["requirement_ids"] = req_ids
        groups.append(group)
    uncategorized = [req_id for req_id in all_req_ids if req_id not in covered and req_id not in _category_ids(by_category, {"mechanic", "rule", "design"}, fallback=[])]
    if uncategorized:
        groups.append(
            {
                "slug": "brief_specific_product_surface",
                "title": "Implement brief-specific product requirements",
                "goal": "Implement preserved source requirements that do not fit a standard game-production category, with direct evidence for each requirement id.",
                "write_set": [
                    "assets/scripts/runtime/brief/BriefSpecificRequirements.ts",
                    "assets/resources/content/brief_specific_content_matrix.json",
                    "assets/resources/commercial_assets/brief_specific_asset_bindings.json",
                    "workflow_runtime_evidence/brief_specific_requirement_evidence.json",
                    "workflow_commercial_feature_evidence.json",
                ],
                "read_set": ["GameDesignSpec", "QualityRubric", "TestOracleSpec"],
                "risk_level": "high",
                "evidence": [
                    "brief_specific_requirement_evidence",
                    "source_requirement_trace",
                    "assets/scripts/runtime/brief/BriefSpecificRequirements.ts",
                    "workflow_runtime_evidence/brief_specific_requirement_evidence.json",
                ],
                "requirement_ids": uncategorized,
            }
        )
    return groups
