from __future__ import annotations

import subprocess
import sys
import json
import sqlite3
import time
from pathlib import Path
import re
from types import SimpleNamespace

from packages.contracts import AgentRoleType, MutationContract, MutationMode, TaskKind, TaskPacket
from packages.core_domain.cluster_router import ClusterRouter
from packages.core_domain.config import build_effective_config
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
from packages.worker_adapters.subprocess_support import completed_process_watchdog_metadata
from packages.worker_adapters.subprocess_support import _direct_visible_provider_python_script
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


def test_legacy_openai_family_model_env_values_upgrade_to_gpt55() -> None:
    effective = build_effective_config(
        env={
            "WORKFLOW_AGENT_MODEL": "gpt-5.4-mini",
            "WORKFLOW_CODEX_MODEL": "gpt-5.4",
            "WORKFLOW_OPENAI_MODEL": "gpt-5.4-mini",
            "WORKFLOW_DOGFOOD_MODEL": "gpt-5.4",
            "WORKFLOW_ADAPTIVE_COMPLEX_MODEL": "gpt-5.4",
        }
    )

    assert effective["agent"]["model"] == "gpt-5.5"
    assert effective["codex"]["model"] == "gpt-5.5"
    assert effective["runtime_gateway"]["openai_model"] == "gpt-5.5"
    assert effective["dogfood"]["model"] == "gpt-5.5"
    assert effective["adaptive_llm_routing"]["complex_model"] == "gpt-5.5"


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

    def _fake_tree_runner(command, cwd, env, capture_output, text, check, timeout, idle_timeout=None):
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
                "idle_timeout": idle_timeout,
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
    assert calls[0]["idle_timeout"] == 120
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
    patch_command = adapter.build_command(patch_packet)
    patch_prompt = patch_command[-1]

    assert "Provider command policy: patch_only_no_shell" in patch_prompt
    assert "Patch-only mode: do not run shell, PowerShell, cmd, Python" in patch_prompt
    assert "Embedded read-set context JSON" in patch_prompt
    assert "Return exactly one valid unified diff patch" in patch_prompt
    assert "artifact-only workflow agent" not in patch_prompt
    assert "--ignore-user-config" in patch_command
    assert "--ignore-rules" in patch_command
    patch_cd = Path(patch_command[patch_command.index("--cd") + 1])
    artifact_cd = Path(artifact_command[artifact_command.index("--cd") + 1])
    assert artifact_cd == tmp_path.resolve()
    assert patch_cd != tmp_path.resolve()
    assert "workflow_codex_patch_apply" in patch_cd.as_posix()
    for feature in [
        "apps",
        "plugins",
        "memories",
        "tool_search",
        "browser_use",
        "computer_use",
        "image_generation",
        "workspace_dependencies",
    ]:
        assert ["--disable", feature] == patch_command[
            patch_command.index(feature) - 1 : patch_command.index(feature) + 1
        ]
    assert "--ignore-user-config" not in artifact_command
    assert "--ignore-rules" not in artifact_command


