"""Push payload construction.

Per `etf-pusher` spec:
    {
      "data_type": "<name>",
      "batch_id": "<ISO8601 UTC>-<data_type>",
      "records": [ ... ]
    }
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable, List, Mapping


def make_batch_id(data_type: str, now: datetime | None = None) -> str:
    """`<iso>-<data_type>` where iso is `YYYY-MM-DDTHH:MM:SSZ`."""
    iso = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{iso}-{data_type}"


def serialize_records(records: Iterable[Mapping[str, Any]]) -> List[dict]:
    """Return JSON-safe records, dropping any `pushed_at` / `failed_at` cursors
    that the store layer uses internally — those should never reach the wire."""
    out: List[dict] = []
    for r in records:
        cleaned = {}
        for k, v in r.items():
            if k in ("pushed_at", "failed_at", "id"):
                continue
            cleaned[k] = v
        out.append(cleaned)
    return out


def build_body(data_type: str, records: Iterable[Mapping[str, Any]], *, batch_id: str | None = None) -> bytes:
    """Build the JSON body bytes for a push request."""
    body = {
        "data_type": data_type,
        "batch_id": batch_id or make_batch_id(data_type),
        "records": serialize_records(records),
    }
    return json.dumps(body, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")