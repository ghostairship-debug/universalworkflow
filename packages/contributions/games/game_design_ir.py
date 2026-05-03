from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable


GAME_DESIGN_SPEC_SCHEMA = "universal_game_design_spec_v1"
SOURCE_MATERIAL_POLICY = "no_delete_no_merge_no_rename_only_augment"


@dataclass(frozen=True)
class RawSourceReceipt:
    source_id: str
    original_path: str | None
    sha256: str
    byte_count: int
    requirement_count: int


@dataclass(frozen=True)
class SourceRequirement:
    req_id: str
    source_id: str
    original_text: str
    normalized_requirement: str
    category: str
    priority: str
    acceptance_method: str
    role_owner: str
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DerivedRequirement:
    derived_id: str
    source_requirement_ids: list[str]
    requirement: str
    reason: str
    owner: str


@dataclass(frozen=True)
class GenreModel:
    genre: str
    camera: str
    target_platforms: list[str]
    session_length: str
    input_model: list[str]
    engine_constraints: list[str]


@dataclass(frozen=True)
class MechanicGraph:
    verbs: list[str]
    rules: list[str]
    resources: list[str]
    win_states: list[str]
    fail_states: list[str]
    progression_dependencies: list[str]


@dataclass(frozen=True)
class StateModelContract:
    authoritative_state_fields: list[str]
    transitions: list[str]
    invariants: list[str]
    save_fields: list[str]


@dataclass(frozen=True)
class InteractionMap:
    input_actions: list[str]
    hit_targets: list[str]
    cancellation_rules: list[str]
    invalid_action_feedback: list[str]
    accessibility_actions: list[str]


@dataclass(frozen=True)
class UIFlowGraph:
    screens: list[str]
    hud_elements: list[str]
    menus: list[str]
    modal_states: list[str]
    localization: list[str]


@dataclass(frozen=True)
class ContentMatrix:
    content_types: list[str]
    tuning_rows: list[str]
    progression_rows: list[str]
    reward_rows: list[str]


@dataclass(frozen=True)
class AssetStyleBible:
    visual_direction: str
    palette: list[str]
    typography: list[str]
    effects: list[str]
    asset_requirements: list[str]


@dataclass(frozen=True)
class AudioDesignSheet:
    bgm_loops: list[str]
    sfx_events: list[str]
    mix_rules: list[str]
    volume_controls: list[str]


@dataclass(frozen=True)
class QualityRubric:
    target_score: int
    p0_allowed: int
    p1_allowed: int
    required_areas: list[str]
    genre_specific_checks: list[str]


@dataclass(frozen=True)
class TestOracleSpec:
    scripted_scenarios: list[str]
    state_assertions: list[str]
    screenshot_expectations: list[str]
    performance_budgets: list[str]
    device_matrix: list[str]