def test_codex_patch_apply_launch_uses_prompt_only_workspace(tmp_path: Path) -> None:
    observed: dict[str, object] = {}

    def _recording_runner(command, cwd, env, capture_output, text, check, timeout):
        observed["command"] = command
        observed["cwd"] = cwd
        artifact = Path(command[command.index("--output-last-message") + 1])
        artifact.write_text("--- a/target.txt\n+++ b/target.txt\n@@ -1 +1 @@\n-before\n+after\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="patch\n", stderr="")

    packet = _packet(
        tmp_path,
        env={"WORKFLOW_CODEX_PATCH_APPLY_PROMPT_WORKSPACE": (tmp_path / "broker").as_posix()},
        artifact="patch.diff",
    )
    patch_packet = TaskPacket.model_validate(
        {
            **packet.model_dump(mode="json"),
            "mutation_contract": MutationContract(
                write_set=["target.txt"],
                mutation_mode=MutationMode.patch_apply,
            ).model_dump(mode="json"),
        }
    )
    adapter = CodexAdapter(runner=_recording_runner, executable=sys.executable)

    result = adapter.launch(patch_packet)

    broker_root = tmp_path / "broker"
    assert Path(str(observed["cwd"])).is_relative_to(broker_root)
    command = observed["command"]
    assert command[command.index("--cd") + 1] == observed["cwd"]
    assert "--ignore-rules" in command
    assert result.metadata["prompt_transport"] == "argv"
    assert Path(result.metadata["prompt_workspace"]).is_relative_to(broker_root)
    assert result.metadata["project_working_directory"] == tmp_path.resolve().as_posix()
    assert result.metadata["project_rules_ignored"] is True


def test_opencode_patch_apply_prompt_uses_patch_only_command_policy(tmp_path: Path) -> None:
    packet = _packet(
        tmp_path,
        env={
            "WORKFLOW_MUTATION_PROVIDER_COMMAND_POLICY": "patch_only_no_shell",
            "WORKFLOW_MUTATION_READ_SET_CONTEXT": '[{"path":"target.txt","kind":"file"}]',
        },
        artifact="opencode_artifact.md",
    )
    patch_packet = TaskPacket.model_validate(
        {
            **packet.model_dump(mode="json"),
            "mutation_contract": MutationContract(
                write_set=["target.txt"],
                mutation_mode=MutationMode.patch_apply,
            ).model_dump(mode="json"),
        }
    )
    adapter = OpenCodeAdapter(runner=_fake_success_runner, executable=sys.executable)

    patch_prompt = adapter.build_command(patch_packet)[-1]

    assert "Provider command policy: patch_only_no_shell" in patch_prompt
    assert "Patch-only mode: do not run shell, PowerShell, cmd, Python" in patch_prompt
    assert "Embedded read-set context JSON" in patch_prompt
    assert "Return exactly one valid unified diff patch" in patch_prompt
    assert "<<<WORKFLOW_FILE>>>" not in patch_prompt


def test_opencode_patch_apply_spills_large_prompt_to_file_attachment(tmp_path: Path) -> None:
    context_file = tmp_path / "read_context.json"
    context_file.write_text(json.dumps([{"path": "target.txt", "content_preview": "x" * 15000}]), encoding="utf-8")
    packet = _packet(
        tmp_path,
        env={
            "WORKFLOW_MUTATION_PROVIDER_COMMAND_POLICY": "patch_only_no_shell",
            "WORKFLOW_MUTATION_READ_SET_CONTEXT": "",
            "WORKFLOW_MUTATION_READ_SET_CONTEXT_FILE": context_file.as_posix(),
        },
        artifact="opencode_artifact.md",
    )
    patch_packet = TaskPacket.model_validate(
        {
            **packet.model_dump(mode="json"),
            "mutation_contract": MutationContract(
                write_set=["target.txt"],
                mutation_mode=MutationMode.patch_apply,
            ).model_dump(mode="json"),
        }
    )
    adapter = OpenCodeAdapter(runner=_fake_success_runner, executable=sys.executable)

    command = adapter.build_command(patch_packet)

    assert "--file" in command
    prompt_path = Path(command[command.index("--file") + 1])
    assert prompt_path.exists()
    prompt_content = prompt_path.read_text(encoding="utf-8")
    assert "Embedded read-set context JSON" in prompt_content
    assert "x" * 100 in prompt_content
    assert command[command.index("--file") - 1] == (
        "Execute the workflow mutation instructions in the attached prompt file. Return only the requested unified diff."
    )


def test_opencode_adapter_timeout_can_be_overridden_for_task_card_runs(monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_OPENCODE_TIMEOUT_SECONDS", "45")

    adapter = OpenCodeAdapter(runner=_fake_success_runner, executable=sys.executable)

    assert adapter.timeout_seconds == 45


def test_opencode_adapter_timeout_can_be_overridden_per_packet(tmp_path: Path, monkeypatch) -> None:
    observed: dict[str, int] = {}

    def _recording_runner(command, cwd, env, capture_output, text, check, timeout):
        observed["timeout"] = timeout
        return subprocess.CompletedProcess(command, 0, stdout="artifact\n", stderr="")

    monkeypatch.delenv("WORKFLOW_OPENCODE_TIMEOUT_SECONDS", raising=False)
    adapter = OpenCodeAdapter(runner=_recording_runner, executable=sys.executable)
    packet = _packet(
        tmp_path,
        env={"WORKFLOW_OPENCODE_TIMEOUT_SECONDS": "12"},
        artifact="opencode_timeout.md",
    )

    result = adapter.launch(packet)

    assert observed["timeout"] == 12
    assert result.metadata["timeout_seconds"] == 12


def test_opencode_adapter_can_launch_direct_visible_provider_cli(tmp_path: Path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def _fake_visible(command, **kwargs):
        calls.append({"command": command, "kwargs": kwargs})
        completed = subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        setattr(
            completed,
            "direct_visible_cli_session",
            {"mode": "direct_provider_visible_cli_enforced", "provider": "opencode", "provider_pid": 5678},
        )
        setattr(completed, "direct_visible_cli_log_paths", {"session_path": (tmp_path / "session.json").as_posix()})
        return completed

    monkeypatch.setattr("packages.worker_adapters.opencode_adapter.run_subprocess_with_direct_visible_cli", _fake_visible)
    packet = _packet(
        tmp_path,
        env={
            "WORKFLOW_PROVIDER_DIRECT_VISIBLE_CLI": "1",
            "WORKFLOW_PROVIDER_VISIBLE_SESSION_ROOT": (tmp_path / "visible").as_posix(),
        },
        artifact="opencode_visible.md",
    )

    result = OpenCodeAdapter(executable=sys.executable).launch(packet)

    assert result.return_code == 0
    assert calls
    assert calls[0]["kwargs"]["provider_name"] == "opencode"
    assert Path(str(calls[0]["kwargs"]["visible_session_dir"])).as_posix().endswith("/run_m41/task_m41/opencode")
    command = calls[0]["command"]
    assert command[command.index("--format") + 1] == "default"
    assert result.metadata["direct_visible_provider_cli"] is True
    assert result.metadata["provider_output_mode"] == "human_readable"
    assert result.metadata["direct_visible_cli_session"]["provider"] == "opencode"


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


def test_codex_adapter_can_launch_direct_visible_provider_cli(tmp_path: Path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def _fake_visible(command, **kwargs):
        calls.append({"command": command, "kwargs": kwargs})
        completed = subprocess.CompletedProcess(command, 0, stdout='{"type":"turn.completed"}\n', stderr="")
        setattr(
            completed,
            "direct_visible_cli_session",
            {"mode": "direct_provider_visible_cli_enforced", "provider": "codex", "provider_pid": 1234},
        )
        setattr(completed, "direct_visible_cli_log_paths", {"session_path": (tmp_path / "session.json").as_posix()})
        return completed

    monkeypatch.setattr("packages.worker_adapters.codex_adapter.run_subprocess_with_direct_visible_cli", _fake_visible)
    packet = _packet(
        tmp_path,
        env={
            "WORKFLOW_PROVIDER_DIRECT_VISIBLE_CLI": "1",
            "WORKFLOW_PROVIDER_VISIBLE_SESSION_ROOT": (tmp_path / "visible").as_posix(),
        },
        artifact="codex_visible.md",
    )

    result = CodexAdapter(executable=sys.executable).launch(packet)

    assert result.return_code == 0
    assert calls
    assert calls[0]["kwargs"]["provider_name"] == "codex"
    assert Path(str(calls[0]["kwargs"]["visible_session_dir"])).as_posix().endswith("/run_m41/task_m41/codex")
    assert calls[0]["command"][-1] == "-"
    assert "--json" not in calls[0]["command"]
    assert result.metadata["direct_visible_provider_cli"] is True
    assert result.metadata["provider_output_mode"] == "human_readable"
    assert result.metadata["direct_visible_cli_session"]["provider"] == "codex"


def test_direct_visible_provider_script_uses_python_mirror_wrapper(tmp_path: Path) -> None:
    script = _direct_visible_provider_python_script(
        command=[
            "C:/Tools/codex.CMD",
            "exec",
            "--output-last-message",
            "D:/Universal Agentic workflow/state/artifacts/patch.diff",
            "-c",
            'model_reasoning_effort="xhigh"',
            "-",
        ],
        cwd=tmp_path,
        stdout_path=tmp_path / "stdout.log",
        stderr_path=tmp_path / "stderr.log",
        stream_path=tmp_path / "stream.jsonl",
        pid_path=tmp_path / "provider_pid.json",
        exit_path=tmp_path / "exit_code.json",
        stdin_path=tmp_path / "stdin.txt",
    )

    assert "$psi.ArgumentList.Add" not in script
    assert "provider_wrapper_exception" in script
    assert "subprocess.Popen(" in script
    assert "shutil.which" in script
    assert "provider_pid" in script


def test_codex_adapter_timeout_records_failure_class_and_stream_previews(tmp_path: Path) -> None:
    adapter = CodexAdapter(runner=_fake_timeout_runner, executable=sys.executable)
    packet = _packet(tmp_path, artifact="codex_timeout.md")

    result = adapter.launch(packet)

    assert result.return_code == 124
    assert result.metadata["failure_class"] == "provider_timeout"
    assert result.metadata["timeout_type"] == "wall_timeout"
    assert result.metadata["timeout_failure_class"] == "provider_wall_timeout"
    assert result.metadata["recovery_suggestion"] == "split_task_or_raise_wall_timeout_with_progress_evidence"
    assert result.metadata["stdout_preview"] == "partial stdout"
    assert "partial stderr" in result.metadata["stderr_preview"]
    assert "timed out after" in result.metadata["stderr_preview"]


def test_codex_adapter_records_provider_stream_event_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    packet = _packet(
        tmp_path,
        env={"WORKFLOW_DB_PATH": db_path.as_posix()},
        artifact="codex_stream.md",
    )
    adapter = CodexAdapter(executable=sys.executable)

    result = adapter.launch(packet)

    assert result.return_code != 0
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT event_type, payload_json FROM run_events WHERE event_type = 'provider_stream_observed'"
        ).fetchone()
    assert row is not None
    payload = json.loads(row[1])
    assert payload["run_id"] == "run_m41"
    assert payload["runtime_task_id"] == "task_m41"
    assert payload["adapter_name"] == "codex"
    assert payload["classification"] == "provider_output"
    assert payload["line_sha256"]
    assert "text" not in payload


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
    assert completed.timeout_type == "wall_timeout"


def test_subprocess_progress_watchdog_records_idle_timeout_for_silent_cli(tmp_path: Path) -> None:
    completed = run_subprocess_with_tree_timeout(
        [sys.executable, "-c", "import time; time.sleep(10)"],
        cwd=tmp_path.as_posix(),
        env={},
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
        idle_timeout=1,
    )

    assert completed.returncode == 124
    assert completed.timeout_type == "idle_timeout"
    assert "idle_timeout" in completed.stderr
    assert completed.stream_event_count == 0


def test_subprocess_progress_watchdog_keeps_output_alive_until_wall_timeout(tmp_path: Path) -> None:
    script = (
        "import sys, time\n"
        "for index in range(20):\n"
        "    print(f'tick {index}', flush=True)\n"
        "    time.sleep(0.2)\n"
    )
    completed = run_subprocess_with_tree_timeout(
        [sys.executable, "-c", script],
        cwd=tmp_path.as_posix(),
        env={},
        capture_output=True,
        text=True,
        check=False,
        timeout=2,
        idle_timeout=1.5,
    )

    assert completed.returncode == 124
    assert completed.timeout_type == "wall_timeout"
    assert "tick" in completed.stdout
    assert completed.stdout_event_count > 1
    assert completed.stream_event_count > 1


def test_subprocess_watchdog_does_not_count_workflow_progress_as_provider_output(tmp_path: Path) -> None:
    script = (
        "import sys, time\n"
        "for index in range(20):\n"
        "    print(f'workflow_progress {index}', file=sys.stderr, flush=True)\n"
        "    time.sleep(0.1)\n"
    )
    completed = run_subprocess_with_tree_timeout(
        [sys.executable, "-c", script],
        cwd=tmp_path.as_posix(),
        env={},
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
        idle_timeout=2,
        provider_output_idle_timeout=0.5,
    )

    assert completed.returncode == 124
    assert completed.timeout_type == "provider_output_idle_timeout"
    assert completed.control_output_event_count > 0
    assert completed.provider_output_event_count == 0
    assert completed.stream_event_count > 0


def test_subprocess_provider_activity_probe_prevents_outer_provider_idle(tmp_path: Path) -> None:
    started = time.monotonic()

    def _probe() -> dict[str, object]:
        elapsed = time.monotonic() - started
        if elapsed > 0.1:
            return {
                "provider_output_event_count": int(elapsed * 20),
                "last_provider_output_at": "2026-04-30T00:00:00+00:00",
            }
        return {"provider_output_event_count": 0}

    completed = run_subprocess_with_tree_timeout(
        [sys.executable, "-c", "import time; time.sleep(0.35)"],
        cwd=tmp_path.as_posix(),
        env={},
        capture_output=True,
        text=True,
        check=False,
        timeout=2,
        provider_output_idle_timeout=0.2,
        activity_probe=_probe,
        activity_probe_interval=0.05,
    )

    assert completed.returncode == 0
    assert completed.provider_output_event_count >= 1
    assert completed.timeout_type is None


def test_subprocess_watchdog_detects_no_material_progress_with_provider_output(tmp_path: Path) -> None:
    script = (
        "import time\n"
        "for index in range(20):\n"
        "    print(f'thinking {index}', flush=True)\n"
        "    time.sleep(0.1)\n"
    )
    completed = run_subprocess_with_tree_timeout(
        [sys.executable, "-c", script],
        cwd=tmp_path.as_posix(),
        env={},
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
        idle_timeout=2,
        provider_output_idle_timeout=2,
        material_progress_idle_timeout=0.5,
    )

    assert completed.returncode == 124
    assert completed.timeout_type == "provider_no_material_progress_timeout"
    assert completed.provider_output_event_count > 0
    assert completed.material_progress_event_count == 0


def test_subprocess_watchdog_records_material_progress_markers(tmp_path: Path) -> None:
    script = (
        "import time\n"
        "for index in range(3):\n"
        "    print(f'changed_files marker_{index}', flush=True)\n"
        "    time.sleep(0.1)\n"
    )
    completed = run_subprocess_with_tree_timeout(
        [sys.executable, "-c", script],
        cwd=tmp_path.as_posix(),
        env={},
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
        idle_timeout=2,
        provider_output_idle_timeout=2,
        material_progress_idle_timeout=1,
    )

    assert completed.returncode == 0
    assert completed.timeout_type is None
    assert completed.provider_output_event_count == 3
    assert completed.material_progress_event_count == 3


def test_subprocess_adaptive_wall_timeout_extends_with_recent_material_progress(tmp_path: Path) -> None:
    script = (
        "import time\n"
        "print('changed_files initial_patch', flush=True)\n"
        "time.sleep(1.2)\n"
        "print('done', flush=True)\n"
    )
    completed = run_subprocess_with_tree_timeout(
        [sys.executable, "-c", script],
        cwd=tmp_path.as_posix(),
        env={},
        capture_output=True,
        text=True,
        check=False,
        timeout=1,
        idle_timeout=3,
        provider_output_idle_timeout=3,
        material_progress_idle_timeout=3,
        adaptive_wall_timeout_extension=1,
        adaptive_wall_timeout_max_extensions=1,
        adaptive_wall_timeout_absolute_max=2,
        adaptive_wall_timeout_progress_window=3,
    )

    assert completed.returncode == 0
    assert completed.timeout_type is None
    assert completed.adaptive_wall_timeout_extension_count == 1
    assert completed.adaptive_wall_timeout_effective_seconds == 2
    assert completed.material_progress_event_count >= 1


def test_subprocess_adaptive_wall_timeout_requires_material_progress(tmp_path: Path) -> None:
    script = (
        "import time\n"
        "print('provider output only', flush=True)\n"
        "time.sleep(1.2)\n"
    )
    completed = run_subprocess_with_tree_timeout(
        [sys.executable, "-c", script],
        cwd=tmp_path.as_posix(),
        env={},
        capture_output=True,
        text=True,
        check=False,
        timeout=1,
        idle_timeout=3,
        provider_output_idle_timeout=3,
        material_progress_idle_timeout=3,
        adaptive_wall_timeout_extension=1,
        adaptive_wall_timeout_max_extensions=1,
        adaptive_wall_timeout_absolute_max=2,
        adaptive_wall_timeout_progress_window=3,
    )

    assert completed.returncode == 124
    assert completed.timeout_type == "wall_timeout"
    assert completed.adaptive_wall_timeout_extension_count == 0
    assert completed.provider_output_event_count >= 1
    assert completed.material_progress_event_count == 0


def test_subprocess_adaptive_wall_timeout_exhaustion_reports_split_signal(tmp_path: Path) -> None:
    script = (
        "import time\n"
        "print('changed_files initial_patch', flush=True)\n"
        "time.sleep(2.2)\n"
    )
    completed = run_subprocess_with_tree_timeout(
        [sys.executable, "-c", script],
        cwd=tmp_path.as_posix(),
        env={},
        capture_output=True,
        text=True,
        check=False,
        timeout=1,
        idle_timeout=4,
        provider_output_idle_timeout=4,
        material_progress_idle_timeout=4,
        adaptive_wall_timeout_extension=1,
        adaptive_wall_timeout_max_extensions=1,
        adaptive_wall_timeout_absolute_max=2,
        adaptive_wall_timeout_progress_window=4,
    )
    metadata = completed_process_watchdog_metadata(completed)

    assert completed.returncode == 124
    assert completed.timeout_type == "adaptive_wall_timeout_exhausted"
    assert metadata["timeout_failure_class"] == "task_scope_too_large_after_adaptive_wall_timeout"
    assert metadata["adaptive_wall_timeout_extension_count"] == 1
    assert metadata["adaptive_wall_timeout_exhausted"] is True


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
            "WORKFLOW_CODEX_MODEL": "gpt-5.5",
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
        env={"WORKFLOW_CODEX_MODEL": "gpt-5.5"},
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
