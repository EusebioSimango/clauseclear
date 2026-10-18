from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Category = Literal[
    "payment",
    "intellectual_property",
    "exclusivity",
    "termination",
    "late_fees",
    "scope",
    "liability",
    "other",
]
Risk = Literal["high", "medium", "low", "ok"]

CATEGORIES: tuple[str, ...] = (
    "payment",
    "intellectual_property",
    "exclusivity",
    "termination",
    "late_fees",
    "scope",
    "liability",
    "other",
)
RISKS: tuple[str, ...] = ("high", "medium", "low", "ok")

_CATEGORY_ALIASES = {
    "compensation": "payment",
    "fee": "payment",
    "fees": "payment",
    "invoice": "payment",
    "ip": "intellectual_property",
    "ownership": "intellectual_property",
    "work_product": "intellectual_property",
    "noncompete": "exclusivity",
    "non_compete": "exclusivity",
    "term": "termination",
    "access": "scope",
    "services": "scope",
    "confidentiality": "other",
    "privacy": "other",
    "damages": "liability",
    "indemnity": "liability",
    "indemnification": "liability",
}


def _first_allowed(raw: str, allowed: tuple[str, ...]) -> str | None:
    for token in raw.replace("/", "|").replace(",", "|").split("|"):
        token = token.strip().lower().replace(" ", "_").replace("-", "_")
        if token in allowed:
            return token
        if token in _CATEGORY_ALIASES and _CATEGORY_ALIASES[token] in allowed:
            return _CATEGORY_ALIASES[token]
    return None


def coerce_category(value: Any) -> str:
    if not isinstance(value, str):
        return "other"
    text = value.strip()
    if text in CATEGORIES:
        return text
    picked = _first_allowed(text, CATEGORIES)
    if picked:
        return picked
    lowered = text.lower().replace(" ", "_")
    for alias, target in _CATEGORY_ALIASES.items():
        if alias in lowered:
            return target
    return "other"


def coerce_risk(value: Any) -> str:
    if not isinstance(value, str):
        return "medium"
    text = value.strip().lower()
    if text in RISKS:
        return text
    return _first_allowed(text, RISKS) or "medium"


def coerce_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    """Repair 1B-model JSON that copies enum unions into fields."""
    findings = payload.get("findings")
    if not isinstance(findings, list):
        return payload
    cleaned = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        row["category"] = coerce_category(row.get("category"))
        row["risk"] = coerce_risk(row.get("risk"))
        cleaned.append(row)
    payload = dict(payload)
    payload["findings"] = cleaned
    return payload


class Finding(BaseModel):
    category: Category
    risk: Risk
    quote: str = Field(min_length=12, max_length=600)
    why_it_matters: str = Field(min_length=12, max_length=500)
    ask_instead: str = Field(min_length=12, max_length=500)

    @field_validator("quote", "why_it_matters", "ask_instead")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("field cannot be empty")
        return cleaned


class Analysis(BaseModel):
    summary: str = Field(min_length=20, max_length=1200)
    findings: list[Finding] = Field(min_length=1, max_length=8)

    @field_validator("summary")
    @classmethod
    def strip_summary(cls, value: str) -> str:
        return " ".join(value.split())


class ValidationIssue(BaseModel):
    index: int
    reason: str
    quote: str = ""


class ValidatedFinding(BaseModel):
    finding: Finding
    status: Literal["ok", "review"]
    issues: list[str] = Field(default_factory=list)
    grounded: bool = False


class Report(BaseModel):
    source_name: str
    char_count: int
    model: str
    attempts: int
    elapsed_seconds: float
    summary: str
    findings: list[ValidatedFinding]
    negotiation_email: str
    disclaimer: str = (
        "ClauseClear is not a lawyer and this is not legal advice. "
        "It flags clauses a freelancer may want a human to review."
    )
