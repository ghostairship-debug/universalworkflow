from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path
import re
from types import SimpleNamespace

from packages.contracts import AgentRoleType, MutationContract, MutationMode, TaskKind, TaskPacket
from packages.core_domain.cluster_router import ClusterRouter
from packages.core_domain.db import migrate
from packages.core_domain.errors import WorkerAdapterUnavailableError
from packages.core_domain.interaction_catalog import list_default_cluster_templates
from packages.core_domain.repositories import PresetRepository
from packages.core_domain.services import OrchestratorService
from packages.worker_adapters.external_artifact_adapters import (
    ClaudeArchitectAdapter,
    MMXMultimodalAdapter,
    VertexMultimodalAdapter,
)
from packages.worker_adapters.codex_adapter import CodexAdapter
from packages.worker_adapters.langchain_agent_adapter import (
    LangChainAgentAdapter,
    resolve_langchain_agent_llm_selection,
)
from packages.worker_adapters.opencode_adapter import OpenCodeAdapter
from packages.worker_adapters.router import WorkerRouter
from packages.worker_adapters.shell_adapter import ShellAdapter
from packages.worker_adapters.subprocess_support import build_subprocess_env
from packages.worker_adapters.subprocess_support import run_subprocess_with_tree_timeout


def _fake_success_runner(command, cwd, env, capture_output, text, check, timeout):
    return subprocess.CompletedProcess(command, 0, stdout="生成的 evidence artifact\n", stderr="")


def _fake_timeout_runner(command, cwd, env, capture_output, text, check, timeout):
    raise subprocess.TimeoutExpired(command, timeout, output="partial stdout", stderr="partial stderr")


def _fake_failure_runner(command, cwd, env, capture_output, text, check, timeout):
    return subprocess.CompletedProcess(command, 2, stdout="", stderr="external adapter failed")


def _fake_empty_success_runner(command, cwd, env, capture_output, text, check, timeout):
    return subprocess.CompletedProcess(command, 0, stdout=None, stderr=None)


def _packet(tmp_path: Path, *, env: dict[str, str] | None = None, artifact: str = "evidence.md") -> TaskPacket:
    return TaskPacket(
        runtime_task_id="task_m41",
        run_id="run_m41",
        task_kind=TaskKind.shell_exec,
        command=[],
        working_directory=tmp_path.as_posix(),
        env={
            "WORKFLOW_RUN_GOAL": "评估 M41 dogfood 能力层",
            **(env or {}),
        },
        expected_artifacts=[artifact],
    )


