---
name: verify-etf-pipeline
description: Verify the etf-fetcher-pusher change end-to-end. Use when the user wants to test, smoke-test, or verify the overseas ETF data pipeline (remote_data/).
license: MIT
metadata:
  scope: project
  applies-to: etf-fetcher-pusher change
---

# verify-etf-pipeline

Smoke-test and verify the overseas ETF data pipeline implemented in `remote_data/`.

Five progressive levels. Pick the deepest one that matches the question being asked — most users only need Level 1 or 2.

## Level 1 — Unit + integration tests (≤30s)

The fastest sanity check. 50 tests cover fetcher, store, pusher, scheduler, backfill, e2e.

```bash
cd /root/work/git_repos/quantitative_analysis
python3 -m pytest remote_data/ -v
```

Expect: `50 passed`. If anything fails, **stop** and read the failing test before continuing — don't proceed to live runs against a broken build.

## Level 2 — Schema init idempotency (≤5s)

Verifies the bootstrap entry point works and is safe to re-run.

```bash
# First run: creates the DB + 12 tables
python3 remote_data/scripts/init_local_db.py

# Second run: must be a no-op, exit 0
python3 remote_data/scripts/init_local_db.py && echo "EXIT=$?"   # → EXIT=0
```

Confirm files exist:
```bash
ls remote_data/data/   # → etf_local.db  etf_local.db-shm  etf_local.db-wal
```

The expected tables (printed by the script): `etf_dead_letter, etf_equity_holdings, etf_esg, etf_fundamentals, etf_holdings, etf_news, etf_performance, etf_quote, etf_sector_weights, fetch_log, push_log` (plus `sqlite_sequence`).

## Level 3 — E2E with mock ingest (≤5s, no network)

The `httpx.MockTransport`-backed e2e tests already cover the full store → push → ingest roundtrip. Run them in isolation for a focused signal:

```bash
python3 -m pytest remote_data/tests/test_e2e_pipeline.py -v
```

Expect 3 tests covering: (a) happy-path push with correct HMAC signature, (b) 4xx → dead-letter, (c) network error → records stay queued for retry.

This is the right level for "I changed the payload format / signing / retry policy" — these tests catch regressions without needing a real ingest endpoint.

## Level 4 — Live daemon smoke (1-2 min, hits yahooquery)

The closest to production. The daemon will fetch real data from yahooquery (first backfill) and start the scheduler. The first push will likely fail because no real ingest is configured — that's expected; we're verifying the **fetch + store + push-loop** paths.

### Option A: shell launcher (no systemd)
```bash
cp remote_data/.env.example remote_data/.env
# Edit remote_data/.env: fill REMOTE_INGEST_URL (any https string works for the smoke test)
#                     set ETF_PIPELINE_SECRET=0123456789abcdef0123456789abcdef
./start-fetcher.sh                  # backgrounds, writes logs/remote_data.pid
sleep 90                            # let it run
./stop-fetcher.sh                   # clean up
head -80 logs/remote_data.log       # captured output
```

### Option B: bare entry point
```bash
PYTHONPATH=. timeout 90 python3 -m remote_data 2>&1 | head -80
```

### What to look for in the log

| Log line | Means |
|---|---|
| `remote_data starting role=LOCAL symbols=20 ingest=...` | Config loaded |
| `local_db.init: schema applied at .../etf_local.db` | Schema OK |
| `health endpoint listening on http://127.0.0.1:8001/health` | Optional `/health` up |
| `scheduler starting` | APScheduler live |
| `fetch start data_type=etf_quote symbols=20` | A fetcher fired |
| `push start data_type=etf_quote rows=N` | Push loop drained |
| `push retry_later ... status=...` | Expected — no real ingest, so 5xx/network |

### Inspect what landed

```bash
# Per-table row counts
sqlite3 remote_data/data/etf_local.db "
  SELECT 'etf_quote' AS t, COUNT(*) FROM etf_quote
  UNION ALL SELECT 'etf_fundamentals', COUNT(*) FROM etf_fundamentals
  UNION ALL SELECT 'etf_news', COUNT(*) FROM etf_news;"

# Recent push attempts
sqlite3 remote_data/data/etf_local.db "SELECT * FROM push_log ORDER BY id DESC LIMIT 5;"

# Recent fetcher activity
sqlite3 remote_data/data/etf_local.db "SELECT * FROM fetch_log ORDER BY id DESC LIMIT 5;"

# Health snapshot
curl -s http://127.0.0.1:8001/health | python3 -m json.tool
```

## Level 5 — Full loop with local mock ingest (most realistic)

Wires up a tiny HTTP server that pretends to be the ingest endpoint, so the pusher sees `200 OK` and rows transition from `pushed_at IS NULL` → `pushed_at = <ts>`.

⚠️ **HTTPS-only caveat**: the pusher refuses `http://` URLs by spec. Two clean options:

### Option A: bypass HTTPS check (dev only, **revert before commit**)
```python
# In remote_data/pusher/client.py, comment out:
# if not url.lower().startswith("https://"):
#     raise HTTPSRequiredError(...)
```

### Option B: real HTTPS with self-signed cert
Out of scope for a quick smoke test; skip unless deploying.

### Mock ingest script (Option A)
```python
# /tmp/mock_ingest.py
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class H(BaseHTTPRequestHandler):
    def log_message(self, *a, **k): pass
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n)
        sig = self.headers.get("X-ETF-Pipeline-Signature", "")[:16]
        print(f"[mock] got {len(body)}B sig={sig}...")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"accepted":0,"rejected":0,"batch_id":"ok"}')

ThreadingHTTPServer(("127.0.0.1", 9999), H).serve_forever()
```

```bash
# Terminal 1
python3 /tmp/mock_ingest.py

# Terminal 2 — point pusher at the mock (after the HTTPS bypass above)
sed -i 's|^REMOTE_INGEST_URL=.*|REMOTE_INGEST_URL=http://127.0.0.1:9999/ingest|' remote_data/.env
./start-fetcher.sh                  # backgrounds, writes logs/remote_data.pid
sleep 60                            # let it run
./stop-fetcher.sh                   # clean up
tail -30 logs/remote_data.log       # captured output

# Verify rows got marked pushed
sqlite3 remote_data/data/etf_local.db "
  SELECT symbol, pushed_at IS NOT NULL AS pushed
  FROM etf_quote ORDER BY id DESC LIMIT 5;"
```

Expect: `pushed=1` for every row.

## When to use which level

| Question being asked | Level |
|---|---|
| "Did my code change break anything?" | 1 |
| "Is the bootstrap path correct?" | 2 |
| "Did I break the signing / push / retry contract?" | 3 |
| "Does the daemon actually start and fetch?" | 4 |
| "Does data actually reach a remote endpoint?" | 5 |

## Common pitfalls

- **`python: command not found`** — use `python3` (system Python 3.12). There is no `python` symlink in this dev env.
- **`No module named pytest`** — install with `python3 -m pip install --break-system-packages pytest python-dotenv httpx yahooquery apscheduler tzdata`.
- **`ZoneInfoNotFoundError: 'US/Eastern'`** — install `tzdata` (Debian split it out of stdlib).
- **`REMOTE_INGEST_URL must be HTTPS`** — this is by design (per `etf-pusher` spec §3). For local mocks, use Option A in Level 5.
- **`No module named remote_data.__main__`** — fixed by `remote_data/__main__.py`; if you see this, you ran an older revision.

## Out of scope

This skill tests the **overseas machine** (`etf-fetcher-pusher`). The **domestic ingest endpoint** (`etf-remote-data-persist`, parallel change) is verified separately on its own machine.