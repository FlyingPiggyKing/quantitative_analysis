"""Push loop: groups pending rows by data_type, ships batches, marks pushed or dead-letters 4xx."""

from __future__ import annotations

import logging
import sqlite3
from typing import List, Optional

from remote_data.config import Config, load_config
from remote_data.pusher import client as push_client
from remote_data.pusher.payload import build_body
from remote_data.store import local_db

logger = logging.getLogger(__name__)


def _row_ids(rows) -> List[int]:
    return [r["id"] for r in rows]


def run_once(
    conn: sqlite3.Connection,
    cfg: Optional[Config] = None,
) -> dict:
    """One pass: drain pending rows for each data_type. Returns a summary dict."""
    cfg = cfg or load_config()
    summary: dict = {"pushed": 0, "dead_lettered": 0, "retried": 0, "by_type": {}}

    for data_type in local_db.all_business_tables():
        try:
            pending = local_db.fetch_pending(conn, data_type, limit=cfg.batch_size)
        except Exception as exc:
            logger.warning("fetch_pending failed for %s: %s", data_type, exc)
            continue
        if not pending:
            continue

        ids = _row_ids(pending)
        # Convert sqlite3.Row to dict so payload.serialize_records can iterate keys.
        dict_rows = [dict(r) for r in pending]
        body = build_body(data_type, dict_rows)

        logger.info(
            "push start data_type=%s rows=%d body=%d bytes",
            data_type, len(pending), len(body),
        )

        try:
            result = push_client.post_batch(cfg, body)
        except push_client.HTTPSRequiredError as exc:
            logger.error("fatal: %s", exc)
            raise

        verdict = push_client.classify(result)
        local_db.record_push_attempt(
            conn,
            data_type=data_type,
            batch_id=None,
            http_status=result.status_code,
            retry_count=result.retries,
            error=result.error,
            row_count=len(pending),
        )

        if verdict == "success":
            local_db.mark_pushed(conn, data_type, ids)
            summary["pushed"] += len(pending)
            summary["by_type"][data_type] = len(pending)
            logger.info(
                "push success data_type=%s rows=%d status=%d retries=%d",
                data_type, len(pending), result.status_code, result.retries,
            )
        elif verdict == "dead_letter":
            local_db.write_dead_letter(
                conn,
                data_type=data_type,
                source_ids=ids,
                batch_id=None,
                response_status=result.status_code,
                response_body=result.body,
            )
            summary["dead_lettered"] += len(pending)
            summary["by_type"][data_type] = len(pending)
            logger.error(
                "push dead_letter data_type=%s rows=%d status=%d body=%r",
                data_type, len(pending), result.status_code,
                (result.body or "")[:300],
            )
        else:  # retry_later
            summary["retried"] += len(pending)
            summary["by_type"][data_type] = len(pending)
            logger.warning(
                "push retry_later data_type=%s rows=%d status=%s",
                data_type, len(pending), result.status_code,
            )

    return summary