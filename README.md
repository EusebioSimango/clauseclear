# ClauseClear

Local contract review for freelancers. Paste a client agreement; a **Gemma** open-weight model running in **Ollama** on your laptop returns a plain-English checklist of clauses to negotiate. The PDF never leaves the machine.

**Not legal advice.** ClauseClear is a flag list, not a lawyer. A human still has to read the paper.

This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 2: Side Hustle](https://dev.to/challenges/hacktoberfest-week2-2026-10-12).

## Why this exists

A 15-minute lawyer skim of a freelance agreement is often more expensive than the first invoice. Cloud legal-AI tools want the full contract uploaded. ClauseClear is the side hustle in between: cheap enough to sell, private enough to use on a real NDA.

The product is the **validator**, not the chatbot. Every quote the model cites has to appear in the contract. Small local models paraphrase; ClauseClear snaps those paraphrases back to the nearest real sentence, or marks the finding `review`. A closed API that "sounds right" is worse than a 1B model you can check.

Measured on this laptop (no GPU, 16 GB RAM, Ollama 0.35): `gemma3:1b` reserved **880 MB** at a 4096-token context (`ollama ps`). The abusive sample (2,554 characters) returned **7 validated quotes, 0 review**, in **56s** over 2 attempts.

## Quick start

```bash
# 1. Local open-weight model (Gemma 3 1B fits a 16 GB laptop; 4B if you have RAM)
ollama serve
ollama pull gemma3:1b

# 2. App
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3a. CLI
python -m clauseclear samples/abusive_client_agreement.txt

# 3b. Browser UI
streamlit run app.py
```

Swap models without changing code:

```bash
export OLLAMA_MODEL=gemma3:4b   # or gemma2:2b, or any OpenAI-compatible tag
```

## What you get

- 4–6 findings: payment, IP, exclusivity, termination, late fees, scope, liability
- Each finding has a **verbatim quote**, why it matters, and a sentence you can send the client
- A draft negotiation email
- A markdown report you can download
- Optional Sentry traces that send **timings and categories only** — never the contract

## Prize categories this project actually uses

- **Best Use of Gemma** — inference is a local Gemma model via Ollama
- **Best Use of Sentry Agent Tracing** — optional, redacted spans around extract → infer → validate

No cloud LLM, no Atlas, no GPU droplet. That is the point of the side hustle: client paper stays on the laptop, so the unit economics are electricity rather than per-page API fees.

## Tests

```bash
pip install pytest
pytest -q
```

Tests cover quote matching and report text. They do not call the model.

## License

MIT. See [LICENSE](LICENSE).
