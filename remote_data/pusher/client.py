"""HTTPS push client with retry/backoff.

Per `etf-pusher` spec:
- HTTPS only (HTTP URLs cause fatal error)
- Per-request timeout = HTTP_TIMEOUT_SECONDS
- Retry on 5xx, 408, 429, and network errors with 1s, 4s, 16s, 64s backoff
- Cap at 5 attempts per batch
- No retry on 4xx (except 408/429)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from remote_data.config import Config
from remote_data.pusher.signing import build_headers

logger = logging.getLogger(__name__)

RETRY_STATUSES = frozenset({408, 429, 500, 502, 503, 504})
NO_RETRY_STATUSES_PREFIX = (4,)  # any 4xx other than 408/429


@dataclass
class PushResult:
    ok: bool
    status_code: Optional[int]
    body: Optional[str]
    retries: int
    error: Optional[str] = None


class PushError(RuntimeError):
    pass


class HTTPSRequiredError(PushError):
    pass


def _backoff_schedule(max_attempts: int) -> list[float]:
    """1s, 4s, 16s, 64s, ... capped at max_attempts-1 (the first attempt has no delay)."""
    schedule = [0.0]
    delay = 1.0
    while len(schedule) < max_attempts:
        schedule.append(delay)
        delay *= 4
    return schedule


def post_batch(
    cfg: Config,
    body: bytes,
    *,
    max_attempts: int = 5,
) -> PushResult:
    """POST a single batch to REMOTE_INGEST_URL. Returns PushResult.

    Caller is responsible for marking rows pushed / dead-lettering on the
    returned `status_code` (use `client.classify` for the policy decision).
    """
    url = cfg.remote_ingest_url
    if not url.lower().startswith("https://"):
        raise HTTPSRequiredError(
            f"REMOTE_INGEST_URL must be HTTPS, got {url!r}"
        )

    ts, sig, headers = build_headers(cfg.etf_pipeline_secret, body)
    headers["Content-Length"] = str(len(body))
    timeout = cfg.http_timeout_seconds

    delays = _backoff_schedule(max_attempts)
    last_status: Optional[int] = None
    last_body: Optional[str] = None
    last_error: Optional[str] = None

    with httpx.Client(timeout=timeout) as client:
        for attempt, delay in enumerate(delays):
            if delay:
                logger.info(
                    "push retry %d/%d after %.1fs (last_status=%s)",
                    attempt + 1, max_attempts, delay, last_status,
                )
                time.sleep(delay)
            try:
                resp = client.post(url, content=body, headers=headers)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                last_status = None
                logger.warning("push network error on attempt %d: %s", attempt + 1, exc)
                continue

            last_status = resp.status_code
            last_body = resp.text
            if 200 <= resp.status_code < 300:
                return PushResult(
                    ok=True, status_code=resp.status_code, body=last_body,
                    retries=attempt, error=None,
                )

            if resp.status_code not in RETRY_STATUSES:
                # Non-retryable 4xx — surface immediately.
                return PushResult(
                    ok=False, status_code=resp.status_code, body=last_body,
                    retries=attempt, error=f"non-retryable status {resp.status_code}",
                )

            last_error = f"retryable status {resp.status_code}"
            logger.warning(
                "push got retryable status %d on attempt %d/%d",
                resp.status_code, attempt + 1, max_attempts,
            )

    return PushResult(
        ok=False, status_code=last_status, body=last_body,
        retries=max_attempts - 1, error=last_error or "max attempts exhausted",
    )


def classify(result: PushResult) -> str:
    """Return one of: 'success', 'retry_later', 'dead_letter'."""
    if result.ok:
        return "success"
    if result.status_code in RETRY_STATUSES or result.status_code is None:
        return "retry_later"
    if result.status_code and 400 <= result.status_code < 500:
        return "dead_letter"
    return "retry_later"