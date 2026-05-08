from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.contributions.games.ai_playtest_execution import AI_PLAYTEST_EXECUTION_PACKET_SCHEMA
from packages.contributions.games.ai_playtest_quality import QUALITY_AREAS, REQUIRED_AI_PLAYTEST_MODES


def test_universal_game_cli_builds_design_ir_plan_and_db_task_cards(tmp_path: Path) -> None:
    brief = tmp_path / "brief.md"
    brief.write_text(
        "\n".join(
            [
                "# Sky Rail Runner",
                "Player jumps and slides through moving hazards.",
                "Coins unlock skins in a shop.",
                "BGM, jump SFX, and crash SFX must play at runtime.",
                "Mobile touch input must be responsive.",
            ]
        ),
        encoding="utf-8",
    )
    spec_path = tmp_path / "design_spec.json"

    design = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "universal-design-ir",
            "--title",
            "Sky Rail Runner",
            "--genre",
            "runner",
            "--source-path",
            str(brief),
            "--output-path",
            str(spec_path),
        ],
    )

    assert design.exit_code == 0
    design_payload = json.loads(design.stdout)
    assert design_payload["validation"]["go"] is True
    assert spec_path.exists()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    assert spec["source_material_policy"] == "no_delete_no_merge_no_rename_only_augment"
    assert set(spec["preserved_requirement_ids"]) == set(spec["input_requirement_ids"])

    playtest_path = tmp_path / "ai_playtest_plan.json"
    playtest = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "ai-playtest-plan",
            "--design-spec-path",
            str(spec_path),
            "--output-path",
            str(playtest_path),
        ],
    )

    assert playtest.exit_code == 0
    playtest_payload = json.loads(playtest.stdout)
    assert playtest_payload["validation"]["go"] is True
    assert set(playtest_payload["plan"]["modes"]) == REQUIRED_AI_PLAYTEST_MODES

    enrichment_path = tmp_path / "enrichment.json"
    enrichment_path.write_text(
        json.dumps(
            {
                "derived_requirements": [
                    {
                        "source_requirement_ids": [spec["input_requirement_ids"][0]],
                        "requirement": "Add runner first-jump timing oracle.",
                    }
                ],
                "test_oracle_spec": {"scripted_scenarios": ["first_jump_timing_path"]},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    enrich = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "design-ir-enrich",
            "--design-spec-path",
            str(spec_path),
            "--enrichment-path",
            str(enrichment_path),
            "--output-path",
            str(tmp_path / "enriched_spec.json"),
        ],
    )

    assert enrich.exit_code == 0
    enrich_payload = json.loads(enrich.stdout)
    assert enrich_payload["validation"]["go"] is True
    assert enrich_payload["design_spec"]["requirements"] == spec["requirements"]

    cards = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "production-task-cards",
            "--design-spec-path",
            str(spec_path),
            "--run-id",
            "run_universal_game_cli",
            "--phase-name",
            "Universal Game Production Quality And AI Playtest Architecture",
            "--write-db",
            "--export-path",
            str(tmp_path / "task_cards.md"),
        ],
    )

    assert cards.exit_code == 0
    cards_payload = json.loads(cards.stdout)
    assert cards_payload["quality"]["go_no_go"] == "GO"
    assert cards_payload["generation_report"]["task_card_count"] >= 4
    assert len(cards_payload["db"]["created_task_card_ids"]) == cards_payload["generation_report"]["task_card_count"]
    assert "Generated from the workflow task card database" in (tmp_path / "task_cards.md").read_text(encoding="utf-8")


