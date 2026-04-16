from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from packages.contracts import (
    Evidence,
    HandoffLite,
    NON_TERMINAL_RUNTIME_GRAPH_STEPS,
    Phase,
    PresetSuggestion,
    PresetDefinition,
    ReviewDecision,
    ReviewVerdict,
    Run,
    RUN_STATUS_TRANSITIONS,
    RunStatus,
    RuntimeGraphStep,
    TERMINAL_RUNTIME_GRAPH_STEPS,
    RuntimeStateRef,
    RuntimeTask,
    TaskCard,
    TaskKind,
    TaskPacket,
    allowed_run_status_transitions,
    can_transition_run_status,
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
    state_ref = RuntimeStateRef(
        run_id=run.run_id,
        runtime_task_id=runtime_task.runtime_task_id,
        graph_step="compiled",
        state_payload={"entrypoint": "resume"},
    )
    suggestion = PresetSuggestion(preset_id="feature_delivery", score=10, reason="keyword match")

    models = [run, phase, task_card, runtime_task, packet, evidence, verdict, handoff, state_ref, suggestion]
    for model in models:
        dumped = model.model_dump(mode="json")
        if "schema_version" in dumped:
            assert dumped["schema_version"] == "v1"
        if "created_at" in dumped:
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


def test_run_status_supports_awaiting_review() -> None:
    run = Run(goal="await human review", preset_id="research_spike", status="awaiting_review")
    assert run.status == "awaiting_review"


def test_run_status_transition_matrix_is_explicit() -> None:
    assert can_transition_run_status("pending", "prepared") is True
    assert can_transition_run_status("prepared", "running") is True
    assert can_transition_run_status("running", "awaiting_review") is True
    assert can_transition_run_status("awaiting_review", "completed") is True
    assert can_transition_run_status("completed", "running") is False
    assert can_transition_run_status("failed", "prepared") is False
    assert can_transition_run_status("cancelled", "awaiting_review") is False
    assert {str(status) for status in allowed_run_status_transitions("prepared")} == {
        "prepared",
        "running",
        "cancelled",
    }
    assert {str(status) for status in RUN_STATUS_TRANSITIONS[RunStatus.awaiting_review]} == {
        "completed",
        "failed",
        "cancelled",
    }


def test_runtime_graph_step_terminality_is_explicit() -> None:
    assert RuntimeGraphStep.completed in TERMINAL_RUNTIME_GRAPH_STEPS
    assert RuntimeGraphStep.compiled in NON_TERMINAL_RUNTIME_GRAPH_STEPS

    state_ref = RuntimeStateRef(
        run_id="run_123",
        runtime_task_id="task_123",
        graph_step=RuntimeGraphStep.compiled,
        state_payload={"entrypoint": "resume"},
    )
    assert state_ref.is_terminal is False

    with pytest.raises(ValidationError):
        RuntimeStateRef(
            run_id="run_123",
            runtime_task_id="task_123",
            graph_step=RuntimeGraphStep.completed,
            state_payload={},
            is_terminal=False,
        )


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


def test_preset_suggestions_are_deterministic_and_explained() -> None:
    resolver = PresetResolver()
    suggestions = resolver.suggest("Research and compare implementation options")
    assert suggestions[0].preset_id == "research_spike"
    assert suggestions[0].score >= suggestions[1].score
    assert suggestions[0].reason

    fallback = resolver.suggest("General task")
    assert [item.preset_id for item in fallback] == ["feature_delivery", "research_spike"]
    assert all(item.reason for item in fallback)


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
