# M8 Phase 2 Task Cards

| Task | Size | Goal | Primary Files | Done When |
| --- | --- | --- | --- | --- |
| `M8-2A` | `medium` | Introduce capability-source abstraction | `packages/core_domain/capability_plane.py` | built-in and MCP capability sources exist |
| `M8-2B` | `medium` | Add local stdio MCP pilot harness | `infra/mcp/readonly_workspace_server.py`, `infra/seeds/mcp_server_profiles.json` | local readonly MCP server can be projected |
| `M8-2C` | `small` | Add capability-source/projection operator surfaces | CLI/API + service methods | tool projection can be previewed without execution |

## Closeout

- The repository now projects a small MCP subset into the agent lane instead of exposing raw inventory.
