"""Ingest dispatcher.

Validates each record against the per-type Pydantic model, dispatches the
valid ones to the persistence layer (UPSERT or INSERT OR IGNORE), and
returns the count of accepted vs. rejected records plus per-index errors.

The endpoint wraps this with the HTTP response (200/207/400) and the
ingest_log write.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError

from backend.schemas.etf import RECORD_VALIDATORS
from backend.services.etf_db import get_conn
from backend.services import etf_service


# data_type -> the per-record Pydantic model and the persistence call.
# Built dynamically from RECORD_VALIDATORS so adding a new data_type is a
# single change in the schema module.
_DISPATCH: Dict[str, str] = {
    "etf_quote": "upsert_quote",
    "etf_fundamentals": "upsert_fundamentals",
    "etf_holdings": "upsert_holdings",
    "etf_sector_weights": "upsert_sector_weights",
    "etf_performance": "upsert_performance",
    "etf_equity_holdings": "upsert_equity_holdings",
    "etf_esg": "upsert_esg",
    "etf_news": "insert_news",
}


def process_batch(
    data_type: str, records: List[Dict[str, Any]]
) -> Tuple[int, int, List[Dict[str, int]]]:
    """Validate each record, persist valid ones, return (accepted, rejected, errors).

    Per-index errors are returned in the same shape the spec requires:
    `[{"index": 2, "error": "field required: ts"}]`. The first error per
    record is reported (subsequent errors on the same record are dropped
    to keep the log compact).
    """
    model_cls = RECORD_VALIDATORS.get(data_type)
    if model_cls is None:
        raise ValueError(f"unsupported data_type '{data_type}'")

    method_name = _DISPATCH.get(data_type)
    if method_name is None:
        raise ValueError(f"no persistence method for data_type '{data_type}'")

    accepted = 0
    rejected = 0
    errors: List[Dict[str, int]] = []

    conn = get_conn()
    try:
        for idx, raw in enumerate(records):
            try:
                validated = model_cls.model_validate(raw)
            except ValidationError as exc:
                rejected += 1
                # First error message only — keeps the error log compact.
                first = exc.errors()[0]
                msg = first.get("msg", "validation error")
                field = ".".join(str(p) for p in first.get("loc", ())) or "record"
                errors.append({"index": idx, "error": f"{field}: {msg}"})
                continue

            try:
                getattr(etf_service, method_name)(conn, validated.model_dump())
            except Exception as exc:  # pragma: no cover - defensive
                rejected += 1
                errors.append({"index": idx, "error": f"persistence: {exc}"})
                continue

            accepted += 1

        conn.commit()
    finally:
        conn.close()

    return accepted, rejected, errors


def log_ingest(
    *,
    batch_id: str | None,
    data_type: str,
    source_ip: str,
    accepted: int,
    rejected: int,
) -> None:
    """Append a row to `etf_ingest_log`. Always called for non-401 requests."""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO etf_ingest_log"
            "(batch_id, data_type, source_ip, accepted, rejected, received_at) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (
                batch_id,
                data_type,
                source_ip,
                accepted,
                rejected,
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
        conn.commit()
    finally:
        conn.close()
