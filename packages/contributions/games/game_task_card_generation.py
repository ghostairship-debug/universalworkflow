from __future__ import annotations

from collections import defaultdict
from typing import Any

from packages.contracts import TaskCard
from packages.contributions.games.game_design_ir import GameDesignSpec


GAME_PRODUCTION_TASK_CARD_SCHEMA = "universal_game_production_task_cards_v1"


def build_game_production_task_cards_from_design_spec(
    *,
    run_id: str,
    phase_name: str,
    spec: GameDesignSpec | dict[str, Any],
    status: str = "draft",
) -> list[TaskCard]:
    payload = spec.to_dict() if isinstance(spec, GameDesignSpec) else dict(spec)
    requirements = payload.get("requirements") if isinstance(payload.get("requirements"), list) else []
    by_category: dict[str, list[str]] = defaultdict(list)
    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        by_category[str(requirement.get("category") or "design")].append(str(requirement.get("req_id")))
    all_req_ids = [str(item) for item in payload.get("preserved_requirement_ids") or []]
    cards: list[TaskCard] = []
    cards.append(
        _task_card(
            run_id=run_id,
            phase_name=phase_name,
            status=status,
            slug="runtime_state_core_loop",
            title="Implement engine-native runtime state and core loop",
            goal=(
                "Implement the authoritative runtime state, core player verbs, win/fail/retry transitions, "
                "save/load fields, and semantic traces defined by the GameDesignSpec."
            ),
            write_set=["project/runtime/gameplay/**", "project/runtime/model/**", "project/runtime/input/**"],
            read_set=["GameDesignSpec", "MechanicGraph", "StateModelContract", "InteractionMap"],
            requirement_ids=_category_ids(by_category, {"mechanic", "rule", "progression", "design"}, fallback=all_req_ids),
            risk_level="high",
            evidence=["engine_native_runtime_state", "semantic_model_transition_trace", "scripted_core_loop_replay"],
        )
    )
    for group in _implementation_groups(by_category, all_req_ids):
        cards.append(
            _task_card(
                run_id=run_id,
                phase_name=phase_name,
                status=status,
                slug=group["slug"],
                title=group["title"],
                goal=group["goal"],
                write_set=group["write_set"],
                read_set=group["read_set"],
                requirement_ids=group["requirement_ids"],
                risk_level=group["risk_level"],
                evidence=group["evidence"],
            )
        )
    cards.append(
        _task_card(
            run_id=run_id,
            phase_name=phase_name,
            status=status,
            slug="ai_surrogate_playtest_quality_gate",
            title="Run AI surrogate playtest and generate repair findings",
            goal=(
                "Run scripted, exploratory, persona, vision, design red-team, performance, device matrix, "
                "and regression playtests; produce quality scorecard and repair task-card findings."
            ),
            write_set=["state/ai_playtest/**", "state/task_cards/**"],
            read_set=["TestOracleSpec", "QualityRubric", "latest_build_artifacts"],
            requirement_ids=all_req_ids,
            risk_level="medium",
            evidence=["ai_playtest_replays", "screenshots", "ai_quality_scorecard", "repair_task_card_batch"],
        )
    )
    return cards


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
        ],
        risk_level=risk_level,
        execution_mode="same_project_patch",
        status=status,
        metadata={
            "schema_version": GAME_PRODUCTION_TASK_CARD_SCHEMA,
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
            "write_set": ["project/runtime/ui/**", "project/localization/**"],
            "read_set": ["UIFlowGraph", "InteractionMap"],
            "risk_level": "high",
            "evidence": ["localized_screenshots", "layout_overlap_report", "ui_flow_state_trace"],
        },
        {
            "categories": {"art"},
            "slug": "art_animation_asset_direction",
            "title": "Implement non-placeholder art direction and animation feedback",
            "goal": "Implement coherent non-placeholder visual assets, animation feedback, effects, and asset bindings required by the source brief.",
            "write_set": ["project/assets/**", "project/runtime/effects/**"],
            "read_set": ["AssetStyleBible", "ContentMatrix"],
            "risk_level": "high",
            "evidence": ["asset_graph", "vision_review_screenshots", "animation_feedback_trace"],
        },
        {
            "categories": {"audio"},
            "slug": "runtime_audio_bgm_sfx_mix",
            "title": "Implement runtime BGM SFX mix and volume controls",
            "goal": "Implement browser/engine runtime BGM, SFX, trigger timing, mix state, mute/volume controls, and audio error evidence.",
            "write_set": ["project/assets/audio/**", "project/runtime/audio/**"],
            "read_set": ["AudioDesignSheet"],
            "risk_level": "high",
            "evidence": ["runtime_audio_proof", "bgm_sfx_trigger_trace", "volume_state_evidence"],
        },
        {
            "categories": {"progression", "economy"},
            "slug": "progression_economy_content_depth",
            "title": "Implement progression economy and content depth",
            "goal": "Implement level/progression, rewards, unlocks, economy, inventory, content matrix rows, and persistence required by the source brief.",
            "write_set": ["project/content/**", "project/runtime/systems/**", "project/runtime/save/**"],
            "read_set": ["ContentMatrix", "StateModelContract"],
            "risk_level": "high",
            "evidence": ["content_matrix_state_proof", "progression_replay", "save_load_state_trace"],
        },
        {
            "categories": {"performance"},
            "slug": "performance_device_input_feel",
            "title": "Implement performance device and input-feel requirements",
            "goal": "Implement input latency, responsive device layouts, frame pacing, low-performance handling, and device-matrix behavior required by the brief.",
            "write_set": ["project/runtime/input/**", "project/runtime/performance/**", "project/runtime/ui/**"],
            "read_set": ["InteractionMap", "TestOracleSpec"],
            "risk_level": "high",
            "evidence": ["device_matrix_report", "input_latency_report", "frame_pacing_report"],
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
                "write_set": ["project/runtime/**", "project/content/**", "project/assets/**"],
                "read_set": ["GameDesignSpec", "QualityRubric", "TestOracleSpec"],
                "risk_level": "high",
                "evidence": ["brief_specific_requirement_evidence", "source_requirement_trace"],
                "requirement_ids": uncategorized,
            }
        )
    return groups
