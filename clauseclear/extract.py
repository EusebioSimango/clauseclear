from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}


class ExtractError(ValueError):
    """Raised when a file cannot be turned into reviewable text."""


def extract_text(source: str | Path, raw: bytes | None = None, filename: str = "") -> str:
    """Pull plain text from a PDF/txt path or uploaded bytes. No model involved."""
    if raw is not None:
        name = filename.lower()
        if name.endswith(".pdf"):
            return _from_pdf_bytes(raw)
        return _clean(_decode(raw))

    path = Path(source)
    if not path.exists():
        raise ExtractError(f"file not found: {path}")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ExtractError(f"unsupported file type: {suffix or '(none)'}")
    if suffix == ".pdf":
        return _from_pdf_path(path)
    return _clean(path.read_text(encoding="utf-8", errors="replace"))


def _from_pdf_path(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # noqa: BLE001 - pypdf raises many types
        raise ExtractError(f"could not read PDF: {exc}") from exc
    pages = [_clean(page.extract_text() or "") for page in reader.pages]
    text = "\n\n".join(page for page in pages if page)
    if len(text) < 80:
        raise ExtractError("PDF did not contain enough extractable text")
    return text


def _from_pdf_bytes(raw: bytes) -> str:
    from io import BytesIO

    try:
        reader = PdfReader(BytesIO(raw))
    except Exception as exc:  # noqa: BLE001
        raise ExtractError(f"could not read PDF: {exc}") from exc
    pages = [_clean(page.extract_text() or "") for page in reader.pages]
    text = "\n\n".join(page for page in pages if page)
    if len(text) < 80:
        raise ExtractError("PDF did not contain enough extractable text")
    return text


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _clean(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    collapsed: list[str] = []
    blank = False
    for line in lines:
        if not line:
            if not blank:
                collapsed.append("")
            blank = True
            continue
        blank = False
        collapsed.append(line)
    return "\n".join(collapsed).strip()
