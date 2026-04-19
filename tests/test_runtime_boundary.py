from __future__ import annotations

import ast
from pathlib import Path

from packages.contracts import RuntimeStateRef
from packages.core_domain.errors import RuntimeGatewayExecutionError
from packages.runtime_langgraph.gateway import NullRuntimeGateway, OpenAIRuntimeGateway


class _FakeResponse:
    id = "resp_fake"
    output_text = "Outcome: create artifact Risk: stale assumptions Check: verify output file"


class _FakeResponses:
    def __init__(self):
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse()


class _FakeOpenAIClient:
    def __init__(self):
        self.responses = _FakeResponses()


def test_contracts_and_core_domain_do_not_import_langgraph() -> None:
    roots = [Path("packages/contracts"), Path("packages/core_domain")]
    for root in roots:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    assert all(alias.name != "langgraph" for alias in node.names)
                if isinstance(node, ast.ImportFrom) and node.module is not None:
                    assert node.module != "langgraph"


def test_runtime_gateway_state_is_lightweight() -> None:
    gateway = NullRuntimeGateway()
    state_ref = gateway.start("run_123", "task_123")
    assert isinstance(state_ref, RuntimeStateRef)
    assert state_ref.run_id == "run_123"
    assert state_ref.runtime_task_id == "task_123"
    assert isinstance(state_ref.graph_step, str)
    assert isinstance(state_ref.state_payload, dict)
    assert gateway.describe()["provider"] == "null"


def test_openai_runtime_gateway_generates_execution_brief_with_fake_client() -> None:
    fake_client = _FakeOpenAIClient()
    gateway = OpenAIRuntimeGateway(client=fake_client, model="gpt-5.4-mini")

    compiled_state = gateway.start("run_456", "task_456")
    compiled_state = RuntimeStateRef.model_validate(
        {
            **compiled_state.model_dump(mode="json"),
            "state_payload": {
                **compiled_state.state_payload,
                "goal": "Draft an execution note",
                "preset_id": "feature_delivery",
                "task_kind": "shell_exec",
                "expected_artifacts": ["state/artifacts/run_456_feature_delivery.md"],
            },
        }
    )
    resumed_state = gateway.resume(compiled_state)

    assert gateway.describe()["provider"] == "openai"
    assert resumed_state.state_payload["runtime_gateway_provider"] == "openai"
    assert resumed_state.state_payload["llm_model"] == "gpt-5.4-mini"
    assert resumed_state.state_payload["runtime_brief"].startswith("Outcome:")
    assert resumed_state.state_payload["context_budget"]["status"] == "ok"
    assert resumed_state.state_payload["context_budget"]["runtime_brief_prompt_chars"] > 0
    assert fake_client.responses.calls[0]["model"] == "gpt-5.4-mini"


def test_openai_runtime_gateway_rejects_over_budget_runtime_brief_prompt() -> None:
    fake_client = _FakeOpenAIClient()
    gateway = OpenAIRuntimeGateway(
        client=fake_client,
        model="gpt-5.4-mini",
        warn_input_chars=40,
        max_input_chars=60,
    )
    compiled_state = RuntimeStateRef.model_validate(
        {
            **gateway.start("run_big", "task_big").model_dump(mode="json"),
            "state_payload": {
                "goal": "x" * 200,
                "preset_id": "feature_delivery",
                "task_kind": "shell_exec",
                "expected_artifacts": ["state/artifacts/run_big.md"],
            },
        }
    )

    try:
        gateway.resume(compiled_state)
    except RuntimeGatewayExecutionError as exc:
        assert exc.details["context_budget"]["over_budget"] is True
    else:
        raise AssertionError("expected runtime gateway to reject an over-budget prompt")
