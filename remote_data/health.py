"""Optional `/health` HTTP endpoint.

Binds to 127.0.0.1:8001 (configurable). Returns:
    {
      "status": "ok",
      "uptime_seconds": <int>,
      "last_successful_push": "<ISO8601 UTC>" | null,
      "pending": { "<data_type>": <count>, ... }
    }
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Optional

from remote_data.config import Config, load_config, resolve_db_path
from remote_data.store import local_db

logger = logging.getLogger(__name__)

_STARTED_AT = datetime.now(timezone.utc)


def _gather(conn: sqlite3.Connection) -> dict:
    last_push = conn.execute(
        "SELECT sent_at FROM push_log WHERE http_status BETWEEN 200 AND 299 "
        "ORDER BY sent_at DESC LIMIT 1"
    ).fetchone()
    pending = {}
    for t in local_db.all_business_tables():
        cur = conn.execute(
            f"SELECT COUNT(*) AS n FROM {t} "
            f"WHERE pushed_at IS NULL AND failed_at IS NULL"
        )
        pending[t] = cur.fetchone()["n"]
    return {
        "status": "ok",
        "uptime_seconds": int((datetime.now(timezone.utc) - _STARTED_AT).total_seconds()),
        "last_successful_push": last_push["sent_at"] if last_push else None,
        "pending": pending,
    }


class _HealthHandler(BaseHTTPRequestHandler):
    # Set by `make_server`.
    db_path: Optional[str] = None

    def log_message(self, format, *args):  # noqa: A002 — silence default logging
        pass

    def do_GET(self):  # noqa: N802
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return
        try:
            assert self.db_path is not None
            conn = local_db.connect(self.db_path)
            try:
                payload = _gather(conn)
            finally:
                conn.close()
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            logger.exception("health endpoint error: %s", exc)
            self.send_response(500)
            self.end_headers()


def make_server(
    cfg: Config,
    *,
    host: str = "127.0.0.1",
    port: int = 8001,
) -> ThreadingHTTPServer:
    db_path = resolve_db_path(cfg)
    _HealthHandler.db_path = db_path
    return ThreadingHTTPServer((host, port), _HealthHandler)


def start_in_background(
    cfg: Optional[Config] = None,
    *,
    host: str = "127.0.0.1",
    port: int = 8001,
) -> threading.Thread:
    """Start the health server in a daemon thread."""
    cfg = cfg or load_config()
    server = make_server(cfg, host=host, port=port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("health endpoint listening on http://%s:%d/health", host, port)
    return thread