def test_universal_game_cli_quality_gate_and_repair_cards(tmp_path: Path) -> None:
    evidence_path = tmp_path / "ai_evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "workflow_generated_product_go": True,
                "core_loop_playable": True,
                "first_session_flow_go": True,
                "requirement_fidelity_go": True,
                "ai_playtest_modes_run": sorted(REQUIRED_AI_PLAYTEST_MODES),
                "area_scores": dict(QUALITY_AREAS),
                "findings": [{"finding_id": "visual-1", "severity": "P2", "category": "visual"}],
                "screenshots": ["first.png", "success.png", "failure.png"],
                "replay_artifacts": ["boot.jsonl"],
                "visual_review_evidence": {
                    "visual_go": True,
                    "visual_quality_score": 90,
                    "screenshots_reviewed": ["first.png", "success.png", "failure.png"],
                    "blockers": [],
                },
                "audio_review_evidence": {
                    "audio_go": True,
                    "bgm_runtime_verified": True,
                    "sfx_runtime_verified": True,
                    "mix_go": True,
                    "blockers": [],
                },
                "engine_native_product_body": {
                    "engine": "cocos",
                    "product_body_mode": "engine_native",
                    "required_components": ["GameModel", "InputController", "AudioFeedbackController"],
                    "component_bindings": ["GameModel", "InputController", "AudioFeedbackController"],
                    "scene_or_prefab_bindings": ["main.scene"],
                    "semantic_trace_source": "engine_runtime_model_transition",
                    "runtime_state_authoritative": True,
                    "build_launch_evidence": {"go": True},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    quality = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "ai-quality-gate",
            "--evidence-path",
            str(evidence_path),
            "--output-path",
            str(tmp_path / "ai_quality_report.json"),
        ],
    )

    assert quality.exit_code == 0
    quality_payload = json.loads(quality.stdout)
    assert quality_payload["ai_surrogate_playtest_go"] is True
    assert quality_payload["governance"]["commercial_playable_go"] is False

    findings_path = tmp_path / "findings.json"
    findings_path.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "finding_id": "audio-p1",
                        "severity": "P1",
                        "category": "audio",
                        "title": "BGM missing during gameplay",
                        "requirement_ids": ["REQ-AUDIO-1"],
                        "replay_artifact_paths": ["replay/audio-p1.jsonl"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    repair = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "ai-repair-cards",
            "--findings-path",
            str(findings_path),
            "--run-id",
            "run_ai_repair_cli",
            "--phase-name",
            "AI Repair Phase",
            "--write-db",
        ],
    )

    assert repair.exit_code == 0
    repair_payload = json.loads(repair.stdout)
    assert repair_payload["generation_report"]["p0_p1_count"] == 1
    assert repair_payload["task_cards"][0]["metadata"]["execution_visibility_mode"] == "human_visible_cli_enforced"


