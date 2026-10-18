from __future__ import annotations

import argparse
import sys
from pathlib import Path

from clauseclear.extract import ExtractError
from clauseclear.model import ModelError, configured_model
from clauseclear.pipeline import review_path
from clauseclear.report import to_markdown
from clauseclear.telemetry import init_sentry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review a freelance contract locally with an open-weight Gemma model."
    )
    parser.add_argument("path", help="PDF or text contract")
    parser.add_argument(
        "--model",
        default=configured_model(),
        help="Ollama model tag (default: env OLLAMA_MODEL or gemma3:1b)",
    )
    parser.add_argument("-o", "--out", help="Write markdown report to this path")
    args = parser.parse_args(argv)

    init_sentry()
    try:
        report = review_path(args.path, model=args.model)
    except (ExtractError, ModelError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    markdown = to_markdown(report)
    if args.out:
        Path(args.out).write_text(markdown, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(markdown)

    ok = sum(1 for item in report.findings if item.status == "ok")
    review = sum(1 for item in report.findings if item.status == "review")
    print(
        f"\n# {ok} validated, {review} need review, "
        f"{report.attempts} attempt(s), {report.elapsed_seconds:.1f}s, model {report.model}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
