from __future__ import annotations

from pathlib import Path

import typer
from mcp.server.fastmcp import FastMCP


app = typer.Typer(add_completion=False, help="Read-only local workspace MCP server.")


def build_server(workspace_root: Path) -> FastMCP:
    server = FastMCP(
        name="uawo-readonly-workspace",
        instructions="Read-only workspace inspection server for low-risk local MCP pilots.",
    )

    @server.tool(
        name="mcp_list_workspace_files",
        description="List up to 50 files under the workspace root. Read-only.",
    )
    def list_workspace_files(limit: int = 50) -> list[str]:
        files = [
            path.relative_to(workspace_root).as_posix()
            for path in workspace_root.rglob("*")
            if path.is_file()
        ]
        return sorted(files)[:limit]

    @server.tool(
        name="mcp_read_workspace_text",
        description="Read a UTF-8 text file under the workspace root. Read-only.",
    )
    def read_workspace_text(relative_path: str, max_chars: int = 8000) -> str:
        target = (workspace_root / relative_path).resolve()
        if workspace_root not in target.parents and target != workspace_root:
            raise ValueError("requested path is outside the workspace root")
        return target.read_text(encoding="utf-8")[:max_chars]

    return server


@app.command()
def main(
    workspace_root: str = typer.Option(".", "--workspace-root", help="Workspace root to expose."),
) -> None:
    root = Path(workspace_root).resolve()
    build_server(root).run(transport="stdio")


if __name__ == "__main__":
    app()
