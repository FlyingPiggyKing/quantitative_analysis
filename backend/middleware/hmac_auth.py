"""HMAC-SHA256 + timestamp-window middleware.

Protects `POST /api/etf/ingest` (and any sub-paths under it). The signature
is `HMAC_SHA256(secret, timestamp + "\n" + body)`. Any failure → 401 with
`{"detail": "unauthorized"}` and NO log to `etf_ingest_log` (anti-pollution).

This is registered as a global middleware but is a no-op for any path that
isn't the ingest endpoint — read endpoints, `/docs`, `/health` are not
touched.
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.services.etf_config import get_etf_config

_INGEST_PREFIX = "/api/etf/ingest"


def _is_ingest_path(path: str) -> bool:
    """True for `/api/etf/ingest` or any sub-path like `/api/etf/ingest/v2`."""
    return path == _INGEST_PREFIX or path.startswith(_INGEST_PREFIX + "/")


def _parse_timestamp(ts: str) -> datetime | None:
    """Parse an ISO8601 UTC timestamp like `2026-06-29T03:14:00Z`. None on error."""
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def verify_signature(secret: str, timestamp: str, body: bytes, provided_sig: str) -> bool:
    """Compute the expected HMAC and compare in constant time.

    Returns False on any malformed input. The caller treats False as 401.
    """
    if not provided_sig or not timestamp:
        return False
    msg = timestamp.encode("utf-8") + b"\n" + body
    expected = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_sig)


def verify_timestamp(ts_str: str, window_seconds: int) -> bool:
    """True if |now_utc - ts| <= window_seconds (anti-replay in both directions)."""
    ts = _parse_timestamp(ts_str)
    if ts is None:
        return False
    delta = abs((datetime.now(timezone.utc) - ts).total_seconds())
    return delta <= window_seconds


class HmacAuthMiddleware(BaseHTTPMiddleware):
    """Scopable HMAC middleware. No-op on non-ingest paths."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method != "POST" or not _is_ingest_path(request.url.path):
            return await call_next(request)

        cfg = get_etf_config()
        ts_header = request.headers.get("X-ETF-Pipeline-Timestamp", "")
        sig_header = request.headers.get("X-ETF-Pipeline-Signature", "")

        if not ts_header or not sig_header:
            return _unauthorized()

        # Body is cached by Starlette so downstream handlers can re-read it.
        body = await request.body()

        if not verify_timestamp(ts_header, cfg.time_window_seconds):
            return _unauthorized()
        if not verify_signature(cfg.pipeline_secret, ts_header, body, sig_header):
            return _unauthorized()

        return await call_next(request)


def _unauthorized() -> JSONResponse:
    return JSONResponse({"detail": "unauthorized"}, status_code=401)
