from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run a minimal MiniMax OpenAI-compatible smoke request.")
    parser.add_argument("--model", default="MiniMax-M2.7")
    parser.add_argument("--base-url", default="https://api.minimaxi.com/v1")
    parser.add_argument("--prompt-path", required=True)
    args = parser.parse_args(argv)

    api_key = os.getenv("MINIMAX_API_KEY") or os.getenv("MINIMAX_TOKEN")
    if not api_key:
        print("MINIMAX_API_KEY or MINIMAX_TOKEN is required", file=sys.stderr)
        return 2
    try:
        from openai import OpenAI
    except ImportError as exc:
        print(f"openai package is not installed: {exc}", file=sys.stderr)
        return 2

    prompt = Path(args.prompt_path).read_text(encoding="utf-8")
    client = OpenAI(api_key=api_key, base_url=str(args.base_url).rstrip("/"))
    response = client.chat.completions.create(
        model=args.model,
        messages=[
            {"role": "system", "content": "Return concise plain text evidence for a local workflow capability probe."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=800,
    )
    text = response.choices[0].message.content or ""
    print(text.strip())
    return 0 if text.strip() else 1


if __name__ == "__main__":
    raise SystemExit(main())
