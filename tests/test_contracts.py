from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from packages.contracts import (
    Evidence,
    HandoffLite,
    Phase,
    PresetDefinition,
    ReviewDecision,
    ReviewVerdict,
    Run,
    RuntimeTask,
    TaskCard,
    TaskKind,
    TaskPacket,
)
from packages.core_domain import PresetNotFoundError, PresetRequiredError, PresetResolver, load_seed_presets


def test_wave1_contracts_round_trip() -> None:
    run = Run(goal="Build the first bootstrap artifact.", preset_id="feature_delivery")
    phase = Phase(run_id=run.run_id, name="bootstrap", order_index=0)
    task_card = TaskCard(
        run_id=run.run_id,
        title="Create a bootstrap artifact",
        description="Generate the first task instructions.",
        acceptance_criteria=["artifact exists"],
    )
    runtime_task = RuntimeTask(
        run_id=run.run_id,
        phase_id=phase.phase_id,
        task_card_id=task_card.task_card_id,
        task_kind=TaskKind.shell_exec,
        summary="Generate a markdown artifact",
    )
    packet = TaskPacket(
        runtime_task_id=runtime_task.runtime_task_id,
        run_id=run.run_id,
        task_kind=TaskKind.shell_exec,
        command=["python", "-c", "print('ok')"],
        working_directory=".",
    )
    evidence = Evidence(
        run_id=run.run_id,
        runtime_task_id=runtime_task.runtime_task_id,
        summary="Command completed successfully.",
        return_code=0,
        raw_execution={"stdout": "ok", "stderr": ""},
    )
    verdict = ReviewVerdict(
        run_id=run.run_id,
        evidence_id=evidence.evidence_id,
        decision=ReviewDecision.pass_,
        rationale="Return code is zero and stderr is empty.",
    )
    handoff = HandoffLite(
        run_id=run.run_id,
        from_phase_id=phase.phase_id,
        to_phase_id=phase.phase_id,
        summary="No handoff used in M0 runtime path.",
    )

    models = [run, phase, task_card, runtime_task, packet, evidence, verdict, handoff]
    for model in models:
        dumped = model.model_dump(mode="json")
        assert dumped["schema_version"] == "v1"
        assert dumped["created_at"]
        restored = type(model).model_validate(dumped)
        assert restored.model_dump(mode="json") == dumped


def test_review_verdict_defaults_to_auto_reviewer() -> None:
    verdict = ReviewVerdict(
        run_id="run_123",
        evidence_id="evidence_123",
        decision=ReviewDecision.pass_,
        rationale="looks good",
    )
    assert verdict.reviewer_type == "auto"


def test_preset_seed_file_parses() -> None:
    presets = load_seed_presets(Path("infra/seeds/presets.json"))
    assert {preset.preset_id for preset in presets} == {"feature_delivery", "research_spike"}
    for preset in presets:
        assert isinstance(preset, PresetDefinition)
        assert preset.default_budget_policy.timeout_seconds > 0


def test_manual_preset_selection_is_required_and_strict() -> None:
    resolver = PresetResolver()
    with pytest.raises(PresetRequiredError):
        resolver.manual_select(None)
    with pytest.raises(PresetNotFoundError):
        resolver.manual_select("missing")
    preset = resolver.manual_select("feature_delivery")
    assert preset.preset_id == "feature_delivery"


def test_budget_policy_value_domains_are_validated() -> None:
    with pytest.raises(ValidationError):
        PresetDefinition.model_validate(
            {
                "preset_id": "bad",
                "name": "Bad Preset",
                "description": "invalid budget policy",
                "allowed_task_kinds": ["shell_exec"],
                "default_review_policy": "auto_only",
                "default_budget_policy": {"max_retries": -1, "timeout_seconds": 0},
            }
        )
