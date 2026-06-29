"""APScheduler wiring + per-data-type fetch jobs + push loop.

Per `etf-scheduler` spec:
- One in-process scheduler (no systemd timers, no Celery)
- A job that raises MUST be caught, logged, and the scheduler continues
- The push loop runs as its own job, decoupled from fetch cadence
"""

from __future__ import annotations

import logging
import sqlite3
import traceback
from datetime import datetime
from typing import Callable, Iterable, List, Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from remote_data.config import Config, load_config
from remote_data.fetcher import (
    fetch_equity_holdings,
    fetch_esg,
    fetch_fundamentals,
    fetch_holdings,
    fetch_news,
    fetch_performance,
    fetch_quotes,
    fetch_sector_weightings,
)
from remote_data.store import local_db

logger = logging.getLogger(__name__)


# Map (data_type -> (fetcher_fn, inserter)).
_FETCH_TABLE = {
    "etf_quote": (fetch_quotes, local_db.insert_etf_quote),
    "etf_fundamentals": (fetch_fundamentals, local_db.insert_etf_fundamentals),
    "etf_holdings": (fetch_holdings, local_db.insert_etf_holdings),
    "etf_sector_weights": (fetch_sector_weightings, local_db.insert_etf_sector_weights),
    "etf_performance": (fetch_performance, local_db.insert_etf_performance),
    "etf_equity_holdings": (fetch_equity_holdings, local_db.insert_etf_equity_holdings),
    "etf_esg": (fetch_esg, local_db.insert_etf_esg),
    "etf_news": (fetch_news, local_db.insert_etf_news),
}


def safe_run(
    conn: sqlite3.Connection,
    data_type: str,
    fn: Callable[..., List[dict]],
    inserter: Callable[..., int],
    *,
    symbols: List[str],
) -> None:
    """Run `fn` with `symbols`, write results to the store, log to fetch_log.

    Catches every exception so the scheduler never dies (per spec §"Scheduler
    is single-process and resilient to job failure").
    """
    logger.info("fetch start data_type=%s symbols=%d", data_type, len(symbols))
    try:
        records = fn(symbols) if data_type != "etf_news" else fn(symbols, since=None)
    except Exception as exc:
        logger.error(
            "fetch failed data_type=%s: %s\n%s",
            data_type, exc, traceback.format_exc(),
        )
        local_db.record_fetch(
            conn, data_type=data_type, symbol=None, status="error",
            error=str(exc), row_count=None,
        )
        return

    try:
        n = inserter(conn, records)
    except Exception as exc:
        logger.error(
            "store insert failed data_type=%s: %s\n%s",
            data_type, exc, traceback.format_exc(),
        )
        local_db.record_fetch(
            conn, data_type=data_type, symbol=None, status="error",
            error=str(exc), row_count=None,
        )
        return

    local_db.record_fetch(
        conn, data_type=data_type, symbol=None, status="ok",
        error=None, row_count=n,
    )
    logger.info("fetch done data_type=%s inserted=%d", data_type, n)


def make_fetch_job(
    data_type: str,
    *,
    conn_factory: Callable[[], sqlite3.Connection],
    cfg: Config,
) -> Callable[[], None]:
    fetcher_fn, inserter = _FETCH_TABLE[data_type]
    symbols = cfg.symbols

    def _job() -> None:
        conn = conn_factory()
        try:
            safe_run(conn, data_type, fetcher_fn, inserter, symbols=symbols)
        finally:
            conn.close()

    return _job


def make_push_job(
    *,
    conn_factory: Callable[[], sqlite3.Connection],
    cfg: Config,
) -> Callable[[], None]:
    """Push loop — runs every cfg.push_interval_seconds, drains pending rows."""
    from remote_data.pusher.loop import run_once

    def _job() -> None:
        conn = conn_factory()
        try:
            summary = run_once(conn, cfg)
            if summary["pushed"] or summary["dead_lettered"] or summary["retried"]:
                logger.info(
                    "push loop: pushed=%d dead_lettered=%d retried=%d",
                    summary["pushed"], summary["dead_lettered"], summary["retried"],
                )
        except Exception as exc:
            logger.error(
                "push loop failed: %s\n%s", exc, traceback.format_exc(),
            )
        finally:
            conn.close()

    return _job


