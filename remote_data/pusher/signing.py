"""HMAC-SHA256 signing for push requests.

Per `etf-pusher` spec:
    to_sign = timestamp_utf8 + b"\\n" + body_utf8
    signature = hmac.new(secret, to_sign, hashlib.sha256).hexdigest()
Headers sent on every request:
    X-ETF-Pipeline-Timestamp: <ISO8601 UTC>
    X-ETF-Pipeline-Signature: <hex>
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sign(secret: str, timestamp: str, body: bytes | str) -> str:
    """Return the hex HMAC-SHA256 signature for `(timestamp + body)`."""
    body_bytes = body.encode("utf-8") if isinstance(body, str) else body
    to_sign = timestamp.encode("utf-8") + b"\n" + body_bytes
    return hmac.new(secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()


def within_window(timestamp: str, *, now: datetime | None = None, window_seconds: int = 300) -> bool:
    """Verify `timestamp` is within ±`window_seconds` of `now` (UTC).

    Used on the receiver side; kept here so both sides share the implementation.
    """
    sent = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    return abs((now - sent).total_seconds()) <= window_seconds


def build_headers(secret: str, body: bytes | str) -> tuple[str, str, dict[str, str]]:
    """Return (timestamp, signature, headers_dict)."""
    ts = now_utc_iso()
    sig = sign(secret, ts, body)
    headers = {
        "Content-Type": "application/json",
        "X-ETF-Pipeline-Timestamp": ts,
        "X-ETF-Pipeline-Signature": sig,
    }
    return ts, sig, headers