def test_dogfood_strong_model_overrides_core_agent_models(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED", "1")
    monkeypatch.setenv("WORKFLOW_DOGFOOD_MODEL", "gpt-5.5")
    monkeypatch.setenv("WORKFLOW_DOGFOOD_REASONING_EFFORT", "xhigh")
    monkeypatch.delenv("WORKFLOW_CODEX_MODEL", raising=False)
    monkeypatch.delenv("WORKFLOW_DOGFOOD_CODEX_MODEL", raising=False)
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("M41 strong model dogfood compile", "feature_delivery")
    prepared = service.compile_run(run.run_id, adapter_name="codex")

    resolved = prepared.resolved_execution
    assert resolved.codex_model == "gpt-5.5"
    assert resolved.codex_reasoning_effort == "xhigh"
    assert resolved.agent_model == "gpt-5.5"
    assert resolved.runtime_gateway_model == "gpt-5.5"
    assert resolved.model_selection_source == "dogfood_strong_default"
    assert resolved.dogfood_strong_model_enabled is True
    assert prepared.task_packet.env["WORKFLOW_MODEL_SELECTION_SOURCE"] == "dogfood_strong_default"
    assert prepared.task_packet.env["WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED"] == "true"


def test_dogfood_codex_backend_routes_architecture_agent_roles_to_codex(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED", "1")
    monkeypatch.setenv("WORKFLOW_DOGFOOD_MODEL", "gpt-5.5")
    monkeypatch.setenv("WORKFLOW_DOGFOOD_REASONING_EFFORT", "xhigh")
    monkeypatch.delenv("WORKFLOW_CODEX_MODEL", raising=False)
    monkeypatch.delenv("WORKFLOW_DOGFOOD_CODEX_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)
    preset = service.preset_repo.get("project_delivery")
    assert preset is not None

    resolved = service._resolve_execution_profile_for_run(
        preset=preset,
        task_kind=preset.allowed_task_kinds[0],
        domain_pack=service._resolve_domain_pack(preset, preset.allowed_task_kinds[0]),
        cluster_template_id="architecture_delivery_cluster",
        cluster_member_id="architecture_delivery_design_planner",
        public_role=AgentRoleType.planner,
        role_label="planner_design",
    )

    assert resolved.adapter_name == "codex"
    assert resolved.selected_model == "gpt-5.5"
    assert resolved.model_selection_source == "dogfood_strong_codex_cli"
    assert resolved.dogfood_execution_backend == "codex_cli"
    assert resolved.source_map["adapter_name"]["original_value"] == "agent"
    assert "turn evidence into a design draft" in resolved.role_responsibilities


def test_dogfood_agent_lane_backend_preserves_agent_adapter(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED", "1")
    monkeypatch.setenv("WORKFLOW_DOGFOOD_EXECUTION_BACKEND", "agent_lane")
    monkeypatch.setenv("UAWO_ENABLE_AGENT_LANE", "1")
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)
    preset = service.preset_repo.get("project_delivery")
    assert preset is not None

    resolved = service._resolve_execution_profile_for_run(
        preset=preset,
        task_kind=preset.allowed_task_kinds[0],
        domain_pack=service._resolve_domain_pack(preset, preset.allowed_task_kinds[0]),
        cluster_template_id="architecture_delivery_cluster",
        cluster_member_id="architecture_delivery_design_planner",
        public_role=AgentRoleType.planner,
        role_label="planner_design",
    )

    assert resolved.adapter_name == "agent"
    assert resolved.model_selection_source == "dogfood_strong_default"
    assert resolved.dogfood_execution_backend == "agent_lane"


def test_external_artifact_adapters_write_artifacts_without_repo_mutation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_CLAUDE_ARCHITECT_ENABLED", "1")
    adapters = [
        ClaudeArchitectAdapter(runner=_fake_success_runner, executable=sys.executable),
        MMXMultimodalAdapter(runner=_fake_success_runner, executable=sys.executable),
    ]

    for adapter in adapters:
        packet = _packet(tmp_path, artifact=f"{adapter.adapter_name}.md")
        result = adapter.launch(packet)

        artifact_path = tmp_path / f"{adapter.adapter_name}.md"
        assert result.return_code == 0
        assert adapter.supports_mutation_mode("artifact_only") is True
        assert adapter.supports_mutation_mode("patch_apply") is False
        assert artifact_path.read_text(encoding="utf-8") == "生成的 evidence artifact\n"


def test_external_artifact_adapter_handles_empty_completed_streams(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_CLAUDE_ARCHITECT_ENABLED", "1")
    adapter = ClaudeArchitectAdapter(runner=_fake_empty_success_runner, executable=sys.executable)
    packet = _packet(tmp_path, artifact="claude-empty.md")

    result = adapter.launch(packet)

    payload = json.loads((tmp_path / "claude-empty.md").read_text(encoding="utf-8"))
    assert result.return_code == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert payload["status"] == "empty_output"


def test_mmx_multimodal_default_command_uses_minimax_openai_cli(tmp_path: Path) -> None:
    adapter = MMXMultimodalAdapter(executable=sys.executable)
    packet = _packet(tmp_path, artifact="mmx.md")

    command = adapter.build_command(packet)

    assert "run" not in command
    assert command[:3] == [sys.executable, "-m", "packages.worker_adapters.minimax_openai_cli"]
    assert command[command.index("--model") + 1] == "MiniMax-M2.7"
    assert command[command.index("--base-url") + 1] == "https://api.minimaxi.com/v1"
    assert "--prompt-path" in command


def test_claude_architect_quota_guard_blocks_second_call(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_CLAUDE_ARCHITECT_ENABLED", "1")
    adapter = ClaudeArchitectAdapter(runner=_fake_success_runner, executable=sys.executable)
    packet = _packet(
        tmp_path,
        env={"WORKFLOW_CLAUDE_ARCHITECT_CALL_COUNT": "1"},
        artifact="architecture_skeleton.md",
    )

    result = adapter.launch(packet)

    assert result.return_code == 1
    assert result.metadata["quota_guarded"] is True
    assert "max_calls_per_session=1" in result.stderr


def test_vertex_multimodal_requires_project_for_default_genai_command(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("WORKFLOW_VERTEX_COMMAND_TEMPLATE", raising=False)
    monkeypatch.delenv("WORKFLOW_VERTEX_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
    adapter = VertexMultimodalAdapter(runner=_fake_success_runner, executable=sys.executable)
    packet = _packet(tmp_path, artifact="vertex.md")

    try:
        adapter.launch(packet)
    except WorkerAdapterUnavailableError as exc:
        assert "GOOGLE_CLOUD_PROJECT" in str(exc)
    else:
        raise AssertionError("Vertex adapter should require a project before default live smoke")


def test_vertex_multimodal_default_command_uses_genai_cli(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_VERTEX_LOCATION", "global")
    adapter = VertexMultimodalAdapter(runner=_fake_success_runner, executable=sys.executable)
    packet = _packet(tmp_path, artifact="vertex.md")

    command = adapter.build_command(packet)

    assert command[:3] == [sys.executable, "-m", "packages.worker_adapters.vertex_genai_cli"]
    assert command[command.index("--project") + 1] == "test-project"
    assert command[command.index("--location") + 1] == "global"
    assert command[command.index("--model") + 1] == "gemini-2.5-flash"


def test_langchain_agent_reports_missing_provider_keys_for_strong_dogfood(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_TOKEN", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    adapter = LangChainAgentAdapter(model="gpt-5.5")
    packet = _packet(
        tmp_path,
        env={
            "WORKFLOW_AGENT_MODEL": "gpt-5.5",
            "WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED": "true",
        },
        artifact="agent.md",
    )

    try:
        adapter.launch(packet)
    except WorkerAdapterUnavailableError as exc:
        assert "MiniMax, DeepSeek, or OpenAI API key" in str(exc)
        assert exc.details["degraded_reason"]
    else:
        raise AssertionError("LangChain agent should report missing provider keys before dogfood execution")


def test_langchain_agent_extracts_content_from_ai_message_like_objects() -> None:
    adapter = LangChainAgentAdapter(model="gpt-5.5")
    ai_message = SimpleNamespace(content=[{"type": "text", "text": "object message artifact"}])

    content = adapter._extract_content({"messages": [ai_message]})

    assert content == "object message artifact"


def test_opencode_adapter_uses_tree_timeout_runner_for_cli_launch(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def _fake_tree_runner(command, cwd, env, capture_output, text, check, timeout):
        content_match = re.search(r"<<<WORKFLOW_FILE>>>\n(.*?)<<<END_WORKFLOW_FILE>>>", command[-1], re.DOTALL)
        assert content_match is not None
        calls.append(
            {
                "command": command,
                "cwd": cwd,
                "capture_output": capture_output,
                "text": text,
                "check": check,
                "timeout": timeout,
            }
        )
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"type": "text", "part": {"text": content_match.group(1)}}),
            stderr=None,
        )

    monkeypatch.setattr(
        "packages.worker_adapters.opencode_adapter.run_subprocess_with_tree_timeout",
        _fake_tree_runner,
    )
    adapter = OpenCodeAdapter(executable=sys.executable, model="minimax/MiniMax-M2.7")
    packet = _packet(tmp_path, artifact="opencode.md")

    result = adapter.launch(packet)

    assert calls
    assert calls[0]["timeout"] == adapter.timeout_seconds
    assert result.stderr == ""
    assert "adapter: opencode" in (tmp_path / "opencode.md").read_text(encoding="utf-8")


def test_opencode_adapter_rejects_artifact_only_output_mismatch(tmp_path: Path) -> None:
    def _drifting_runner(command, cwd, env, capture_output, text, check, timeout):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"type": "text", "part": {"text": "not the requested artifact"}}),
            stderr="",
        )

    adapter = OpenCodeAdapter(runner=_drifting_runner, executable=sys.executable, model="minimax/MiniMax-M2.7")
    packet = _packet(tmp_path, artifact="opencode.md")

    result = adapter.launch(packet)

    assert result.return_code == 1
    assert result.artifact_paths == []
    assert result.metadata["failure_class"] == "artifact_output_mismatch"
    assert "artifact-only output did not match expected content" in result.stderr
    assert not (tmp_path / "opencode.md").exists()


def test_opencode_adapter_accepts_exact_content_wrapped_in_markers(tmp_path: Path) -> None:
    def _marker_runner(command, cwd, env, capture_output, text, check, timeout):
        content_match = re.search(r"<<<WORKFLOW_FILE>>>\n(.*?)<<<END_WORKFLOW_FILE>>>", command[-1], re.DOTALL)
        assert content_match is not None
        wrapped = f"<<<WORKFLOW_FILE>>>\n{content_match.group(1)}<<<END_WORKFLOW_FILE>>>"
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"type": "text", "part": {"text": wrapped}}),
            stderr="",
        )

    adapter = OpenCodeAdapter(runner=_marker_runner, executable=sys.executable, model="minimax/MiniMax-M2.7")
    packet = _packet(tmp_path, artifact="opencode.md")

    result = adapter.launch(packet)

    assert result.return_code == 0
    assert "adapter: opencode" in (tmp_path / "opencode.md").read_text(encoding="utf-8")
    assert "<<<WORKFLOW_FILE>>>" not in (tmp_path / "opencode.md").read_text(encoding="utf-8")


def test_opencode_adapter_accepts_artifact_with_outer_whitespace(tmp_path: Path) -> None:
    def _whitespace_runner(command, cwd, env, capture_output, text, check, timeout):
        content_match = re.search(r"<<<WORKFLOW_FILE>>>\n(.*?)<<<END_WORKFLOW_FILE>>>", command[-1], re.DOTALL)
        assert content_match is not None
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"type": "text", "part": {"text": f"\n\n{content_match.group(1).rstrip()}\n\n"}}),
            stderr="",
        )

    adapter = OpenCodeAdapter(runner=_whitespace_runner, executable=sys.executable, model="minimax/MiniMax-M2.7")
    packet = _packet(tmp_path, artifact="opencode.md")

    result = adapter.launch(packet)

    assert result.return_code == 0
    assert (tmp_path / "opencode.md").read_text(encoding="utf-8").endswith("\n")
    assert (tmp_path / "opencode.md").read_text(encoding="utf-8").startswith("preset:")