def market_status(now: datetime, tz_name: str = "US/Eastern") -> str:
    """Return one of: 'pre', 'open', 'post', 'closed'."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:  # py<3.9, but pyproject requires 3.11
        from backports.zoneinfo import ZoneInfo  # type: ignore
    local = now.astimezone(ZoneInfo(tz_name))
    minutes = local.hour * 60 + local.minute
    weekday = local.weekday()  # 0=Mon, 6=Sun
    if weekday >= 5:
        return "closed"
    if 240 <= minutes < 570:    # 04:00 – 09:30 ET
        return "pre"
    if 570 <= minutes < 960:    # 09:30 – 16:00 ET
        return "open"
    if 960 <= minutes < 1200:   # 16:00 – 20:00 ET
        return "post"
    return "closed"


def quote_interval_minutes(cfg: Config, now: datetime) -> int:
    """Pick the configured interval based on market session."""
    status = market_status(now, cfg.market_tz)
    if status == "open":
        return cfg.fetch_quotes_interval_minutes
    if status in ("pre", "post"):
        return cfg.fetch_quotes_offhours_interval_minutes
    return cfg.fetch_quotes_offhours_interval_minutes


# ---------------------------------------------------------------------------
# Scheduler construction
# ---------------------------------------------------------------------------


def build_scheduler(
    cfg: Config,
    *,
    conn_factory: Callable[[], sqlite3.Connection],
    backfill_runner: Optional[Callable[[sqlite3.Connection], None]] = None,
) -> BlockingScheduler:
    """Build (but do not start) the BlockingScheduler with all jobs wired.

    Caller is responsible for `scheduler.start()`.
    """
    scheduler = BlockingScheduler(timezone=cfg.market_tz)

    # Push loop — independent cadence
    push_job = make_push_job(conn_factory=conn_factory, cfg=cfg)
    scheduler.add_job(
        push_job,
        IntervalTrigger(seconds=cfg.push_interval_seconds),
        id="push_loop",
        max_instances=1,
        coalesce=True,
    )

    # Fetchers
    fetch_quotes_job = make_fetch_job(
        "etf_quote", conn_factory=conn_factory, cfg=cfg
    )
    scheduler.add_job(
        fetch_quotes_job,
        IntervalTrigger(minutes=cfg.fetch_quotes_interval_minutes),
        id="fetch_quotes_market",
        max_instances=1,
        coalesce=True,
    )

    fetch_news_job = make_fetch_job(
        "etf_news", conn_factory=conn_factory, cfg=cfg
    )
    scheduler.add_job(
        fetch_news_job,
        IntervalTrigger(minutes=cfg.fetch_news_interval_minutes),
        id="fetch_news",
        max_instances=1,
        coalesce=True,
    )

    # Daily EOD jobs
    fetch_fundamentals_job = make_fetch_job(
        "etf_fundamentals", conn_factory=conn_factory, cfg=cfg
    )
    scheduler.add_job(
        fetch_fundamentals_job,
        CronTrigger(hour=16, minute=40, timezone=cfg.market_tz),
        id="fetch_fundamentals",
        max_instances=1,
        coalesce=True,
    )

    fetch_performance_job = make_fetch_job(
        "etf_performance", conn_factory=conn_factory, cfg=cfg
    )
    scheduler.add_job(
        fetch_performance_job,
        CronTrigger(hour=16, minute=45, timezone=cfg.market_tz),
        id="fetch_performance",
        max_instances=1,
        coalesce=True,
    )

    # Weekly Sunday jobs
    fetch_holdings_job = make_fetch_job(
        "etf_holdings", conn_factory=conn_factory, cfg=cfg
    )
    scheduler.add_job(
        fetch_holdings_job,
        CronTrigger(day_of_week="sun", hour=10, minute=0, timezone=cfg.market_tz),
        id="fetch_holdings",
        max_instances=1,
        coalesce=True,
    )

    fetch_sw_job = make_fetch_job(
        "etf_sector_weights", conn_factory=conn_factory, cfg=cfg
    )
    scheduler.add_job(
        fetch_sw_job,
        CronTrigger(day_of_week="sun", hour=10, minute=15, timezone=cfg.market_tz),
        id="fetch_sector_weights",
        max_instances=1,
        coalesce=True,
    )

    fetch_eh_job = make_fetch_job(
        "etf_equity_holdings", conn_factory=conn_factory, cfg=cfg
    )
    scheduler.add_job(
        fetch_eh_job,
        CronTrigger(day_of_week="sun", hour=10, minute=30, timezone=cfg.market_tz),
        id="fetch_equity_holdings",
        max_instances=1,
        coalesce=True,
    )

    # Monthly ESG
    fetch_esg_job = make_fetch_job(
        "etf_esg", conn_factory=conn_factory, cfg=cfg
    )
    scheduler.add_job(
        fetch_esg_job,
        CronTrigger(day=1, hour=10, minute=0, timezone=cfg.market_tz),
        id="fetch_esg",
        max_instances=1,
        coalesce=True,
    )

    # Prune daily
    def _prune_job() -> None:
        conn = conn_factory()
        try:
            counts = local_db.prune(conn)
            logger.info("prune done: %s", counts)
        except Exception as exc:
            logger.error("prune failed: %s\n%s", exc, traceback.format_exc())
        finally:
            conn.close()

    scheduler.add_job(
        _prune_job,
        CronTrigger(hour=17, minute=0, timezone=cfg.market_tz),
        id="prune",
        max_instances=1,
        coalesce=True,
    )

    # Backfill — runs once on startup, then never again.
    if backfill_runner:
        scheduler.add_job(
            backfill_runner,
            "date",  # fire once, run_at=now
            id="backfill",
            max_instances=1,
            coalesce=True,
        )

    return scheduler