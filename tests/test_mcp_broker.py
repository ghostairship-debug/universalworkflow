from __future__ import annotations

from packages.contracts import ExecutionLaneType, MCPServerProfile, MCPTransport, ReviewPolicy, TaskKind
from packages.core_domain import capability_plane
from packages.core_domain.capability_plane import CapabilityPlane


def _profile(profile_id: str, tools: list[str]) -> MCPServerProfile:
    return MCPServerProfile(
        profile_id=profile_id,
        name=profile_id.replace("_", " ").title(),
        description=f"{profile_id} test MCP profile",
        transport=MCPTransport.stdio,
        startup_command=["test-mcp-server"],
        allowed_tools=tools,
        max_tools=len(tools),
    )


def _manifest(
    plane: CapabilityPlane,
    *,
    profile_ids: list[str] | None = None,
    tool_ids: list[str] | None = None,
):
    return plane.build_projection_manifest(
        run_id=None,
        preset_id="research_spike_reviewable",
        task_kind=TaskKind.shell_exec,
        review_policy=ReviewPolicy.optional,
        lane_type=ExecutionLaneType.standard_agent,
        include_mcp=True,
        mcp_profile_ids=profile_ids,
        mcp_tool_ids=tool_ids,
    )


def test_mcp_broker_requires_explicit_profile_or_tool_selector(monkeypatch) -> None:
    monkeypatch.setattr(capability_plane, "mcp_dependency_available", lambda: True)
    plane = CapabilityPlane(
        mcp_profiles=[
            _profile("alpha", ["shared_tool", "alpha_only"]),
            _profile("beta", ["shared_tool", "beta_only"]),
        ]
    )

    manifest, profiles = _manifest(plane)

    assert profiles == []
    assert all(str(tool.source_type) == "built_in" for tool in manifest.tools)


def test_mcp_broker_keeps_same_name_tools_canonical_per_profile(monkeypatch) -> None:
    monkeypatch.setattr(capability_plane, "mcp_dependency_available", lambda: True)
    plane = CapabilityPlane(
        mcp_profiles=[
            _profile("alpha", ["shared_tool"]),
            _profile("beta", ["shared_tool"]),
        ]
    )

    manifest, profiles = _manifest(plane, profile_ids=["alpha", "beta"])

    mcp_tool_ids = {tool.canonical_tool_id for tool in manifest.tools if str(tool.source_type) == "mcp_stdio"}
    assert {profile.profile_id for profile in profiles} == {"alpha", "beta"}
    assert mcp_tool_ids == {"mcp:alpha:shared_tool", "mcp:beta:shared_tool"}


def test_mcp_broker_can_select_single_canonical_tool(monkeypatch) -> None:
    monkeypatch.setattr(capability_plane, "mcp_dependency_available", lambda: True)
    plane = CapabilityPlane(
        mcp_profiles=[
            _profile("alpha", ["shared_tool", "alpha_only"]),
            _profile("beta", ["shared_tool", "beta_only"]),
        ]
    )

    manifest, profiles = _manifest(plane, tool_ids=["mcp:beta:shared_tool"])

    mcp_tools = [tool for tool in manifest.tools if str(tool.source_type) == "mcp_stdio"]
    assert [profile.profile_id for profile in profiles] == ["beta"]
    assert [tool.canonical_tool_id for tool in mcp_tools] == ["mcp:beta:shared_tool"]
