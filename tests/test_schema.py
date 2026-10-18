from clauseclear.schema import Analysis, coerce_analysis, coerce_category, coerce_risk


def test_pipe_union_category_becomes_first_label():
    assert (
        coerce_category(
            "payment|intellectual_property|exclusivity|termination|late_fees|scope|liability|other"
        )
        == "payment"
    )


def test_pipe_union_risk_becomes_first_label():
    assert coerce_risk("high|medium|low|ok") == "high"


def test_alias_maps_compensation_to_payment():
    assert coerce_category("Compensation & Payment Terms") == "payment"


def test_exact_error_payload_validates():
    payload = coerce_analysis(
        {
            "summary": "This audit agreement is mostly fair but still needs a human look at IP and liability.",
            "findings": [
                {
                    "category": "payment|intellectual_property|exclusivity|termination|late_fees|scope|liability|other",
                    "risk": "high|medium|low|ok",
                    "quote": "Final Balance: $1,000.00 USD due within 7 calendar days after delivery",
                    "why_it_matters": "Seven days after delivery is tight if the client delays review.",
                    "ask_instead": "Start the seven days when the report is delivered, not when it is accepted.",
                }
            ],
        }
    )
    analysis = Analysis.model_validate(payload)
    assert analysis.findings[0].category == "payment"
    assert analysis.findings[0].risk == "high"
