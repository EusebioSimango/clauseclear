from __future__ import annotations

import time
from pathlib import Path

import sentry_sdk
from pydantic import ValidationError

from clauseclear.extract import extract_text
from clauseclear.model import ModelError, analyze_contract, configured_model
from clauseclear.report import build_email
from clauseclear.schema import Report
from clauseclear.telemetry import hash_source, init_sentry, span
from clauseclear.validate import rank_findings, retry_instructions, validate_analysis

MAX_ATTEMPTS = 3


def review_path(path: str | Path, model: str | None = None) -> Report:
    source_path = Path(path)
    with span("extract", kind="file"):
        text = extract_text(source_path)
    return review_text(text, source_name=source_path.name, model=model)


def review_bytes(raw: bytes, filename: str, model: str | None = None) -> Report:
    with span("extract", kind="upload"):
        text = extract_text("", raw=raw, filename=filename)
    return review_text(text, source_name=filename or "upload", model=model)


def review_text(text: str, source_name: str = "pasted.txt", model: str | None = None) -> Report:
    if len(text.strip()) < 80:
        raise ValueError("Need more contract text (80+ characters).")

    chosen = model or configured_model()
    extra = ""
    last_error: Exception | None = None
    started = time.perf_counter()
    init_sentry()

    with sentry_sdk.start_transaction(op="clauseclear.review", name="review_contract") as txn:
        txn.set_tag("model", chosen)
        txn.set_tag("source_hash", hash_source(text))
        txn.set_tag("chars", str(len(text)))
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                with span("infer", attempt=attempt, model=chosen):
                    analysis = analyze_contract(
                        text, extra_instructions=extra, model=chosen
                    )
                with span("validate", attempt=attempt):
                    findings, issues = validate_analysis(analysis, text)
                quote_misses = [issue for issue in issues if "not found" in issue.reason]
                if quote_misses and attempt < MAX_ATTEMPTS:
                    extra = retry_instructions(quote_misses)
                    continue
                ranked = rank_findings(findings)
                elapsed = time.perf_counter() - started
                txn.set_tag("attempts", str(attempt))
                txn.set_tag(
                    "validated",
                    str(sum(1 for item in ranked if item.status == "ok")),
                )
                return Report(
                    source_name=source_name,
                    char_count=len(text),
                    model=chosen,
                    attempts=attempt,
                    elapsed_seconds=round(elapsed, 2),
                    summary=analysis.summary,
                    findings=ranked,
                    negotiation_email=build_email(ranked, source_name),
                )
            except (ModelError, ValidationError) as exc:
                last_error = exc
                extra = (
                    "Return JSON only, matching the schema. "
                    f"Previous error: {exc}"
                )
                continue

    raise ModelError(
        f"Could not produce a validated review after {MAX_ATTEMPTS} attempts. "
        f"Last error: {last_error}"
    )
