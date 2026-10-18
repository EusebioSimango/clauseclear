from clauseclear.report import build_email
from clauseclear.schema import Finding, ValidatedFinding


def test_email_lists_high_risk_asks():
    findings = [
        ValidatedFinding(
            finding=Finding(
                category="payment",
                risk="high",
                quote="Payment is due ninety (90) days after Client's written acceptance",
                why_it_matters="Ninety-day payment wrecks cash flow.",
                ask_instead="Pay 50% up front and the rest in 14 days.",
            ),
            status="ok",
        ),
        ValidatedFinding(
            finding=Finding(
                category="scope",
                risk="ok",
                quote="Contractor will perform design and frontend implementation work",
                why_it_matters="Scope is open-ended.",
                ask_instead="Cap revisions at two rounds.",
            ),
            status="ok",
        ),
    ]
    email = build_email(findings, "abusive_client_agreement.txt")
    assert "Pay 50% up front" in email
    assert "Cap revisions" not in email
