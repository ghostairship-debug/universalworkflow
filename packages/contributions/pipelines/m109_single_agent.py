from __future__ import annotations

from packages.contracts import PipelineStage, PipelineStageKind, TaskKind


REAL_COMMERCIAL_GAME_PIPELINE_ID = "commercial_game_production"


def commercial_game_production_stages(pipeline_id: str = REAL_COMMERCIAL_GAME_PIPELINE_ID) -> list[PipelineStage]:
    intake = _role_stage(
        name="Unified brief intake agent",
        order_index=0,
        goal="Build or consume the unified project brief and agent packets without lossy summarization.",
        role_id="intake_packaging_agent",
        pipeline_id=pipeline_id,
    )
    product = _role_stage(
        name="Product gameplay agent",
        order_index=1,
        goal="Define gameplay goals, player loop, level flow, and acceptance outline from the unified brief.",
        role_id="product_gameplay_agent",
        pipeline_id=pipeline_id,
        depends_on=[intake.stage_id],
        specialization="product_vision_and_player_loop",
    )
    mechanics = _role_stage(
        name="Mechanics system designer agent",
        order_index=2,
        goal="Derive mechanic rules, moment-to-moment feel, fail/revive logic, and state invariants from the unified brief.",
        role_id="mechanics_system_designer_agent",
        pipeline_id=pipeline_id,
        depends_on=[product.stage_id],
        specialization="mechanics_rules_and_input_feel",
    )
    level_economy = _role_stage(
        name="Level and economy designer agent",
        order_index=3,
        goal="Design level objectives, difficulty curve, unlock pacing, rewards, economy sinks, and retention loops.",
        role_id="level_economy_designer_agent",
        pipeline_id=pipeline_id,
        depends_on=[mechanics.stage_id],
        specialization="level_pacing_economy_and_rewards",
    )
    ui = _role_stage(
        name="UI flow agent",
        order_index=4,
        goal="Define screens, panels, interactions, mobile UX, and player feedback requirements.",
        role_id="ui_experience_agent",
        pipeline_id=pipeline_id,
        depends_on=[product.stage_id],
        specialization="screen_flow_and_hud_structure",
    )
    ui_polish = _role_stage(
        name="UI UX polish agent",
        order_index=5,
        goal="Refine player journey, control ergonomics, readability, accessibility, commercial UI polish, and screenshot quality standards.",
        role_id="ui_ux_polish_agent",
        pipeline_id=pipeline_id,
        depends_on=[ui.stage_id, mechanics.stage_id],
        specialization="commercial_ui_ux_polish",
    )
    art_direction = _role_stage(
        name="Art direction agent",
        order_index=6,
        goal="Define visual style bible, palette, iconography, board materials, character or theme assets, and non-placeholder asset acceptance.",
        role_id="art_direction_agent",
        pipeline_id=pipeline_id,
        depends_on=[ui_polish.stage_id, level_economy.stage_id],
        specialization="aesthetic_style_bible_and_asset_graph",
    )
    animation_vfx = _role_stage(
        name="Animation and VFX feedback agent",
        order_index=7,
        goal="Design motion grammar, success/failure feedback, effects timing, transition feel, and animation evidence requirements.",
        role_id="animation_vfx_feedback_agent",
        pipeline_id=pipeline_id,
        depends_on=[art_direction.stage_id, mechanics.stage_id],
        specialization="motion_vfx_and_feedback_readability",
    )
    audio_feedback = _role_stage(
        name="Audio feedback designer agent",
        order_index=8,
        goal="Design BGM mood, SFX event map, mix rules, volume controls, and audio-runtime evidence requirements.",
        role_id="audio_feedback_designer_agent",
        pipeline_id=pipeline_id,
        depends_on=[mechanics.stage_id, ui_polish.stage_id],
        specialization="music_sfx_mix_and_event_feedback",
    )
    tech = _role_stage(
        name="Technical plan agent",
        order_index=9,
        goal="Define Cocos implementation boundaries, write sets, test plan, and integration risks.",
        role_id="technical_plan_agent",
        pipeline_id=pipeline_id,
        depends_on=[
            mechanics.stage_id,
            level_economy.stage_id,
            ui_polish.stage_id,
            art_direction.stage_id,
            animation_vfx.stage_id,
            audio_feedback.stage_id,
        ],
        specialization="cocos_runtime_integration_and_evidence",
    )
    multimodal = _role_stage(
        name="Multimodal generation agent",
        order_index=10,
        goal="Define image, audio, music, and visual QA asset requirements and provider route expectations.",
        role_id="multimodal_generation_agent",
        pipeline_id=pipeline_id,
        depends_on=[art_direction.stage_id, animation_vfx.stage_id, audio_feedback.stage_id, tech.stage_id],
        specialization="provider_asset_generation_and_visual_review",
    )
    ai_playtest_oracle = _role_stage(
        name="AI playtest oracle agent",
        order_index=11,
        goal="Design player personas, scripted/exploratory playtest modes, screenshot/audio review rubrics, and repair-loop triggers.",
        role_id="ai_playtest_oracle_agent",
        pipeline_id=pipeline_id,
        depends_on=[mechanics.stage_id, level_economy.stage_id, ui_polish.stage_id, multimodal.stage_id],
        specialization="automated_player_qa_oracles",
    )
    task_cards = _role_stage(
        name="Task card generation agent",
        order_index=12,
        goal="Compile the specialist role outputs into high-quality task card inputs with read/write sets, tests, evidence, blockers, owner roles, and model guidance.",
        role_id="task_card_generation_agent",
        pipeline_id=pipeline_id,
        depends_on=[tech.stage_id, multimodal.stage_id, ai_playtest_oracle.stage_id],
        specialization="specialist_output_to_db_task_cards",
    )
    asset_generation = _capability_stage(
        name="Real asset generation handoff",
        order_index=13,
        goal="Generate or import the actual image, UI, audio, music, and review assets required by the task cards; placeholders must stay blockers.",
        capability="commercial_game_asset_generation",
        pipeline_id=pipeline_id,
        depends_on=[task_cards.stage_id],
        metadata={
            "planning_mode": "task_card_driven",
            "forbids_fixed_template": True,
            "requires_provider_evidence": True,
        },
    )
    implementation = _capability_stage(
        name="Task-card implementation worker",
        order_index=14,
        goal="Execute the DB-backed task cards against one persistent Cocos project. Do not generate a fixed-template game as the delivery.",
        capability="commercial_game_task_card_worker",
        pipeline_id=pipeline_id,
        depends_on=[asset_generation.stage_id],
        metadata={
            "planning_mode": "task_card_driven",
            "forbids_fixed_template": True,
            "requires_db_task_cards": True,
            "requires_incremental_repair": True,
        },
    )
    qa = _role_stage(
        name="QA player perspective agent",
        order_index=15,
        goal="Review generated evidence from a player-visible quality perspective and prepare repair findings.",
        role_id="qa_player_perspective_agent",
        pipeline_id=pipeline_id,
        depends_on=[implementation.stage_id],
        specialization="player_visible_quality_red_team",
    )
    supervisor = _role_stage(
        name="Supervisor decision agent",
        order_index=16,
        goal="Decide continue, repair, stop, or cluster upgrade based on QA, evidence, and gates.",
        role_id="supervisor",
        pipeline_id=pipeline_id,
        depends_on=[qa.stage_id],
        specialization="production_governance_and_repair_loop",
    )
    readiness_gate = PipelineStage(
        name="Real commercial readiness gate",
        stage_kind=PipelineStageKind.validation_gate,
        order_index=17,
        goal="Validate that the actual implemented game, not a fixed template scaffold, satisfies player-visible commercial readiness.",
        depends_on=[supervisor.stage_id],
        validation_commands=[],
        metadata={
            "planning_mode": "task_card_driven",
            "direct_mutation_allowed": False,
            "validation": "commercial_game_production_go_no_go",
            "pipeline_recipe": pipeline_id,
            "forbids_fixed_template": True,
        },
    )
    return [
        intake,
        product,
        mechanics,
        level_economy,
        ui,
        ui_polish,
        art_direction,
        animation_vfx,
        audio_feedback,
        tech,
        multimodal,
        ai_playtest_oracle,
        task_cards,
        asset_generation,
        implementation,
        qa,
        supervisor,
        readiness_gate,
    ]


