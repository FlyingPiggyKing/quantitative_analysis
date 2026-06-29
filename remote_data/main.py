"""Entry point for `python -m remote_data`.

Per the design doc §9 (Bootstrap), the main.py startup hook MUST call
`local_db.init()` BEFORE `scheduler.start()` so the scheduler never sees a
missing-table error. This is the safety net for users who run the daemon
directly without going through `init_local_db.py` first.
"""

from __future__ import annotations

import logging
import os
import signal
import sys

from remote_data.config import configure_logging, load_config, resolve_db_path
from remote_data.scheduler.jobs import build_scheduler
from remote_data.store import local_db

logger = logging.getLogger(__name__)


def _open_conn_factory(db_path):
    """Returns a no-arg callable that yields a fresh sqlite3 connection."""
    def _factory():
        return local_db.connect(db_path)
    return _factory


def main() -> int:
    cfg = load_config()
    configure_logging(cfg)
    logger.info(
        "remote_data starting role=%s symbols=%d ingest=%s",
        cfg.deploy_role, len(cfg.symbols), cfg.remote_ingest_url,
    )

    # 1. Apply schema BEFORE the scheduler starts (idempotent).
    db_path = resolve_db_path(cfg)
    local_db.init(db_path)
    conn_factory = _open_conn_factory(db_path)

    # 2. Optionally import + schedule the backfill job.
    backfill_runner = None
    try:
        from remote_data.jobs.backfill_fundamentals import maybe_backfill

        def _backfill():
            from remote_data.jobs.backfill_fundamentals import run_once as _bf_once
            conn = conn_factory()
            try:
                _bf_once(conn, cfg)
            finally:
                conn.close()

        backfill_runner = _backfill
    except ImportError:
        logger.debug("backfill module not yet implemented — skipping")

    # 3. Build + run scheduler.
    scheduler = build_scheduler(
        cfg, conn_factory=conn_factory, backfill_runner=backfill_runner,
    )

    # 4. Optional /health endpoint on 127.0.0.1:8001 — for ops / liveness probes.
    if os.getenv("ENABLE_HEALTH_ENDPOINT", "1") == "1":
        try:
            from remote_data import health as health_mod
            health_mod.start_in_background(cfg)
        except Exception as exc:
            logger.warning("could not start health endpoint: %s", exc)

    def _shutdown(signum, _frame):
        logger.info("received signal %s, shutting down", signum)
        try:
            scheduler.shutdown(wait=False)
        finally:
            sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("scheduler starting")
    scheduler.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())