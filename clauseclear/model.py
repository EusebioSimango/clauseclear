from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx
from pydantic import ValidationError

from clauseclear import DEFAULT_MODEL
from clauseclear.schema import Analysis

SYSTEM_PROMPT = """You review freelance client contracts for a solo freelancer.
Return ONLY valid JSON with this shape:
{
  "summary": "2-4 sentences in plain English covering money, IP, lock-in, and exit",
  "findings": [
    {
      "category": "payment|intellectual_property|exclusivity|termination|late_fees|scope|liability|other",
      "risk": "high|medium|low|ok",
      "quote": "exact contiguous phrase copied from the contract",
      "why_it_matters": "one plain-English sentence",
      "ask_instead": "one sentence the freelancer can send to the client"
    }
  ]
}
Rules:
- Produce 4 to 6 findings. Prefer the riskiest payment, IP, exclusivity, termination, late-fee, and scope clauses.
- quote MUST be copied character-for-character from the contract. One sentence, 12-400 characters.
- Bad quote: "the freelancer waits three months to get paid"
- Good quote: "Payment is due ninety (90) days after Client's written acceptance of the final deliverables."
- Do not invent dates, percentages, or obligations that are not in the text.
- This is a flag list, not legal advice.
- No markdown, no commentary, JSON only.
"""


class ModelError(RuntimeError):
    pass


def configured_model() -> str:
    return os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)


def configured_base_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")


def analyze_contract(source: str, extra_instructions: str = "", model: str | None = None) -> Analysis:
    payload = _chat(source, extra_instructions, model or configured_model())
    return Analysis.model_validate(payload)


def _chat(source: str, extra_instructions: str, model: str) -> dict[str, Any]:
    user = (
        "Contract text:\n---\n"
        f"{source[:14000]}\n---\n"
        "Identify the clauses that would hurt a freelancer if signed as-is."
    )
    if extra_instructions:
        user += "\n\n" + extra_instructions

    body = {
        "model": model,
        "temperature": 0.1,
        "max_tokens": 1200,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    url = f"{configured_base_url()}/chat/completions"
    try:
        response = httpx.post(url, json=body, timeout=180.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ModelError(
            "Could not reach the local model. Start Ollama with `ollama serve` "
            f"and pull `{model}`. ({exc})"
        ) from exc

    data = response.json()
    content = data["choices"][0]["message"]["content"]
    parsed = _loads_json(content)
    try:
        Analysis.model_validate(parsed)
    except ValidationError as exc:
        raise ModelError(f"model JSON failed schema: {exc}") from exc
    return parsed


def _loads_json(content: str) -> dict[str, Any]:
    text = content.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ModelError("model did not return JSON")
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ModelError(f"could not parse model JSON: {exc}") from exc
