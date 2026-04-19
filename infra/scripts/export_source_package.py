from __future__ import annotations

import argparse
import json
from pathlib import Path

from infra.validation.source_package import export_source_package


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a clean source package or run a dry hygiene check.")
    parser.add_argument(
        "--output-path",
        default="state/source_packages/pre_m8_source_package.zip",
        help="Output archive path.",
    )
    parser.add_argument(
        "--manifest-path",
        default="state/source_packages/pre_m8_source_package_manifest.json",
        help="Manifest output path.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write the archive; only emit the manifest.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = export_source_package(
        Path(args.output_path),
        manifest_path=Path(args.manifest_path),
        dry_run=args.dry_run,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
