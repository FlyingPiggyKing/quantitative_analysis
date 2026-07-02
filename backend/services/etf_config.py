"""ETF pipeline configuration.

Loads the env vars documented in `etf-config` spec and validates them at
startup. The HMAC secret is the only required key; everything else has
defensible defaults. Log output uses a presence-only format for the secret
(NOT the value) per the spec.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class EtfConfig:
    pipeline_secret: str
    remote_db_path: str
    time_window_seconds: int
    ingest_max_requests_per_day: int
    ingest_max_body_bytes: int
    rate_limit_flush_seconds: int


_cached: EtfConfig | None = None


def _load() -> EtfConfig:
    secret = os.getenv("ETF_PIPELINE_SECRET", "").strip()
    if not secret:
        # Fail-fast. The presence-only message is safe to surface in logs.
        print("[etf-config] ETF_PIPELINE_SECRET: <missing>", file=sys.stderr)
        raise SystemExit(
            "ETF_PIPELINE_SECRET is not set. The ETF ingest endpoint refuses "
            "to start without a shared secret. Set it in backend/.env."
        )
    return EtfConfig(
        pipeline_secret=secret,
        remote_db_path=os.getenv("REMOTE_DB_PATH", "./data/etf_remote.db"),
        time_window_seconds=int(os.getenv("TIME_WINDOW_SECONDS", "300")),
        ingest_max_requests_per_day=int(os.getenv("INGEST_MAX_REQUESTS_PER_DAY", "50000")),
        ingest_max_body_bytes=int(os.getenv("INGEST_MAX_BODY_BYTES", "1048576")),
        rate_limit_flush_seconds=int(os.getenv("RATE_LIMIT_FLUSH_SECONDS", "60")),
    )


def get_etf_config() -> EtfConfig:
    """Return the cached config. Reload via `reset_for_test()` in tests."""
    global _cached
    if _cached is None:
        _cached = _load()
    return _cached


def validate() -> None:
    """Validate config at startup. Logs presence of the secret only — never the value."""
    cfg = _load()
    print(f"[etf-config] ETF_PIPELINE_SECRET: <set> (length={len(cfg.pipeline_secret)})")
    print(f"[etf-config] REMOTE_DB_PATH={cfg.remote_db_path}")
    print(f"[etf-config] TIME_WINDOW_SECONDS={cfg.time_window_seconds}")
    print(f"[etf-config] INGEST_MAX_REQUESTS_PER_DAY={cfg.ingest_max_requests_per_day}")
    print(f"[etf-config] INGEST_MAX_BODY_BYTES={cfg.ingest_max_body_bytes}")
    print(f"[etf-config] RATE_LIMIT_FLUSH_SECONDS={cfg.rate_limit_flush_seconds}")


def reset_for_test() -> None:
    """Clear the cached config. Tests use this to pick up new env values."""
    global _cached
    _cached = None
