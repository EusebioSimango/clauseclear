from __future__ import annotations

from clauseclear.schema import Report, ValidatedFinding

RISK_LABEL = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW", "ok": "OK"}


def build_email(findings: list[ValidatedFinding], source_name: str) -> str:
    asks = [
        item.finding.ask_instead
        for item in findings
        if item.finding.risk in {"high", "medium"}
    ]
    if not asks:
        asks = [item.finding.ask_instead for item in findings[:3]]
    numbered = "\n".join(f"{i}. {ask}" for i, ask in enumerate(asks[:5], start=1))
    return (
        f"Hi — thanks for sending the agreement ({source_name}). "
        "I can move forward once we tighten a few clauses:\n\n"
        f"{numbered}\n\n"
        "Happy to send a redline. Thanks."
    )


def to_markdown(report: Report) -> str:
    lines = [
        f"# ClauseClear report — {report.source_name}",
        "",
        f"- Model: `{report.model}`",
        f"- Characters reviewed: {report.char_count}",
        f"- Attempts: {report.attempts}",
        f"- Time: {report.elapsed_seconds:.1f}s",
        "",
        "## Summary",
        "",
        report.summary,
        "",
        "## Clauses to negotiate",
        "",
    ]
    for item in report.findings:
        flag = "NEEDS REVIEW" if item.status == "review" else RISK_LABEL[item.finding.risk]
        lines.extend(
            [
                f"### {item.finding.category.replace('_', ' ').title()} — {flag}",
                "",
                f"> {item.finding.quote}",
                "",
                f"**Why it matters:** {item.finding.why_it_matters}",
                "",
                f"**Ask instead:** {item.finding.ask_instead}",
                "",
            ]
        )
        if item.grounded:
            lines.append("_Quote grounded to the nearest sentence in the contract._")
            lines.append("")
        if item.issues:
            lines.append(f"_Validator: {'; '.join(item.issues)}_")
            lines.append("")
    lines.extend(["---", "", report.disclaimer, ""])
    return "\n".join(lines)