@dataclass(frozen=True)
class GameDesignSpec:
    schema_version: str
    title: str
    source_material_policy: str
    source_count: int
    input_count: int
    requirement_count: int
    raw_source_receipts: list[RawSourceReceipt]
    input_requirement_ids: list[str]
    preserved_requirement_ids: list[str]
    omitted_requirement_ids: list[str]
    requirements: list[SourceRequirement]
    derived_requirements: list[DerivedRequirement]
    genre_model: GenreModel
    mechanic_graph: MechanicGraph
    state_model_contract: StateModelContract
    interaction_map: InteractionMap
    ui_flow_graph: UIFlowGraph
    content_matrix: ContentMatrix
    asset_style_bible: AssetStyleBible
    audio_design_sheet: AudioDesignSheet
    quality_rubric: QualityRubric
    test_oracle_spec: TestOracleSpec

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_game_design_spec(
    *,
    title: str,
    sources: Iterable[dict[str, Any]],
    genre: str = "unspecified",
    camera: str = "brief_defined",
    target_platforms: Iterable[str] | None = None,
    input_model: Iterable[str] | None = None,
    derived_requirements: Iterable[dict[str, Any]] | None = None,
) -> GameDesignSpec:
    """Build a game-agnostic, lossless design IR from source requirement chunks.

    `sources` is intentionally simple so callers can feed PDF/MD/DOCX-derived
    chunks without coupling this module to a specific intake pipeline.
    """

    source_list = list(sources)
    receipts: list[RawSourceReceipt] = []
    requirements: list[SourceRequirement] = []
    for source_index, source in enumerate(source_list, start=1):
        source_id = str(source.get("source_id") or f"source_{source_index:03d}")
        raw_text = str(source.get("raw_text") or source.get("content") or "")
        requirement_texts = _source_requirement_texts(source)
        raw_for_hash = raw_text or "\n".join(requirement_texts)
        receipts.append(
            RawSourceReceipt(
                source_id=source_id,
                original_path=_optional_str(source.get("original_path") or source.get("path")),
                sha256=_sha256(raw_for_hash),
                byte_count=len(raw_for_hash.encode("utf-8")),
                requirement_count=len(requirement_texts),
            )
        )
        for requirement_index, text in enumerate(requirement_texts, start=1):
            normalized = " ".join(str(text).split())
            req_id = str(source.get("req_id_prefix") or f"REQ-S{source_index:03d}") + f"-{requirement_index:04d}"
            category = classify_requirement(normalized)
            requirements.append(
                SourceRequirement(
                    req_id=req_id,
                    source_id=source_id,
                    original_text=str(text),
                    normalized_requirement=normalized,
                    category=category,
                    priority=_priority_for_requirement(normalized),
                    acceptance_method=_acceptance_for_category(category),
                    role_owner=_owner_for_category(category),
                    tags=_tags_for_requirement(normalized),
                )
            )
    input_ids = [requirement.req_id for requirement in requirements]
    derived = [
        DerivedRequirement(
            derived_id=str(item.get("derived_id") or f"DERIVED-{index:04d}"),
            source_requirement_ids=[str(req_id) for req_id in item.get("source_requirement_ids") or []],
            requirement=str(item.get("requirement") or ""),
            reason=str(item.get("reason") or "engineering augmentation"),
            owner=str(item.get("owner") or "technical_plan_agent"),
        )
        for index, item in enumerate(list(derived_requirements or []), start=1)
    ]
    tags = {tag for requirement in requirements for tag in requirement.tags}
    return GameDesignSpec(
        schema_version=GAME_DESIGN_SPEC_SCHEMA,
        title=title,
        source_material_policy=SOURCE_MATERIAL_POLICY,
        source_count=len(source_list),
        input_count=len(source_list),
        requirement_count=len(requirements),
        raw_source_receipts=receipts,
        input_requirement_ids=input_ids,
        preserved_requirement_ids=list(input_ids),
        omitted_requirement_ids=[],
        requirements=requirements,
        derived_requirements=derived,
        genre_model=GenreModel(
            genre=genre,
            camera=camera,
            target_platforms=list(target_platforms or ["mobile", "desktop"]),
            session_length="brief_defined",
            input_model=list(input_model or _input_model_from_tags(tags)),
            engine_constraints=["engine_native_runtime_required", "browser_bridge_inspection_only"],
        ),
        mechanic_graph=MechanicGraph(
            verbs=_values_for_tags(tags, _VERB_BY_TAG, fallback=["brief_defined_player_verbs"]),
            rules=[requirement.normalized_requirement for requirement in requirements if requirement.category in {"mechanic", "rule"}],
            resources=[requirement.normalized_requirement for requirement in requirements if requirement.category == "economy"],
            win_states=[requirement.normalized_requirement for requirement in requirements if "win_state" in requirement.tags],
            fail_states=[requirement.normalized_requirement for requirement in requirements if "failure" in requirement.tags],
            progression_dependencies=[
                requirement.normalized_requirement for requirement in requirements if requirement.category == "progression"
            ],
        ),
        state_model_contract=StateModelContract(
            authoritative_state_fields=_values_for_tags(tags, _STATE_FIELD_BY_TAG, fallback=["brief_defined_runtime_state"]),
            transitions=_values_for_tags(tags, _TRANSITION_BY_TAG, fallback=["boot", "input", "state_update", "feedback"]),
            invariants=["all_must_requirements_preserved", "runtime_state_drives_semantic_trace"],
            save_fields=_values_for_tags(tags, _SAVE_FIELD_BY_TAG, fallback=["progression_state_when_required"]),
        ),
        interaction_map=InteractionMap(
            input_actions=_values_for_tags(tags, _INPUT_ACTION_BY_TAG, fallback=["brief_defined_inputs"]),
            hit_targets=["all_player_visible_controls", "primary_play_area"],
            cancellation_rules=["invalid_input_has_feedback", "modal_or_drag_cancel_supported"],
            invalid_action_feedback=["visual_feedback", "audio_or_haptic_feedback_when_available"],
            accessibility_actions=["readable_text", "tap_targets_sized_for_target_platform"],
        ),
        ui_flow_graph=UIFlowGraph(
            screens=_values_for_tags(tags, _SCREEN_BY_TAG, fallback=["title_or_boot", "gameplay", "pause", "failure_retry"]),
            hud_elements=_values_for_tags(tags, _HUD_BY_TAG, fallback=["objective", "status", "primary_feedback"]),
            menus=_values_for_tags(tags, _MENU_BY_TAG, fallback=["settings_or_pause"]),
            modal_states=["success", "failure", "confirmation_or_reward_when_required"],
            localization=["brief_language_required", "no_unlocalized_required_ui"],
        ),
        content_matrix=ContentMatrix(
            content_types=_values_for_tags(tags, _CONTENT_BY_TAG, fallback=["brief_defined_content"]),
            tuning_rows=["difficulty_curve", "reward_curve", "first_session_tuning"],
            progression_rows=["first_objective", "success_path", "failure_path", "next_action"],
            reward_rows=_values_for_tags(tags, _REWARD_BY_TAG, fallback=["brief_defined_rewards"]),
        ),
        asset_style_bible=AssetStyleBible(
            visual_direction="brief_defined_non_placeholder_art_direction",
            palette=["coherent_palette_required"],
            typography=["localized_readable_type"],
            effects=["state_change_feedback", "reward_feedback", "failure_feedback"],
            asset_requirements=["no_placeholder_only_required_surface", "style_consistency_required"],
        ),
        audio_design_sheet=AudioDesignSheet(
            bgm_loops=["runtime_bgm_loop_when_required"],
            sfx_events=["input_feedback", "success_feedback", "failure_feedback", "reward_feedback"],
            mix_rules=["volume_balance", "no_uncontrolled_autoplay_claim"],
            volume_controls=["mute", "volume_state_persisted_when_required"],
        ),
        quality_rubric=QualityRubric(
            target_score=85,
            p0_allowed=0,
            p1_allowed=0,
            required_areas=[
                "requirement_fidelity",
                "core_gameplay_correctness",
                "player_experience",
                "ui_ux_polish",
                "art_direction",
                "audio",
                "input_feel",
                "content_depth",
                "performance",
                "robustness",
            ],
            genre_specific_checks=["genre_model_defined", "brief_specific_oracles_defined"],
        ),
        test_oracle_spec=TestOracleSpec(
            scripted_scenarios=["boot_to_first_action", "success_path", "failure_retry_path", "settings_or_pause_path"],
            state_assertions=["must_requirements_implemented", "runtime_state_transitions_valid"],
            screenshot_expectations=["first_screen", "core_action", "success_feedback", "failure_feedback", "main_menu_or_pause"],
            performance_budgets=["load_time_budget", "input_latency_budget", "frame_pacing_budget"],
            device_matrix=["desktop", "mobile_portrait", "mobile_landscape_or_responsive_when_required"],
        ),
    )


