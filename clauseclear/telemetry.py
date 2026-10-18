from __future__ import annotations

import hashlib
import os
from contextlib import contextmanager
from typing import Iterator

import sentry_sdk
from sentry_sdk.types import Event, Hint

_booted = False


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _strip_pii(event: Event, hint: Hint) -> Event | None:
    """Never send contract text, quotes, filenames, or prompts to Sentry."""
    del hint
    event.pop("breadcrumbs", None)
    extra = event.get("extra") or {}
    for key in list(extra):
        if key.lower() in {"quote", "contract", "source", "prompt", "filename", "text"}:
            extra[key] = "[redacted]"
    event["extra"] = extra
    if "request" in event:
        event["request"] = {"url": "local://clauseclear"}
    return event


def init_sentry() -> bool:
    global _booted
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn or _booted:
        return bool(dsn)
    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "1.0")),
        send_default_pii=False,
        before_send=_strip_pii,
        before_send_transaction=_strip_pii,
    )
    _booted = True
    return True


@contextmanager
def span(name: str, **tags: str | int | float) -> Iterator[None]:
    init_sentry()
    with sentry_sdk.start_span(op="clauseclear", name=name) as current:
        for key, value in tags.items():
            current.set_tag(key, str(value))
        yield


def hash_source(source: str) -> str:
    return _fingerprint(source)
