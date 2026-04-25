from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.core_domain.test_matrix import run_matrix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the workflow pytest matrix with isolated basetemp.")
    parser.add_argument("--suite", choices=["unit", "core", "integration", "slow", "full"], required=True)
    parser.add_argument("--shard", help="Optional N/M shard selector.")
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = run_matrix(
            suite=args.suite,
            shard=args.shard,
            workspace_root=Path(args.workspace_root).resolve(),
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return int(payload.get("return_code") or 0)


if __name__ == "__main__":
    raise SystemExit(main())