def validate_game_design_spec(spec: GameDesignSpec | dict[str, Any]) -> dict[str, Any]:
    payload = spec.to_dict() if isinstance(spec, GameDesignSpec) else dict(spec)
    blockers: list[str] = []
    if payload.get("schema_version") != GAME_DESIGN_SPEC_SCHEMA:
        blockers.append("game_design_spec_schema_invalid")
    if payload.get("source_material_policy") != SOURCE_MATERIAL_POLICY:
        blockers.append("source_material_policy_invalid")
    input_ids = _string_list(payload.get("input_requirement_ids"))
    preserved_ids = _string_list(payload.get("preserved_requirement_ids"))
    omitted_ids = _string_list(payload.get("omitted_requirement_ids"))
    requirement_count = int(payload.get("requirement_count") or 0)
    requirements = payload.get("requirements") if isinstance(payload.get("requirements"), list) else []
    if payload.get("source_count") != payload.get("input_count"):
        blockers.append("source_count_input_count_mismatch")
    if requirement_count != len(requirements):
        blockers.append("requirement_count_mismatch")
    if set(input_ids) != set(preserved_ids):
        blockers.append("preserved_requirement_ids_incomplete")
    if omitted_ids:
        blockers.append("omitted_requirement_ids_block_execution")
    if any("10x10" in str(item).lower() for item in payload.get("genre_model", {}).values() if not isinstance(item, list)):
        blockers.append("design_specific_requirement_leaked_into_genre_model")
    receipts = payload.get("raw_source_receipts") if isinstance(payload.get("raw_source_receipts"), list) else []
    if not receipts:
        blockers.append("raw_source_receipts_missing")
    if any(not receipt.get("sha256") for receipt in receipts if isinstance(receipt, dict)):
        blockers.append("raw_source_hash_missing")
    return {
        "schema_version": "universal_game_design_spec_validation_v1",
        "go": not blockers,
        "blockers": blockers,
        "source_count": payload.get("source_count"),
        "requirement_count": requirement_count,
        "input_requirement_count": len(input_ids),
        "preserved_requirement_count": len(preserved_ids),
        "omitted_requirement_ids": omitted_ids,
    }


