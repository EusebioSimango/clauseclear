from pathlib import Path

from clauseclear.schema import Analysis, Finding
from clauseclear.validate import quote_in_source, retry_instructions, validate_analysis

CONTRACT = Path("samples/abusive_client_agreement.txt").read_text(encoding="utf-8")


def test_quote_survives_whitespace_folding():
    quote = "Payment is due   ninety (90) days after Client's written acceptance"
    assert quote_in_source(quote, CONTRACT)


def test_paraphrase_is_rejected_as_verbatim_quote():
    assert not quote_in_source(
        "The freelancer must wait three months to get paid after delivery",
        CONTRACT,
    )


def test_paraphrase_snaps_to_real_payment_sentence():
    from clauseclear.validate import snap_quote_to_source

    snapped = snap_quote_to_source(
        "the freelancer waits ninety days after acceptance to get paid",
        CONTRACT,
    )
    assert snapped is not None
    assert "ninety (90) days" in snapped
    assert quote_in_source(snapped, CONTRACT)


def test_money_amount_snaps_even_when_the_rest_is_paraphrase():
    from clauseclear.validate import snap_quote_to_source

    contract = (
        "The Client agrees to pay the Contractor a fixed fee of $1,500.00 USD "
        "for the complete execution of the Services."
    )
    snapped = snap_quote_to_source(
        "The fixed fee of $1,500.00 USD is a bare minimum and does not protect against disputes.",
        contract,
    )
    assert snapped is not None
    assert "$1,500.00" in snapped


def test_unrelated_invention_does_not_snap():
    from clauseclear.validate import snap_quote_to_source

    assert snap_quote_to_source(
        "Contractor will transfer all cryptocurrency wallets to Client by Friday.",
        CONTRACT,
    ) is None


def test_fabricated_quote_marked_review():
    analysis = Analysis(
        summary="This agreement is heavily one-sided on payment, IP, and exit.",
        findings=[
            Finding(
                category="payment",
                risk="high",
                quote="Payment is due ninety (90) days after Client's written acceptance",
                why_it_matters="Ninety-day payment wrecks a freelancer's cash flow.",
                ask_instead="Please pay 40% on kickoff and the rest in 14 days.",
            ),
            Finding(
                category="exclusivity",
                risk="high",
                quote="Contractor shall never work for anyone else in this industry forever.",
                why_it_matters="A fake quote should not ship as if it were in the paper.",
                ask_instead="Please drop exclusivity or limit it to the project term.",
            ),
        ],
    )
    findings, issues = validate_analysis(analysis, CONTRACT)
    assert findings[0].status == "ok"
    assert findings[1].status == "review"
    assert findings[1].grounded is False
    assert "not found" in issues[0].reason
    text = retry_instructions(issues)
    assert "finding[1]" in text
