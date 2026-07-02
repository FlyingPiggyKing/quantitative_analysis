"""POST /api/etf/ingest — receive HMAC-signed batches from the overseas pusher.

Middleware (registered in main.py) already enforces HMAC and per-IP rate
limit. This module only owns:
- Body-size cap (413)
- Pydantic top-level validation (400 for unknown data_type / missing batch_id)
- Dispatch to the per-type persistence flow (200/207)
- etf_ingest_log write (except for 401, which the HMAC middleware returns
  silently).
"""
from __future__ import annotations

from typing import Annotated, Union

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import Field, TypeAdapter, ValidationError

from backend.middleware.rate_limit import get_source_ip
from backend.schemas.etf import IngestRequest
from backend.services.etf_config import get_etf_config
from backend.services.etf_ingest_service import log_ingest, process_batch

router = APIRouter(tags=["etf-ingest"])

# Module-level adapter so we can `validate_python` the parsed JSON body
# without rebuilding the discriminated union on every request.
_INGEST_ADAPTER = TypeAdapter(IngestRequest)


@router.post("/api/etf/ingest")
async def ingest(
    request: Request,
) -> dict:
    cfg = get_etf_config()
    source_ip = get_source_ip(request)

    # Body-size cap. Read raw bytes first; the body is cached for downstream.
    body_bytes = await request.body()
    if len(body_bytes) > cfg.ingest_max_body_bytes:
        # Log the rejection — useful diagnostic, schema-failure is 4xx.
        log_ingest(
            batch_id=None,
            data_type="oversized",
            source_ip=source_ip,
            accepted=0,
            rejected=1,
        )
        raise HTTPException(status_code=413, detail="payload too large")

    # Parse JSON + top-level Pydantic validation.
    try:
        import json
        try:
            raw = json.loads(body_bytes)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"invalid JSON: {exc.msg}")
        parsed = _INGEST_ADAPTER.validate_python(raw)
    except ValidationError as exc:
        # Top-level schema failure (unknown data_type, missing batch_id, ...).
        log_ingest(
            batch_id=(raw or {}).get("batch_id") if isinstance(raw, dict) else None,
            data_type=(raw or {}).get("data_type") if isinstance(raw, dict) else None,
            source_ip=source_ip,
            accepted=0,
            rejected=1,
        )
        raise HTTPException(status_code=400, detail=f"schema error: {exc.errors()[0]['msg']}")

    # Dispatch. process_batch raises ValueError for unknown data_type
    # (shouldn't reach here because the union validates data_type, but
    # be defensive in case the discriminated union's Literal slips through).
    try:
        accepted, rejected, errors = process_batch(parsed.data_type, parsed.records)
    except ValueError as exc:
        log_ingest(
            batch_id=parsed.batch_id,
            data_type=parsed.data_type,
            source_ip=source_ip,
            accepted=0,
            rejected=1,
        )
        raise HTTPException(status_code=400, detail=str(exc))

    # Audit log for every accepted request that got past HMAC.
    log_ingest(
        batch_id=parsed.batch_id,
        data_type=parsed.data_type,
        source_ip=source_ip,
        accepted=accepted,
        rejected=rejected,
    )

    body: dict = {
        "accepted": accepted,
        "rejected": rejected,
        "batch_id": parsed.batch_id,
    }
    if errors:
        body["errors"] = errors

    # Status code: 200 if all valid, 207 if some rejected, 400 if ALL rejected.
    # Per etf-ingest-endpoint spec: "All records invalid" → HTTP 400 with the
    # same body shape (accepted/rejected/errors), NOT a FastAPI detail wrapper.
    if accepted == 0 and rejected > 0:
        status_code = 400
    elif rejected > 0:
        status_code = 207
    else:
        status_code = 200

    from fastapi.responses import JSONResponse
    return JSONResponse(body, status_code=status_code)
