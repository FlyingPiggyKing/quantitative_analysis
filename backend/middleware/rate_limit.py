"""Per-IP sliding-window rate limit for the ingest endpoint.

The 24h window is implemented as a (window_start, count) counter per IP
— fixed-window is simpler and indistinguishable from true sliding at the
real traffic profile. State lives in a module-level dict guarded by a lock
and is persisted to `rate_limit_state` every `RATE_LIMIT_FLUSH_SECONDS` by
a background thread so a backend restart doesn't reset the counter.

Scoping: only `POST /api/etf/ingest` (and any sub-path) is rate-limited.
Read endpoints under `/api/etf/` are not limited.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.services.etf_config import get_etf_config
from backend.services.etf_db import get_conn

_INGEST_PREFIX = "/api/etf/ingest"
_WINDOW_SECONDS = 24 * 60 * 60


class _Counter:
    __slots__ = ("window_start", "count")

    def __init__(self, window_start: float, count: int) -> None:
        self.window_start = window_start
        self.count = count


# Module-level state shared by the middleware and the background flusher.
# Module globals are fine for a single-process FastAPI deployment (the spec
# explicitly rules out multi-region / distributed rate-limit infra).
_state: dict[str, _Counter] = {}
_lock = threading.Lock()
_loaded = False


def _ensure_loaded() -> None:
    """Populate `_state` from `rate_limit_state` once per process."""
    global _loaded
    if _loaded:
        return
    with _lock:
        if _loaded:
            return
        try:
            conn = get_conn()
            try:
                rows = conn.execute(
                    "SELECT ip, window_start, count FROM rate_limit_state"
                ).fetchall()
            finally:
                conn.close()
            now = time.time()
            for row in rows:
                ws = float(row["window_start"])
                # Discard entries whose window already expired.
                if now - ws < _WINDOW_SECONDS:
                    _state[row["ip"]] = _Counter(ws, int(row["count"]))
        except Exception:
            # First run — table may not exist yet, init() will create it.
            pass
        _loaded = True


def _flush() -> None:
    """Snapshot the in-memory state and persist to `rate_limit_state`."""
    with _lock:
        snapshot = [(ip, c.window_start, c.count) for ip, c in _state.items()]
    if not snapshot:
        return
    try:
        conn = get_conn()
        try:
            for ip, ws, count in snapshot:
                conn.execute(
                    "INSERT INTO rate_limit_state(ip, window_start, count) VALUES(?, ?, ?) "
                    "ON CONFLICT(ip) DO UPDATE SET window_start = excluded.window_start, "
                    "count = excluded.count",
                    (ip, ws, count),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[rate-limit] flush failed: {exc}")


def check_and_increment(ip: str, limit: int) -> bool:
    """True if the request is within the limit. Always increments the counter."""
    _ensure_loaded()
    now = time.time()
    with _lock:
        c = _state.get(ip)
        if c is None or now - c.window_start >= _WINDOW_SECONDS:
            c = _Counter(now, 1)
        else:
            c.count += 1
        _state[ip] = c
        return c.count <= limit


def log_rate_limited(ip: str) -> None:
    """Write a row to `etf_ingest_log` with data_type='rate_limited'."""
    try:
        conn = get_conn()
        try:
            conn.execute(
                "INSERT INTO etf_ingest_log"
                "(batch_id, data_type, source_ip, accepted, rejected, received_at) "
                "VALUES(?, ?, ?, ?, ?, ?)",
                (
                    None,
                    "rate_limited",
                    ip,
                    0,
                    0,
                    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[rate-limit] log write failed: {exc}")


def get_source_ip(request: Request) -> str:
    """Resolve the source IP.

    Priority per spec: leftmost (original client) of `X-Forwarded-For`,
    then socket `remote_addr`. The fallback covers direct connections
    without a reverse proxy.
    """
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        first = xff.split(",", 1)[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method != "POST" or not request.url.path.startswith(_INGEST_PREFIX):
            return await call_next(request)
        cfg = get_etf_config()
        ip = get_source_ip(request)
        if not check_and_increment(ip, cfg.ingest_max_requests_per_day):
            log_rate_limited(ip)
            return JSONResponse(
                {"detail": "rate limit exceeded"},
                status_code=429,
            )
        return await call_next(request)


# --- Background flusher ---

_flusher_thread: Optional[threading.Thread] = None
_flusher_stop = threading.Event()


def start_flusher() -> None:
    """Start the background flusher thread. Idempotent."""
    global _flusher_thread
    if _flusher_thread and _flusher_thread.is_alive():
        return
    _flusher_stop.clear()
    cfg = get_etf_config()
    interval = max(1, cfg.rate_limit_flush_seconds)

    def loop() -> None:
        while not _flusher_stop.is_set():
            # Event.wait is interruptible — cleaner than time.sleep.
            if _flusher_stop.wait(timeout=interval):
                break
            try:
                _flush()
            except Exception as exc:  # pragma: no cover - defensive
                print(f"[rate-limit] flusher iteration failed: {exc}")

    _flusher_thread = threading.Thread(
        target=loop, name="etf-rate-limit-flusher", daemon=True
    )
    _flusher_thread.start()


def stop_flusher() -> None:
    """Stop the flusher. Best-effort: bounded join so shutdown isn't blocked."""
    global _flusher_thread
    _flusher_stop.set()
    if _flusher_thread:
        _flusher_thread.join(timeout=2)
        _flusher_thread = None


def _reset_for_test() -> None:
    """Clear in-memory state and the loaded flag. Tests only."""
    global _loaded
    with _lock:
        _state.clear()
    _loaded = False