def validate_derived_semantic_enrichment(
    spec: GameDesignSpec | dict[str, Any],
    enrichment: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = spec.to_dict() if isinstance(spec, GameDesignSpec) else dict(spec)
    patch = enrichment if isinstance(enrichment, dict) else {}
    blockers: list[str] = []
    input_ids = _string_list(payload.get("input_requirement_ids"))
    preserved_ids = _string_list(payload.get("preserved_requirement_ids"))
    patch_input_ids = _string_list(patch.get("input_requirement_ids"))
    patch_preserved_ids = _string_list(patch.get("preserved_requirement_ids"))
    if patch.get("requirements") is not None:
        blockers.append("enrichment_cannot_replace_requirements")
    if _string_list(patch.get("omitted_requirement_ids")):
        blockers.append("enrichment_cannot_omit_requirements")
    if "input_requirement_ids" in patch and patch_input_ids != input_ids:
        blockers.append("enrichment_cannot_change_input_requirement_ids")
    if "preserved_requirement_ids" in patch and patch_preserved_ids != preserved_ids:
        blockers.append("enrichment_cannot_change_preserved_requirement_ids")
    known_ids = set(input_ids)
    for item in _dict_list(patch.get("derived_requirements")):
        source_ids = _string_list(item.get("source_requirement_ids"))
        if not source_ids:
            blockers.append("derived_requirement_source_ids_missing")
            continue
        missing = [req_id for req_id in source_ids if req_id not in known_ids]
        if missing:
            blockers.append("derived_requirement_references_unknown_source_requirement")
    return {
        "schema_version": "universal_game_design_semantic_enrichment_validation_v1",
        "go": not blockers,
        "blockers": list(dict.fromkeys(blockers)),
        "source_material_policy": SOURCE_MATERIAL_POLICY,
        "allowed_policy": "derived_only_no_source_requirement_mutation",
    }


def apply_derived_semantic_enrichment(
    spec: GameDesignSpec | dict[str, Any],
    enrichment: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = spec.to_dict() if isinstance(spec, GameDesignSpec) else dict(spec)
    patch = enrichment if isinstance(enrichment, dict) else {}
    validation = validate_derived_semantic_enrichment(payload, patch)
    if not validation["go"]:
        enriched = dict(payload)
        enriched["semantic_enrichment_validation"] = validation
        return enriched
    enriched = dict(payload)
    enriched["derived_requirements"] = [
        *(enriched.get("derived_requirements") or []),
        *_normalized_derived_requirements(patch.get("derived_requirements")),
    ]
    for section, field_names in {
        "quality_rubric": ["genre_specific_checks", "required_areas"],
        "test_oracle_spec": [
            "scripted_scenarios",
            "state_assertions",
            "screenshot_expectations",
            "performance_budgets",
            "device_matrix",
        ],
        "genre_model": ["engine_constraints", "input_model", "target_platforms"],
    }.items():
        target = dict(enriched.get(section) or {})
        source = patch.get(section) if isinstance(patch.get(section), dict) else {}
        for field_name in field_names:
            additions = _string_list(source.get(field_name))
            if additions:
                target[field_name] = _dedupe_strings([*_string_list(target.get(field_name)), *additions])
        enriched[section] = target
    enriched["semantic_enrichment_validation"] = validation
    return enriched


def classify_requirement(text: str) -> str:
    value = text.lower()
    if any(token in value for token in ["bgm", "sfx", "audio", "music", "音频", "音乐", "音效"]):
        return "audio"
    if any(token in value for token in ["ui", "hud", "menu", "panel", "中文", "界面", "按钮", "面板"]):
        return "ui"
    if any(token in value for token in ["level", "stage", "关卡", "progress", "unlock", "解锁"]):
        return "progression"
    if any(token in value for token in ["coin", "shop", "skin", "item", "economy", "金币", "商店", "皮肤", "道具"]):
        return "economy"
    if any(token in value for token in ["art", "asset", "sprite", "animation", "美术", "动效", "资产"]):
        return "art"
    if any(token in value for token in ["fps", "latency", "performance", "frame", "性能", "帧率", "延迟"]):
        return "performance"
    if any(token in value for token in ["place", "clear", "jump", "attack", "turn", "drag", "放置", "消除", "拖拽", "移动"]):
        return "mechanic"
    if any(token in value for token in ["fail", "game over", "revive", "失败", "复活"]):
        return "rule"
    return "design"


def _source_requirement_texts(source: dict[str, Any]) -> list[str]:
    requirements = source.get("requirements")
    if isinstance(requirements, list):
        return [str(item) for item in requirements if str(item).strip()]
    raw_text = str(source.get("raw_text") or source.get("content") or "")
    return [line.strip(" -\t") for line in raw_text.splitlines() if line.strip(" -\t")]


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _normalized_derived_requirements(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, item in enumerate(_dict_list(value), start=1):
        result.append(
            {
                "derived_id": str(item.get("derived_id") or f"DERIVED-ENRICHED-{index:04d}"),
                "source_requirement_ids": _string_list(item.get("source_requirement_ids")),
                "requirement": str(item.get("requirement") or ""),
                "reason": str(item.get("reason") or "derived semantic enrichment"),
                "owner": str(item.get("owner") or "semantic_enrichment_agent"),
            }
        )
    return result


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _priority_for_requirement(text: str) -> str:
    value = text.lower()
    if any(token in value for token in ["must", "required", "必须", "不得", "不能", "no-go", "失败"]):
        return "must"
    return "should"


def _acceptance_for_category(category: str) -> str:
    return {
        "audio": "runtime_audio_and_mix_evidence",
        "ui": "player_visible_screenshot_and_layout_review",
        "progression": "state_transition_and_scenario_playtest",
        "economy": "state_transition_and_persistence_test",
        "art": "asset_graph_and_vision_review",
        "performance": "performance_budget_measurement",
        "mechanic": "scripted_playtest_and_state_assertion",
        "rule": "semantic_rule_oracle",
        "design": "source_requirement_review",
    }.get(category, "source_requirement_review")


def _owner_for_category(category: str) -> str:
    return {
        "audio": "audio_designer_agent",
        "ui": "ux_reviewer_agent",
        "progression": "gameplay_designer_agent",
        "economy": "systems_designer_agent",
        "art": "art_director_agent",
        "performance": "performance_agent",
        "mechanic": "gameplay_engineer_agent",
        "rule": "gameplay_engineer_agent",
    }.get(category, "product_designer_agent")


def _tags_for_requirement(text: str) -> list[str]:
    value = text.lower()
    tags: set[str] = set()
    keyword_tags = {
        "drag": ["drag", "拖拽", "拖动"],
        "touch": ["touch", "tap", "点击", "触摸"],
        "keyboard": ["keyboard", "键盘"],
        "audio": ["bgm", "sfx", "music", "audio", "音频", "音乐", "音效"],
        "shop": ["shop", "商店"],
        "skin": ["skin", "皮肤"],
        "gallery": ["gallery", "collection", "画廊", "收集"],
        "level": ["level", "stage", "关卡"],
        "failure": ["fail", "game over", "失败", "无处可放"],
        "revive": ["revive", "复活"],
        "clear": ["clear", "消除"],
        "placement": ["place", "placement", "放置"],
        "save": ["save", "localstorage", "存档", "保存"],
        "ui": ["ui", "hud", "界面", "面板"],
    }
    for tag, tokens in keyword_tags.items():
        if any(token in value for token in tokens):
            tags.add(tag)
    return sorted(tags)


def _input_model_from_tags(tags: set[str]) -> list[str]:
    result = []
    if {"drag", "touch"} & tags:
        result.append("touch_pointer")
    if "keyboard" in tags:
        result.append("keyboard")
    return result or ["brief_defined_input"]


def _values_for_tags(tags: set[str], mapping: dict[str, str], *, fallback: list[str]) -> list[str]:
    values = [mapping[tag] for tag in sorted(tags) if tag in mapping]
    return values or list(fallback)


_VERB_BY_TAG = {
    "drag": "drag",
    "placement": "place",
    "clear": "clear",
    "revive": "revive",
    "shop": "purchase_or_equip",
    "level": "select_or_progress_level",
}
_STATE_FIELD_BY_TAG = {
    "level": "level_progress",
    "shop": "owned_items",
    "skin": "equipped_skin",
    "gallery": "collection_progress",
    "audio": "audio_state",
    "save": "save_data",
    "failure": "failure_state",
}
_TRANSITION_BY_TAG = {
    "drag": "drag_start_move_release",
    "placement": "attempt_place",
    "clear": "resolve_clear_or_success",
    "failure": "enter_failure_state",
    "revive": "revive_from_failure",
    "level": "advance_or_select_level",
    "shop": "purchase_or_equip_item",
}
_SAVE_FIELD_BY_TAG = {
    "level": "unlocked_level",
    "shop": "owned_items",
    "skin": "equipped_skin",
    "gallery": "collection_progress",
    "audio": "audio_preferences",
}
_INPUT_ACTION_BY_TAG = {
    "drag": "drag_pointer_or_touch",
    "touch": "tap_or_touch",
    "keyboard": "keyboard_control",
}
_SCREEN_BY_TAG = {
    "shop": "shop_screen",
    "skin": "skin_screen",
    "gallery": "collection_screen",
    "level": "level_select_screen",
    "failure": "failure_retry_screen",
}
_HUD_BY_TAG = {
    "level": "objective_progress",
    "audio": "audio_state",
    "shop": "currency_or_inventory_state",
    "gallery": "collection_progress",
}
_MENU_BY_TAG = {
    "shop": "shop_menu",
    "skin": "skin_menu",
    "gallery": "gallery_menu",
    "level": "level_menu",
    "audio": "audio_settings",
}
_CONTENT_BY_TAG = {
    "level": "levels",
    "shop": "shop_items",
    "skin": "skins",
    "gallery": "collectibles",
}
_REWARD_BY_TAG = {
    "clear": "success_reward",
    "level": "level_reward",
    "shop": "economy_reward",
    "gallery": "collection_reward",
}
