from __future__ import annotations

import struct
from pathlib import Path

from packages.contributions.games.cocos.reference_quality import build_reference_quality_evidence
from packages.contributions.pipelines.commercial_game_evidence_contracts import build_commercial_final_gate_evidence


def test_reference_quality_rejects_sparse_candidate(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    candidate_dir = tmp_path / "candidate"
    reference_screens = _write_screens(reference_dir, "ref", count=3, pad=4096)
    candidate_screens = _write_screens(candidate_dir, "candidate", count=1, pad=512)
    reference = {
        "feature_coverage": {
            "board10x10": True,
            "threeCandidates": True,
            "skinBackgroundCollection": True,
            "levelSwitchingUi": True,
        },
        "score": 268,
        "events": [f"event_{index}" for index in range(19)],
        "open_panels": ["PausePanel"],
        "screenshots": [path.as_posix() for path in reference_screens],
    }
    candidate = {
        "feature_coverage": {"board10x10": True},
        "score": 40,
        "events": ["start_game", "place_candidate", "revive"],
        "open_panels": [],
        "screenshots": [path.as_posix() for path in candidate_screens],
    }

    evidence = build_reference_quality_evidence(
        candidate_playtest=candidate,
        reference_playtest=reference,
        candidate_project_dir=candidate_dir,
        reference_project_dir=reference_dir,
    )

    assert evidence["go"] is False
    assert "reference_quality_missing_features" in evidence["blockers"]
    assert "missing_reference_feature_skinBackgroundCollection" in evidence["blockers"]
    assert "reference_quality_score_below_reference" in evidence["blockers"]
    assert "reference_quality_event_count_below_reference" in evidence["blockers"]
    assert "reference_quality_open_panel_count_below_reference" in evidence["blockers"]
    assert "reference_quality_screenshot_count_below_reference" in evidence["blockers"]


def test_reference_quality_accepts_candidate_that_matches_reference(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    candidate_dir = tmp_path / "candidate"
    reference_screens = _write_screens(reference_dir, "ref", count=3, pad=1024)
    candidate_screens = _write_screens(candidate_dir, "candidate", count=3, pad=2048)
    reference = {
        "feature_coverage": {"board10x10": True, "levelSwitchingUi": True},
        "score": 268,
        "events": [f"event_{index}" for index in range(19)],
        "open_panels": ["PausePanel"],
        "screenshots": [path.as_posix() for path in reference_screens],
    }
    candidate = {
        "feature_coverage": {"board10x10": True, "levelSwitchingUi": True, "extraPolish": True},
        "score": 320,
        "events": [f"event_{index}" for index in range(21)],
        "open_panels": ["PausePanel"],
        "screenshots": [path.as_posix() for path in candidate_screens],
    }

    evidence = build_reference_quality_evidence(
        candidate_playtest=candidate,
        reference_playtest=reference,
        candidate_project_dir=candidate_dir,
        reference_project_dir=reference_dir,
    )

    assert evidence["go"] is True
    assert evidence["blockers"] == []


def test_final_gate_blocks_reference_quality_regression() -> None:
    go_contract = {"go": True, "blockers": [], "source": {}}
    gate = build_commercial_final_gate_evidence(
        technical_smoke_go=True,
        production_scaffold_go=True,
        require_commercial=True,
        require_cocos_ecosystem=False,
        require_live_agent_roles=False,
        require_human_player_review=False,
        asset_graph=go_contract,
        cocos_bridge_evidence=go_contract,
        same_project_patch_ledger=go_contract,
        build_ledger=go_contract,
        browser_playtest_ledger=go_contract,
        product_feature_depth_go=True,
        product_feature_blockers=[],
        live_role_provider_proof_go=False,
        human_player_review_go=False,
        gameplay_semantic_evidence=go_contract,
        product_body_evidence=go_contract,
        reference_quality_evidence={
            "go": False,
            "blockers": ["reference_quality_score_below_reference"],
            "source": {},
        },
    )

    assert gate["machine_evidence_go"] is False
    assert "reference_quality_score_below_reference" in gate["machine_blockers"]


def _write_screens(root: Path, stem: str, *, count: int, pad: int) -> list[Path]:
    root.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index in range(count):
        path = root / f"{stem}_{index}.png"
        path.write_bytes(_fake_png_bytes(390, 844, pad + index))
        paths.append(path)
    return paths


def _fake_png_bytes(width: int, height: int, pad: int) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x06\x00\x00\x00"
        + (b"x" * pad)
    )