def test_opencode_command_places_options_before_prompt(tmp_path: Path) -> None:
    adapter = OpenCodeAdapter(executable=sys.executable, model="minimax/MiniMax-M2.7")
    packet = _packet(tmp_path, artifact="opencode.md")

    command = adapter.build_command(packet)

    assert command[-1].startswith("You are executing a local workflow task")
    assert command.index("--model") < len(command) - 1
    assert command.index("--format") < len(command) - 1
    assert command.index("--dir") < len(command) - 1


def test_opencode_resolves_windows_npm_cmd_shim_to_node_script(tmp_path: Path, monkeypatch) -> None:
    npm_dir = tmp_path / "npm"
    script_path = npm_dir / "node_modules" / "opencode-ai" / "bin" / "opencode"
    shim_path = npm_dir / "opencode.CMD"
    node_path = tmp_path / "node.exe"
    script_path.parent.mkdir(parents=True)
    script_path.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    shim_path.write_text("@echo off\n", encoding="utf-8")
    node_path.write_text("", encoding="utf-8")

    def _fake_which(name: str):
        if name == "opencode":
            return str(shim_path)
        if name == "node":
            return str(node_path)
        return None

    monkeypatch.setattr("packages.worker_adapters.opencode_adapter.shutil.which", _fake_which)
    adapter = OpenCodeAdapter(executable="opencode", model="minimax/MiniMax-M2.7")
    packet = _packet(tmp_path, artifact="opencode.md")

    command = adapter.build_command(packet)

    assert command[:2] == [str(node_path), str(script_path)]