def m109_single_agent_cocos_stages(template_id: str) -> list[PipelineStage]:
    return commercial_game_production_stages(template_id)


def _role_stage(
    *,
    name: str,
    order_index: int,
    goal: str,
    role_id: str,
    pipeline_id: str,
    depends_on: list[str] | None = None,
    specialization: str | None = None,
) -> PipelineStage:
    return PipelineStage(
        name=name,
        stage_kind=PipelineStageKind.agent_role,
        order_index=order_index,
        goal=goal,
        preset_id="advisory_delivery",
        task_kind=TaskKind.shell_exec,
        depends_on=list(depends_on or []),
        metadata={
            "planning_mode": "single_agent_role",
            "direct_mutation_allowed": False,
            "pipeline_recipe": pipeline_id,
            "role_executor": "single_agent_role_v1",
            "role_id": role_id,
            "role_kind": "single_agent",
            "role_specialization": specialization or role_id,
            "specialized_role_pipeline_version": "commercial_game_specialist_roles_v1",
            "forbids_fixed_template": True,
        },
    )


def _capability_stage(
    *,
    name: str,
    order_index: int,
    goal: str,
    capability: str,
    pipeline_id: str,
    depends_on: list[str],
    metadata: dict[str, object] | None = None,
) -> PipelineStage:
    return PipelineStage(
        name=name,
        stage_kind=PipelineStageKind.capability,
        order_index=order_index,
        goal=goal,
        preset_id="feature_delivery",
        task_kind=TaskKind.shell_exec,
        depends_on=list(depends_on),
        write_set=["state/pipeline_runs"],
        metadata={
            "planning_mode": str((metadata or {}).get("planning_mode") or "task_card_driven"),
            "capability": capability,
            "pipeline_recipe": pipeline_id,
            "forbids_fixed_template": True,
            **(metadata or {}),
        },
    )
