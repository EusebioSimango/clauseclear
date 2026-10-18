from __future__ import annotations

import re
from difflib import SequenceMatcher

from clauseclear.schema import Analysis, Finding, ValidatedFinding, ValidationIssue

_WHITESPACE = re.compile(r"\s+")
_CLAUSE_SPLIT = re.compile(r"\n(?=\d+\.\s)")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
SNAP_THRESHOLD = 0.42


def normalize(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip().lower()


def quote_in_source(quote: str, source: str) -> bool:
    """True when the quote appears in the contract after whitespace folding."""
    haystack = normalize(source)
    needle = normalize(quote)
    if len(needle) < 12:
        return False
    if needle in haystack:
        return True
    compact_quote = needle.replace("- ", "").replace(" -", "")
    compact_source = haystack.replace("- ", "").replace(" -", "")
    return compact_quote in compact_source


def candidate_spans(source: str) -> list[str]:
    spans: list[str] = []
    for clause in _CLAUSE_SPLIT.split(source):
        clause = _WHITESPACE.sub(" ", clause).strip()
        if len(clause) >= 12:
            spans.append(clause)
        for sentence in _SENTENCE_SPLIT.split(clause):
            sentence = sentence.strip()
            if len(sentence) >= 12:
                spans.append(sentence)
    return spans


def _score(quote: str, span: str) -> float:
    nq = normalize(quote)
    ns = normalize(span)
    seq = SequenceMatcher(None, nq, ns).ratio()
    q_tokens = set(nq.split())
    s_tokens = set(ns.split())
    significant = {tok for tok in q_tokens if len(tok) > 3 or any(ch.isdigit() for ch in tok)}
    if not significant:
        significant = q_tokens
    overlap = len(significant & s_tokens) / max(len(significant), 1)
    score = 0.6 * overlap + 0.4 * seq
    distinctive = {
        tok
        for tok in q_tokens
        if any(ch.isdigit() for ch in tok) or "$" in tok
    }
    if distinctive & s_tokens:
        score += 0.3
    return min(score, 1.0)


def snap_quote_to_source(quote: str, source: str) -> str | None:
    """Replace a paraphrase with the closest real sentence, or None if nothing is close."""
    if quote_in_source(quote, source):
        return " ".join(quote.split())
    best_span = ""
    best_score = 0.0
    for span in candidate_spans(source):
        score = _score(quote, span)
        if score > best_score:
            best_score = score
            best_span = span
    if best_score >= SNAP_THRESHOLD and best_span:
        return best_span[:600]
    return None


def validate_analysis(analysis: Analysis, source: str) -> tuple[list[ValidatedFinding], list[ValidationIssue]]:
    validated: list[ValidatedFinding] = []
    issues: list[ValidationIssue] = []
    seen_quotes: set[str] = set()

    for index, finding in enumerate(analysis.findings):
        finding_issues: list[str] = []
        grounded = False
        quote = finding.quote
        if not quote_in_source(quote, source):
            snapped = snap_quote_to_source(quote, source)
            if snapped:
                finding = finding.model_copy(update={"quote": snapped})
                quote = snapped
                grounded = True
            else:
                finding_issues.append("quote not found in the contract")
        key = normalize(quote)
        if key in seen_quotes:
            finding_issues.append("duplicate quote")
        seen_quotes.add(key)
        status = "review" if finding_issues else "ok"
        validated.append(
            ValidatedFinding(
                finding=finding,
                status=status,
                issues=finding_issues,
                grounded=grounded,
            )
        )
        for reason in finding_issues:
            issues.append(ValidationIssue(index=index, reason=reason, quote=finding.quote))
    return validated, issues


def retry_instructions(issues: list[ValidationIssue]) -> str:
    if not issues:
        return ""
    lines = [
        "Your previous JSON had problems. Fix ONLY these issues and return JSON again:",
    ]
    for issue in issues:
        snippet = issue.quote[:180]
        lines.append(f"- finding[{issue.index}]: {issue.reason}. quote was: {snippet!r}")
    lines.append(
        "Every quote MUST be an exact contiguous phrase copied from the contract. "
        "Copy a short clause (one sentence). Do not paraphrase. "
        "If you cannot copy a real phrase, drop that finding."
    )
    return "\n".join(lines)


def rank_findings(findings: list[ValidatedFinding]) -> list[ValidatedFinding]:
    order = {"high": 0, "medium": 1, "low": 2, "ok": 3}
    return sorted(
        findings,
        key=lambda item: (0 if item.status == "ok" else 1, order[item.finding.risk]),
    )
