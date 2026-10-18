from pathlib import Path

from clauseclear.extract import extract_text

SAMPLE = Path("samples/fair_agreement.txt")


def test_extract_plain_text():
    text = extract_text(SAMPLE)
    assert "River Studio Ltd" in text
    assert "fourteen (14) days" in text


def test_extract_from_bytes_matches_path():
    raw = SAMPLE.read_bytes()
    assert "portfolio" in extract_text("", raw=raw, filename="fair_agreement.txt").lower()
