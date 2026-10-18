from typing import Literal

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
