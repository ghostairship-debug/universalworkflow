from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run a minimal Vertex AI Generative AI smoke request.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--location", default="global")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--prompt-path", required=True)
    args = parser.parse_args(argv)

    try:
        from google import genai
    except ImportError as exc:
        print(f"google-genai is not installed: {exc}", file=sys.stderr)
        return 2

    prompt = Path(args.prompt_path).read_text(encoding="utf-8")
    client = genai.Client(vertexai=True, project=args.project, location=args.location)
    response = client.models.generate_content(model=args.model, contents=prompt)
    text = response.text or ""
    print(text.strip())
    return 0 if text.strip() else 1


if __name__ == "__main__":
    raise SystemExit(main())
