from __future__ import annotations

import argparse
import json
from pathlib import Path

from infra.validation.doc_hygiene import check_living_doc_links


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check living-doc link portability and target validity.")
    parser.add_argument("--report-path", default=None, help="Optional JSON report path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = check_living_doc_links()
    if args.report_path:
        report_path = Path(args.report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