def test_langchain_agent_provider_selection_prefers_minimax_with_deepseek_fallback(monkeypatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-minimax")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek")
    monkeypatch.delenv("WORKFLOW_LANGCHAIN_AGENT_PROVIDER", raising=False)

    selection = resolve_langchain_agent_llm_selection()

    assert selection.provider == "minimax"
    assert selection.model == "MiniMax-M2.7"
    assert selection.fallback_provider == "deepseek"
    assert selection.fallback_model == "deepseek-v4-flash"


def test_codex_dogfood_artifact_prompt_contains_role_handoff_and_keeps_patch_prompt_separate(tmp_path: Path) -> None:
    artifact_packet = _packet(
        tmp_path,
        env={
            "WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED": "true",
            "WORKFLOW_DOGFOOD_EXECUTION_BACKEND": "codex_cli",
            "WORKFLOW_MODEL_SELECTION_SOURCE": "dogfood_strong_codex_cli",
            "WORKFLOW_ROLE_LABEL": "planner_design",
            "WORKFLOW_PUBLIC_ROLE": "planner",
            "WORKFLOW_CLUSTER_TEMPLATE_ID": "architecture_delivery_cluster",
            "WORKFLOW_CLUSTER_MEMBER_ID": "architecture_delivery_design_planner",
            "WORKFLOW_ROLE_RESPONSIBILITIES": json.dumps(["turn evidence into a design draft"]),
            "WORKFLOW_ORCHESTRATION_PLAN_GRAPH": '{"handoff_points":["planner_design","phase_designer"]}',
        },
        artifact="codex_artifact.md",
    )
    adapter = CodexAdapter(runner=_fake_success_runner, executable=sys.executable)

    artifact_command = adapter.build_command(artifact_packet)
    artifact_prompt = artifact_command[-1]

    assert "artifact-only workflow agent" in artifact_prompt
    assert "Role label: planner_design" in artifact_prompt
    assert "Responsibilities JSON" in artifact_prompt
    assert "Handoff context JSON" in artifact_prompt
    assert "<<<WORKFLOW_FILE>>>" not in artifact_prompt

    patch_packet = TaskPacket.model_validate(
        {
            **artifact_packet.model_dump(mode="json"),
            "mutation_contract": MutationContract(
                write_set=["target.txt"],
                mutation_mode=MutationMode.patch_apply,
            ).model_dump(mode="json"),
        }
    )
    patch_prompt = adapter.build_command(patch_packet)[-1]

    assert "Return only one valid unified diff patch" in patch_prompt
    assert "artifact-only workflow agent" not in patch_prompt


