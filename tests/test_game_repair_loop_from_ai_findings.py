from __future__ import annotations

from packages.core_domain.task_card_store import task_card_execution_eligibility, task_card_quality_report
from packages.contributions.games.ai_repair_loop import (
    build_repair_task_cards_from_ai_execution_report,
    build_repair_task_cards_from_ai_findings,
    findings_from_ai_execution_report,
    repair_task_card_batch_report,
)


def test_ai_findings_generate_requirement_covered_repair_task_cards() -> None:
    cards = build_repair_task_cards_from_ai_findings(
        run_id="universal_game_quality_20260503",
        phase_name="Universal Game Production Quality And AI Playtest Architecture",
        status="active",
        findings=[
            {
                "finding_id": "drag-latency-p1",
                "severity": "P1",
                "category": "device",
                "title": "Touch drag preview lags behind the player finger",
                "observed": "The touch preview trails the gesture and lands one cell away.",
                "expected": "The preview follows the gesture and lands on the intended target.",
                "reproduction": "Replay drag_latency_mobile.jsonl on mobile portrait viewport.",
                "requirement_ids": ["REQ-INPUT-001", "REQ-MOBILE-002"],
                "evidence_paths": ["output/playwright/drag_latency_mobile.png"],
                "replay_artifact_paths": ["output/replays/drag_latency_mobile.jsonl"],
            }
        ],
    )

    assert len(cards) == 1
    card = cards[0]
    assert card.risk_level == "high"
    assert card.metadata["human_visible_cli_required"] is True
    assert card.metadata["execution_visibility_mode"] == "human_visible_cli_enforced"
    assert card.metadata["covered_requirement_ids"] == ["REQ-INPUT-001", "REQ-MOBILE-002"]
    assert task_card_execution_eligibility(card)["execution_eligible"] is True


def test_ai_repair_batch_report_summarizes_p0_p1_and_requirement_coverage() -> None:
    cards = build_repair_task_cards_from_ai_findings(
        run_id="universal_game_quality_20260503",
        phase_name="Universal Game Production Quality And AI Playtest Architecture",
        status="active",
        findings=[
            {"finding_id": "audio-p0", "severity": "P0", "category": "audio", "requirement_ids": ["REQ-AUDIO-001"]},
            {"finding_id": "visual-p3", "severity": "P3", "category": "visual", "requirement_ids": ["REQ-ART-001"]},
        ],
    )

    report = repair_task_card_batch_report(cards)
    quality = task_card_quality_report(cards)

    assert report["task_card_count"] == 2
    assert report["p0_p1_count"] == 1
    assert report["covered_requirement_ids"] == ["REQ-ART-001", "REQ-AUDIO-001"]
    assert quality["go_no_go"] == "GO"


def test_ai_no_go_execution_report_generates_visible_repair_loop_cards() -> None:
    report = {
        "go": False,
        "validation": {"blockers": ["input_latency_above_floor"]},
        "quality": {
            "ai_surrogate_playtest_go": False,
            "blockers": ["ai_quality_score_below_85"],
            "blocking_findings": [
                {
                    "finding_id": "drag-latency-p1",
                    "severity": "P1",
                    "category": "device",
                    "title": "Drag input lands one cell away",
                    "requirement_ids": ["REQ-INPUT-001"],
                }
            ],
        },
        "quality_evidence": {
            "requirement_ids": ["REQ-INPUT-001"],
            "replay_artifacts": ["replays/drag_latency.jsonl"],
            "screenshots": ["screenshots/drag_latency.png"],
        },
    }

    findings = findings_from_ai_execution_report(report)
    cards = build_repair_task_cards_from_ai_execution_report(
        run_id="run_ai_no_go_repair",
        phase_name="AI Repair Phase",
        report=report,
        status="active",
    )
    quality = task_card_quality_report(cards)

    assert {finding["finding_id"] for finding in findings} == {
        "drag-latency-p1",
        "validation_input_latency_above_floor",
        "quality_ai_quality_score_below_85",
    }
    assert len(cards) == 3
    assert quality["go_no_go"] == "GO"
    assert all(card.metadata["execution_visibility_mode"] == "human_visible_cli_enforced" for card in cards)
