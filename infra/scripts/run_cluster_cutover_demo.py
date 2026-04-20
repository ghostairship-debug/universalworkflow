from __future__ import annotations

import argparse
import json
from pathlib import Path

from infra.validation.cluster_flow import run_cluster_cutover_demo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the M20 cluster cutover demo and emit a JSON report.")
    parser.add_argument(
        "--db-path",
        default="state/cluster_cutover_demo.db",
        help="SQLite database path used for the cutover demo.",
    )
    parser.add_argument(
        "--report-path",
        default="state/cluster_cutover_demo_report.json",
        help="Where to write the demo JSON report.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_cluster_cutover_demo(Path(args.db_path))
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nCluster cutover demo written to: {report_path.as_posix()}")


if __name__ == "__main__":
    main()
