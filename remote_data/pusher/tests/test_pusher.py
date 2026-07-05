"""Unit + integration tests for the pusher."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

import httpx
import pytest

from remote_data.pusher import client, payload, signing
from remote_data.pusher.loop import run_once


# ---------------------------------------------------------------------------
# Signing — known vector
# ---------------------------------------------------------------------------


def test_signing_known_vector():
    secret = "test-secret"
    ts = "2026-06-29T03:14:00Z"
    body = b'{"data_type":"etf_quote","records":[]}'
    expected = hmac.new(
        secret.encode(), (ts + "\n").encode() + body, hashlib.sha256
    ).hexdigest()
    assert signing.sign(secret, ts, body) == expected


def test_within_window_accepts_close_timestamp():
    now = datetime(2026, 6, 29, 3, 14, 30, tzinfo=timezone.utc)
    assert signing.within_window("2026-06-29T03:14:00Z", now=now, window_seconds=300)


def test_within_window_rejects_old_timestamp():
    now = datetime(2026, 6, 29, 3, 30, 0, tzinfo=timezone.utc)
    assert not signing.within_window("2026-06-29T03:14:00Z", now=now, window_seconds=300)


def test_build_headers_returns_expected_keys():
    ts, sig, headers = signing.build_headers("s", b"body")
    assert headers["X-ETF-Pipeline-Timestamp"] == ts
    assert headers["X-ETF-Pipeline-Signature"] == sig
    assert headers["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# Payload shape
# ---------------------------------------------------------------------------


def test_payload_drops_internal_cursors():
    records = [
        {"id": 1, "symbol": "QQQ", "price": 1.0, "pushed_at": "x", "failed_at": None},
    ]
    body = payload.build_body("etf_quote", records)
    parsed = json.loads(body)
    assert "id" not in parsed["records"][0]
    assert "pushed_at" not in parsed["records"][0]
    assert "failed_at" not in parsed["records"][0]
    assert parsed["records"][0]["symbol"] == "QQQ"


def test_payload_batch_id_format():
    body = payload.build_body("etf_quote", [])
    parsed = json.loads(body)
    assert parsed["batch_id"].endswith("-etf_quote")
    expected_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    assert parsed["batch_id"].startswith(expected_prefix)


# ---------------------------------------------------------------------------
# Client: HTTPS-only, retry, classify
# ---------------------------------------------------------------------------


def _cfg(tmp_path, url="https://example.com/ingest", timeout=5):
    from remote_data.config import Config
    return Config(
        deploy_role="LOCAL",
        remote_ingest_url=url,
        etf_pipeline_secret="x" * 32,
        local_db_path=str(tmp_path / "db.sqlite"),
        time_window_seconds=300,
        http_timeout_seconds=timeout,
        yahooquery_max_retries=1,
        yahooquery_backoff_seconds=0,
        symbols=["QQQ"],
        fetch_quotes_interval_minutes=5,
        fetch_quotes_offhours_interval_minutes=30,
        push_interval_seconds=30,
        batch_size=500,
        market_tz="US/Eastern",
        log_level="INFO",
        log_file=str(tmp_path / "log.txt"),
    )


def test_client_rejects_http_url(tmp_path):
    cfg = _cfg(tmp_path, url="http://insecure.example.com/ingest")
    with pytest.raises(client.HTTPSRequiredError):
        client.post_batch(cfg, b"{}", max_attempts=1)


def test_classify_success():
    r = client.PushResult(ok=True, status_code=200, body="", retries=0)
    assert client.classify(r) == "success"


def test_classify_4xx_is_dead_letter():
    r = client.PushResult(ok=False, status_code=400, body="bad", retries=0)
    assert client.classify(r) == "dead_letter"


def test_classify_5xx_is_retry_later():
    r = client.PushResult(ok=False, status_code=503, body="", retries=1)
    assert client.classify(r) == "retry_later"


def test_classify_network_error_is_retry_later():
    r = client.PushResult(ok=False, status_code=None, body=None, retries=0, error="TimeoutError")
    assert client.classify(r) == "retry_later"


def test_backoff_schedule():
    s = client._backoff_schedule(5)
    assert s == [0.0, 1.0, 4.0, 16.0, 64.0]


# ---------------------------------------------------------------------------
# Loop integration against a fake transport
# ---------------------------------------------------------------------------


class _TransportRecorder:
    def __init__(self, responses):
        # responses is a list of (status, body) consumed per call
        self._responses = list(responses)
        self.calls = []  # list of (url, body_bytes, headers)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = request.content
        headers = dict(request.headers)
        self.calls.append((str(request.url), body, headers))
        if not self._responses:
            status, resp_body = 200, b""
        else:
            status, resp_body = self._responses.pop(0)
        return httpx.Response(status_code=status, content=resp_body)


def _sign_match(secret: str, ts: str, body: bytes) -> str:
    return hmac.new(
        secret.encode(), (ts + "\n").encode() + body, hashlib.sha256
    ).hexdigest()


def test_loop_marks_pushed_on_2xx(tmp_path):
    from remote_data.store import local_db
    db_path = tmp_path / "db.sqlite"
    local_db.init(db_path)
    conn = local_db.connect(db_path)
    local_db.insert_etf_quote(conn, [
        {"symbol": "QQQ", "ts": "2026-06-29T13:30:00Z", "price": 1.0},
    ])
    cfg = _cfg(tmp_path)

    transport = _TransportRecorder([(200, b'{"ok":true}')])

    # Patch httpx.Client used inside post_batch with a factory that yields a
    # fresh mock client per call. Reference httpx via the module-level symbol
    # to avoid recursion (we patch client.httpx.Client, not the httpx module).
    real_httpx_Client = client.httpx.Client

    def _make_mock_client(*a, **kw):
        return real_httpx_Client(transport=httpx.MockTransport(transport))

    client.httpx.Client = _make_mock_client
    try:
        summary = run_once(conn, cfg)
    finally:
        client.httpx.Client = real_httpx_Client

    assert summary["pushed"] == 1
    assert summary["dead_lettered"] == 0
    # Source row marked pushed.
    row = conn.execute(
        "SELECT pushed_at FROM etf_quote WHERE symbol='QQQ'"
    ).fetchone()
    assert row["pushed_at"] is not None
    # Header signature is correct.
    url, body, headers = transport.calls[0]
    expected_sig = _sign_match(cfg.etf_pipeline_secret, headers["x-etf-pipeline-timestamp"], body)
    assert headers["x-etf-pipeline-signature"] == expected_sig
    # push_log row written.
    plog = conn.execute("SELECT * FROM push_log").fetchall()
    assert len(plog) == 1
    assert plog[0]["http_status"] == 200
    conn.close()


def test_loop_dead_letters_on_4xx(tmp_path):
    from remote_data.store import local_db
    db_path = tmp_path / "db.sqlite"
    local_db.init(db_path)
    conn = local_db.connect(db_path)
    local_db.insert_etf_quote(conn, [
        {"symbol": "QQQ", "ts": "2026-06-29T13:30:00Z", "price": 1.0},
    ])
    cfg = _cfg(tmp_path)

    transport = _TransportRecorder([(400, b"bad schema")])

    real_httpx_Client = client.httpx.Client

    def _make_mock_client(*a, **kw):
        return real_httpx_Client(transport=httpx.MockTransport(transport))

    client.httpx.Client = _make_mock_client
    try:
        summary = run_once(conn, cfg)
    finally:
        client.httpx.Client = real_httpx_Client

    assert summary["dead_lettered"] == 1
    assert summary["pushed"] == 0
    # Dead-letter row written + source row marked failed_at.
    dl = conn.execute("SELECT * FROM etf_dead_letter").fetchall()
    assert len(dl) == 1
    assert dl[0]["response_status"] == 400
    row = conn.execute("SELECT failed_at FROM etf_quote WHERE symbol='QQQ'").fetchone()
    assert row["failed_at"] is not None
    conn.close()


def test_loop_retries_5xx_then_returns(tmp_path):
    from remote_data.store import local_db
    db_path = tmp_path / "db.sqlite"
    local_db.init(db_path)
    conn = local_db.connect(db_path)
    local_db.insert_etf_quote(conn, [
        {"symbol": "QQQ", "ts": "2026-06-29T13:30:00Z", "price": 1.0},
    ])
    cfg = _cfg(tmp_path)

    # Provide 5 consecutive 503s — the default max_attempts is 5.
    transport = _TransportRecorder([(503, b"server error")] * 5)

    real_httpx_Client = client.httpx.Client

    def _make_mock_client(*a, **kw):
        return real_httpx_Client(transport=httpx.MockTransport(transport))

    client.httpx.Client = _make_mock_client
    # Patch time.sleep so retries don't actually wait.
    import time as _time
    real_sleep = _time.sleep
    _time.sleep = lambda *_a, **_k: None
    try:
        try:
            summary = run_once(conn, cfg)
        finally:
            _time.sleep = real_sleep
    finally:
        client.httpx.Client = real_httpx_Client

    # 503 is retryable — every attempt exhausted, retry_later verdict.
    assert summary["retried"] == 1
    row = conn.execute("SELECT pushed_at FROM etf_quote WHERE symbol='QQQ'").fetchone()
    assert row["pushed_at"] is None
    conn.close()