def test_universal_game_cli_ai_no_go_repair_loop_materializes_worker_entries(tmp_path: Path) -> None:
    report_path = tmp_path / "ai_execution_report.json"
    report_path.write_text(
        json.dumps(
            {
                "go": False,
                "validation": {"blockers": ["input_latency_above_floor"]},
                "quality": {
                    "ai_surrogate_playtest_go": False,
                    "blockers": ["ai_quality_score_below_85"],
                    "blocking_findings": [
                        {
                            "finding_id": "audio-p1",
                            "severity": "P1",
                            "category": "audio",
                            "title": "BGM missing during gameplay",
                            "requirement_ids": ["REQ-AUDIO-1"],
                        }
                    ],
                },
                "quality_evidence": {
                    "requirement_ids": ["REQ-AUDIO-1"],
                    "replay_artifacts": ["replay/audio-p1.jsonl"],
                    "screenshots": ["screenshots/audio-p1.png"],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "ai-repair-loop",
            "--execution-report-path",
            str(report_path),
            "--run-id",
            "run_ai_repair_loop_cli",
            "--phase-name",
            "AI Repair Phase",
            "--write-db",
            "--task-card-dir",
            str(tmp_path / "worker_cards"),
            "--export-path",
            str(tmp_path / "repair_cards.md"),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["repair_required"] is True
    assert payload["quality"]["go_no_go"] == "GO"
    assert payload["loop"]["finding_count"] == 3
    assert len(payload["db"]["created_task_card_ids"]) == 3
    assert len(payload["worker_loop_entries"]) == 3
    first_entry = payload["worker_loop_entries"][0]
    assert first_entry["requires_human_visible_cli_window"] is True
    assert "--execute" in first_entry["command"]
    assert Path(first_entry["task_card_path"]).exists()


def test_universal_game_cli_execution_gate_checks_ai_playtest_artifacts(tmp_path: Path) -> None:
    mode_results = {}
    for mode in sorted(REQUIRED_AI_PLAYTEST_MODES):
        replay = tmp_path / f"{mode}.jsonl"
        screenshot = tmp_path / f"{mode}.png"
        state = tmp_path / f"{mode}_state.json"
        replay.write_text('{"event":"boot"}\n', encoding="utf-8")
        screenshot.write_bytes(b"png")
        state.write_text('{"state":"ok"}', encoding="utf-8")
        mode_results[mode] = {
            "status": "completed",
            "fresh_run": True,
            "replay_artifacts": [replay.as_posix()],
            "screenshots": [screenshot.as_posix()],
            "state_snapshots": [state.as_posix()],
            "findings": [],
            "console_errors": [],
            "page_errors": [],
        }
    packet_path = tmp_path / "execution_packet.json"
    packet_path.write_text(
        json.dumps(
            {
                "schema_version": AI_PLAYTEST_EXECUTION_PACKET_SCHEMA,
                "plan": {
                    "schema_version": "universal_ai_playtest_lab_plan_v1",
                    "modes": sorted(REQUIRED_AI_PLAYTEST_MODES),
                    "scripted_scenarios": ["boot"],
                    "vision_review_targets": ["first_screen"],
                    "device_matrix": ["desktop", "mobile_portrait"],
                    "requirement_ids": ["REQ-1"],
                },
                "workflow_generated_product_go": True,
                "core_loop_playable": True,
                "first_session_flow_go": True,
                "requirement_fidelity_go": True,
                "area_scores": dict(QUALITY_AREAS),
                "mode_results": mode_results,
                "scripted_scenario_results": [{"scenario": "boot", "status": "passed"}],
                "device_matrix_results": [
                    {"device": "desktop", "status": "passed"},
                    {"device": "mobile_portrait", "status": "passed"},
                ],
                "performance_metrics": {"min_fps": 60, "input_latency_ms": 50},
                "vision_review": {
                    "visual_go": True,
                    "visual_quality_score": 90,
                    "targets_checked": ["first_screen"],
                    "screenshots_reviewed": [next(iter(mode_results.values()))["screenshots"][0]],
                    "blockers": [],
                },
                "audio_review": {
                    "audio_go": True,
                    "bgm_runtime_verified": True,
                    "sfx_runtime_verified": True,
                    "mix_go": True,
                    "blockers": [],
                },
                "engine_native_product_body": {
                    "engine": "cocos",
                    "product_body_mode": "engine_native",
                    "required_components": ["GameModel", "InputController", "AudioFeedbackController"],
                    "component_bindings": ["GameModel", "InputController", "AudioFeedbackController"],
                    "scene_or_prefab_bindings": ["main.scene"],
                    "semantic_trace_source": "engine_runtime_model_transition",
                    "runtime_state_authoritative": True,
                    "build_launch_evidence": {"go": True},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "ai-playtest-execution-gate",
            "--packet-path",
            str(packet_path),
            "--output-path",
            str(tmp_path / "execution_report.json"),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["go"] is True
    assert payload["validation"]["artifact_existence_checked"] is True


def test_universal_game_cli_ai_playtest_run_writes_honest_no_go_without_browser_target(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "schema_version": "universal_ai_playtest_lab_plan_v1",
                "modes": sorted(REQUIRED_AI_PLAYTEST_MODES),
                "scripted_scenarios": ["boot"],
                "state_assertions": ["runtime_state_valid"],
                "vision_review_targets": ["first_screen"],
                "device_matrix": ["desktop", "mobile_portrait"],
                "requirement_ids": ["REQ-1"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "ai-playtest-run",
            "--plan-path",
            str(plan_path),
            "--output-dir",
            str(tmp_path / "ai_run"),
            "--output-path",
            str(tmp_path / "ai_run_summary.json"),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["go"] is False
    assert "ai_playtest_browser_target_missing" in payload["runner"]["browser_runner_blockers"]
    assert Path(payload["packet_path"]).exists()
    assert Path(payload["report_path"]).exists()
