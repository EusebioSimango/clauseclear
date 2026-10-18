from __future__ import annotations

from pathlib import Path

import streamlit as st

from clauseclear import DEFAULT_MODEL, FALLBACK_MODELS
from clauseclear.extract import ExtractError
from clauseclear.model import ModelError, configured_model
from clauseclear.pipeline import review_bytes, review_text
from clauseclear.report import to_markdown
from clauseclear.telemetry import init_sentry

SAMPLE_DIR = Path(__file__).resolve().parent / "samples"
RISK_COLOR = {"high": "#b42318", "medium": "#b54708", "low": "#175cd3", "ok": "#027a48"}

st.set_page_config(page_title="ClauseClear", page_icon="C", layout="wide")
init_sentry()

st.title("ClauseClear")
st.caption(
    "A local contract checklist for freelancers. "
    "Your client's agreement is sent only to a model running on this machine."
)
st.info(
    "Not legal advice. ClauseClear flags clauses a human should still read. "
    "Nothing is uploaded unless you set an optional Sentry DSN, and even then "
    "contract text is stripped."
)

with st.sidebar:
    st.header("Local model")
    model = st.selectbox(
        "Ollama tag",
        options=list(dict.fromkeys((configured_model(), DEFAULT_MODEL, *FALLBACK_MODELS))),
        index=0,
    )
    st.markdown(
        "Start the model with `ollama serve` and `ollama pull gemma3:1b`. "
        "Swap tags anytime — the product does not depend on a vendor API."
    )
    sample_name = st.selectbox(
        "Load a sample",
        options=["(none)", "abusive_client_agreement.txt", "fair_agreement.txt"],
    )

pasted = ""
if sample_name != "(none)":
    pasted = (SAMPLE_DIR / sample_name).read_text(encoding="utf-8")

uploaded = st.file_uploader("PDF or .txt contract", type=["pdf", "txt", "md"])
text = st.text_area("Or paste the agreement", value=pasted, height=280)

run = st.button("Review on this laptop", type="primary")

if run:
    try:
        if uploaded is not None:
            report = review_bytes(uploaded.getvalue(), uploaded.name, model=model)
        else:
            report = review_text(text, source_name="pasted.txt", model=model)
    except (ExtractError, ModelError, ValueError) as exc:
        st.error(str(exc))
        st.stop()

    ok = sum(1 for item in report.findings if item.status == "ok")
    review_n = sum(1 for item in report.findings if item.status == "review")
    high = sum(1 for item in report.findings if item.finding.risk == "high")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Validated quotes", ok)
    c2.metric("Need review", review_n)
    c3.metric("High-risk flags", high)
    c4.metric("Time", f"{report.elapsed_seconds:.1f}s")

    st.subheader("Plain-English summary")
    st.write(report.summary)

    st.subheader("Clauses to negotiate")
    for item in report.findings:
        color = RISK_COLOR[item.finding.risk]
        badge = item.finding.risk.upper() if item.status == "ok" else "QUOTE NOT IN CONTRACT"
        st.markdown(
            f"**{item.finding.category.replace('_', ' ').title()}** "
            f"<span style='color:{color};font-weight:600'>{badge}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(f"> {item.finding.quote}")
        st.write(f"**Why it matters:** {item.finding.why_it_matters}")
        st.write(f"**Ask instead:** {item.finding.ask_instead}")
        if item.grounded:
            st.caption("Quote grounded to the nearest sentence in the contract.")
        if item.issues:
            st.caption("Validator: " + "; ".join(item.issues))
        st.divider()

    st.subheader("Email you can send")
    st.code(report.negotiation_email, language=None)
    st.download_button(
        "Download markdown report",
        data=to_markdown(report),
        file_name="clauseclear-report.md",
        mime="text/markdown",
    )
    st.caption(report.disclaimer)
