# M8 Phase 2 - MCP Capability Pilot

**Phase status:** Completed  
**Entry condition:** the standard agent lane exists and can consume a projected tool subset.

## Scope

- add capability-source abstraction
- add built-in capability source
- add local stdio MCP capability source
- add read-only local MCP server harness
- add tool-projection manifest and server-profile surfaces

## Outputs

- `packages/core_domain/capability_plane.py`
- `infra/mcp/readonly_workspace_server.py`
- `infra/seeds/mcp_server_profiles.json`
- CLI/API capability source and projection preview commands

## Outcome

- Reframed the capability plane as router-first projection instead of raw inventory exposure.
- Added the first local stdio MCP profile and fake/local harness.
- Added projection manifests that keep `TaskKind` stable while allowing tool diversity through capability selection.

## Next Reassessment

Next approved phase: `M8 Phase 3 - Observability Abstraction And First Sink`
