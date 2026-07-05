"""Configuration loader for remote_data.

Reads `.env` from the package directory (or any path in `ENV_FILE`), validates
required keys, and exposes a typed `Config` object for the rest of the pipeline.

Contract: see openspec/changes/etf-fetcher-pusher/specs/etf-config/spec.md
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Resolve the package directory once at import time so callers (init scripts,
# main.py) can call `load_config()` without thinking about CWD.
_PACKAGE_DIR = Path(__file__).resolve().parent
_DEFAULT_ENV_FILE = _PACKAGE_DIR / ".env"

DEFAULT_SYMBOLS: List[str] = [
    "QQQ", "IVV", "SPY", "VTI", "VOO", "QQQM", "SCHB", "ITOT",
    "VEA", "VWO", "BND", "AGG", "TLT", "IEF",
    "GLD", "SLV", "USO", "UNG", "ARKK", "SOXX",
]


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    deploy_role: str
    remote_ingest_url: str
    etf_pipeline_secret: str

    local_db_path: str
    time_window_seconds: int
    http_timeout_seconds: int
    yahooquery_max_retries: int
    yahooquery_backoff_seconds: int

    symbols: List[str]

    fetch_quotes_interval_minutes: int
    fetch_quotes_offhours_interval_minutes: int
    push_interval_seconds: int
    batch_size: int

    market_tz: str
    log_level: str
    log_file: str

    package_dir: Path = field(default=_PACKAGE_DIR)


def _split_symbols(raw: str) -> List[str]:
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(
            f"Missing required env var {name}. "
            f"Set it in {_DEFAULT_ENV_FILE} or your shell environment."
        )
    return value


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def _str(name: str, default: str) -> str:
    return os.getenv(name, default)


def load_config(env_file: Path | str | None = None) -> Config:
    """Load + validate config from `.env` and the process environment.

    Args:
        env_file: Optional explicit path to an env file. If None, defaults to
            `<package_dir>/.env`.
    """
    target = Path(env_file) if env_file else _DEFAULT_ENV_FILE
    if target.exists():
        load_dotenv(target, override=False)
    else:
        logger.debug("No env file at %s; relying on process env", target)

    deploy_role = _require("DEPLOY_ROLE")
    if deploy_role != "LOCAL":
        raise ConfigError(
            f"DEPLOY_ROLE must be 'LOCAL' for this pipeline, got {deploy_role!r}"
        )

    url = _require("REMOTE_INGEST_URL")
    if not url.lower().startswith("https://"):
        # Per spec: HTTP-only URLs are fatal at startup. Surfacing here gives a
        # clearer error than the pusher refusing later.
        raise ConfigError(
            f"REMOTE_INGEST_URL must be HTTPS, got {url!r}"
        )

    secret = _require("ETF_PIPELINE_SECRET")
    if len(secret) < 16:
        raise ConfigError(
            "ETF_PIPELINE_SECRET should be at least 16 characters (32+ recommended)"
        )

    symbols_raw = _str("SYMBOLS", "")
    symbols = _split_symbols(symbols_raw) if symbols_raw else list(DEFAULT_SYMBOLS)

    return Config(
        deploy_role=deploy_role,
        remote_ingest_url=url,
        etf_pipeline_secret=secret,
        local_db_path=_str("LOCAL_DB_PATH", "data/etf_local.db"),
        time_window_seconds=_int("TIME_WINDOW_SECONDS", 300),
        http_timeout_seconds=_int("HTTP_TIMEOUT_SECONDS", 15),
        yahooquery_max_retries=_int("YAHOOQUERY_MAX_RETRIES", 3),
        yahooquery_backoff_seconds=_int("YAHOOQUERY_BACKOFF_SECONDS", 2),
        symbols=symbols,
        fetch_quotes_interval_minutes=_int("FETCH_QUOTES_INTERVAL_MINUTES", 5),
        fetch_quotes_offhours_interval_minutes=_int(
            "FETCH_QUOTES_OFFHOURS_INTERVAL_MINUTES", 30
        ),
        push_interval_seconds=_int("PUSH_INTERVAL_SECONDS", 30),
        batch_size=_int("BATCH_SIZE", 500),
        market_tz=_str("MARKET_TZ", "US/Eastern"),
        log_level=_str("LOG_LEVEL", "INFO"),
        log_file=_str("LOG_FILE", "data/etf_local.log"),
    )


def resolve_db_path(cfg: Config) -> Path:
    """Resolve LOCAL_DB_PATH against CWD or the package directory, in that order."""
    raw = Path(cfg.local_db_path)
    if raw.is_absolute():
        return raw
    if raw.exists():
        return raw.resolve()
    # Default fallback: relative to package dir so the daemon finds the DB
    # even when launched from elsewhere via `python -m remote_data`.
    return (_PACKAGE_DIR / raw).resolve()


def configure_logging(cfg: Config) -> None:
    """Configure root logger with a rotating file handler + stdout."""
    from logging.handlers import RotatingFileHandler

    level = getattr(logging, cfg.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    # Avoid stacking handlers on re-init.
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)

    log_path = Path(cfg.log_file)
    if not log_path.is_absolute():
        log_path = _PACKAGE_DIR / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    fh = RotatingFileHandler(
        log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)