def test_codex_adapter_timeout_can_be_overridden_for_local_dogfood(monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_CODEX_TIMEOUT_SECONDS", "45")

    adapter = CodexAdapter(runner=_fake_success_runner, executable=sys.executable)

    assert adapter.timeout_seconds == 45


def test_codex_adapter_timeout_can_be_overridden_per_packet(tmp_path: Path, monkeypatch) -> None:
    observed: dict[str, int] = {}

    def _recording_runner(command, cwd, env, capture_output, text, check, timeout):
        observed["timeout"] = timeout
        return subprocess.CompletedProcess(command, 0, stdout="artifact\n", stderr="")

    monkeypatch.delenv("WORKFLOW_CODEX_TIMEOUT_SECONDS", raising=False)
    adapter = CodexAdapter(runner=_recording_runner, executable=sys.executable)
    packet = _packet(
        tmp_path,
        env={"WORKFLOW_CODEX_TIMEOUT_SECONDS": "12"},
        artifact="codex_timeout.md",
    )

    result = adapter.launch(packet)

    assert observed["timeout"] == 12
    assert result.metadata["timeout_seconds"] == 12


def test_subprocess_tree_timeout_returns_124_for_hung_cli(tmp_path: Path) -> None:
    command = [
        sys.executable,
        "-c",
        "import time; time.sleep(60)",
    ]

    completed = run_subprocess_with_tree_timeout(
        command,
        cwd=tmp_path.as_posix(),
        env={},
        capture_output=True,
        text=True,
        check=False,
        timeout=1,
    )

    assert completed.returncode == 124
    assert "command timed out after 1s" in completed.stderr


def test_subprocess_tree_timeout_decodes_utf8_stdout_when_text_requested(tmp_path: Path) -> None:
    command = [
        sys.executable,
        "-c",
        "import sys; sys.stdout.buffer.write('€ live'.encode('utf-8'))",
    ]

    completed = run_subprocess_with_tree_timeout(
        command,
        cwd=tmp_path.as_posix(),
        env={},
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert completed.returncode == 0
    assert completed.stdout == "€ live"


def test_subprocess_tree_timeout_encodes_utf8_stdin_when_text_requested(tmp_path: Path) -> None:
    command = [
        sys.executable,
        "-c",
        "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())",
    ]

    completed = run_subprocess_with_tree_timeout(
        command,
        cwd=tmp_path.as_posix(),
        env={},
        input="€ prompt",
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
        encoding="utf-8",
        errors="replace",
    )

    assert completed.returncode == 0
    assert completed.stdout == "€ prompt"


def test_codex_command_places_exec_options_before_prompt(tmp_path: Path) -> None:
    packet = _packet(
        tmp_path,
        env={
            "WORKFLOW_CODEX_MODEL": "gpt-5.4",
            "WORKFLOW_CODEX_REASONING_EFFORT": "xhigh",
        },
        artifact="codex_order.md",
    )
    adapter = CodexAdapter(runner=_fake_success_runner, executable=sys.executable)

    command = adapter.build_command(packet)
    stdin_command = adapter.build_command(packet, prompt_via_stdin=True)

    assert command[-1].startswith("You are executing a local workflow task")
    assert command.index("--model") < len(command) - 1
    assert command.index("-c") < len(command) - 1
    assert stdin_command[-1] == "-"
    assert stdin_command.index("--model") < len(stdin_command) - 1


def test_codex_command_creates_artifact_parent_directory(tmp_path: Path) -> None:
    packet = _packet(
        tmp_path,
        env={"WORKFLOW_CODEX_MODEL": "gpt-5.4"},
        artifact="nested/codex/artifact.md",
    )
    adapter = CodexAdapter(runner=_fake_success_runner, executable=sys.executable)

    adapter.build_command(packet)

    assert (tmp_path / "nested" / "codex").is_dir()


def test_codex_subprocess_env_preserves_codex_cli_context(monkeypatch) -> None:
    monkeypatch.setenv("CODEX_THREAD_ID", "thread-test")
    monkeypatch.setenv("CODEX_INTERNAL_ORIGINATOR_OVERRIDE", "Codex Desktop")

    env = build_subprocess_env()

    assert env["CODEX_THREAD_ID"] == "thread-test"
    assert env["CODEX_INTERNAL_ORIGINATOR_OVERRIDE"] == "Codex Desktop"


def test_architecture_delivery_cluster_is_suggested_for_m41_dogfood() -> None:
    templates = list_default_cluster_templates()
    template = next(item for item in templates if item.template_id == "architecture_delivery_cluster")
    labels = [member.role_label for member in template.member_specs]

    assert labels == [
        "multimodal_evidence",
        "planner_design",
        "claude_architect_gate",
        "phase_designer",
        "implementer",
        "quality_gate",
        "doc_curator",
        "launch_guard",
    ]
    assert ClusterRouter(templates).suggest_template_ids(goal="M41 架构 dogfood 多模态 Claude 接入") == [
        "architecture_delivery_cluster"
    ]


def test_architecture_delivery_launch_preview_projects_cluster_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    payload = service.launch_goal(
        goal="M41 架构 dogfood 多模态 Claude 接入",
        preferred_cluster_template_ids=["architecture_delivery_cluster"],
        execute=False,
    )
    detail = service.get_status_detail(payload["run"]["run_id"])

    assert payload["selected_clusters"][0]["template_id"] == "architecture_delivery_cluster"
    assert payload["cluster_policy_preview"]["selected_cluster_template_ids"] == ["architecture_delivery_cluster"]
    assert detail["selected_clusters"][0]["template_id"] == "architecture_delivery_cluster"
    assert detail["cluster_graph"]["cluster_template_ids"] == ["architecture_delivery_cluster"]
    assert payload["goal_packet"]["cluster_execution_plans"][0]["handoff_points"] == [
        "multimodal_evidence",
        "planner_design",
        "claude_architect_gate",
        "phase_designer",
        "implementer",
        "quality_gate",
        "doc_curator",
        "launch_guard",
    ]


def test_cluster_member_compile_does_not_embed_parent_orchestration_plan(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Compile a cluster member without recursive orchestration", "project_delivery")
    prepared = service.compile_run(
        run.run_id,
        cluster_template_id="architecture_delivery_cluster",
        cluster_member_id="architecture_delivery_design_planner",
        public_role=AgentRoleType.planner,
        role_label="planner_design",
    )

    assert prepared.task_packet.env["WORKFLOW_CLUSTER_TEMPLATE_ID"] == "architecture_delivery_cluster"
    assert prepared.task_packet.env["WORKFLOW_CLUSTER_MEMBER_ID"] == "architecture_delivery_design_planner"
    assert "WORKFLOW_ORCHESTRATION_PLAN" not in prepared.task_packet.env


def test_orchestration_rejects_failed_child_before_fallback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED", "1")
    monkeypatch.setenv("WORKFLOW_DOGFOOD_EXECUTION_BACKEND", "codex_cli")
    monkeypatch.setenv("WORKFLOW_DOGFOOD_MODEL", "gpt-5.5")
    monkeypatch.setenv("WORKFLOW_DOGFOOD_REASONING_EFFORT", "xhigh")
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    router = WorkerRouter(
        [
            ShellAdapter(),
            CodexAdapter(runner=_fake_timeout_runner, executable=sys.executable),
        ]
    )
    service = OrchestratorService(db_path, worker_router=router)

    payload = service.launch_goal(
        goal="M41 fallback should not silently approve failed children",
        preferred_cluster_template_ids=["architecture_delivery_cluster"],
        execute=True,
    )
    assert payload["run"]["run_id"]
    failed_codex_children = []
    recovered_shell_children = []
    for run in service.list_runs(limit=50):
        detail = service.get_status_detail(run.run_id)
        receipt = detail.get("capability_execution_receipt") or {}
        if receipt.get("adapter_name") == "codex" and receipt.get("return_code") == 124:
            failed_codex_children.append(detail)
        if receipt.get("adapter_name") == "shell" and receipt.get("return_code") == 0 and detail["run"]["status"] == "completed":
            recovered_shell_children.append(detail)

    assert failed_codex_children
    assert recovered_shell_children
    assert {item["run"]["status"] for item in failed_codex_children} == {"failed"}
    assert {item["latest_review_verdict"]["decision"] for item in failed_codex_children} == {"fail"}
    assert {item["latest_runtime_attempt"]["status"] for item in failed_codex_children} == {"failed"}
    assert "auto_review_passed" not in {
        item["latest_runtime_attempt"]["close_reason"] for item in failed_codex_children
    }


def test_orchestration_rejects_nonzero_human_required_child_before_fallback(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    router = WorkerRouter(
        [
            MMXMultimodalAdapter(runner=_fake_failure_runner, executable=sys.executable),
            ShellAdapter(),
        ]
    )
    service = OrchestratorService(db_path, worker_router=router)

    service.launch_goal(
        goal="M41 fallback should close failed human-required multimodal child",
        preferred_cluster_template_ids=["architecture_delivery_cluster"],
        execute=True,
    )
    failed_mmx_children = []
    recovered_shell_children = []
    for run in service.list_runs(limit=50):
        detail = service.get_status_detail(run.run_id)
        receipt = detail.get("capability_execution_receipt") or {}
        if receipt.get("adapter_name") == "mmx_multimodal" and receipt.get("return_code") == 2:
            failed_mmx_children.append(detail)
        if (
            detail["run"]["preset_id"] == "research_spike_reviewable"
            and receipt.get("adapter_name") == "shell"
            and receipt.get("return_code") == 0
        ):
            recovered_shell_children.append(detail)

    assert failed_mmx_children
    assert recovered_shell_children
    assert {item["run"]["status"] for item in failed_mmx_children} == {"failed"}
    assert {item["latest_review_verdict"]["decision"] for item in failed_mmx_children} == {"fail"}


def test_capability_health_uses_runtime_invocation_ledger(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    service = OrchestratorService(db_path, workspace_root=tmp_path)
    run = service.create_run("Record capability runtime invocation", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)

    health = service.list_capability_health()
    shell_route = next(
        item for item in health if item["descriptor"]["capability_id"] == "adapter_route:shell_exec:shell"
    )

    assert shell_route["recent_call_summary"]["verified_by_runtime"] is True
    assert shell_route["recent_call_summary"]["recent_success_count"] >= 1
    assert shell_route["readiness_state"] == "recently_successful"
    assert shell_route["runtime_ledger_summary"]["verified_by_runtime"] is True
    assert shell_route["runtime_ledger_summary"]["last_duration_ms"] is not None
    assert shell_route["provider_route"] == "shell"
