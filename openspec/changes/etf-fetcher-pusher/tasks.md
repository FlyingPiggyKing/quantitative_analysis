## 1. Project Skeleton & Config

- [x] 1.1 Create `remote_data/` directory with `__init__.py`
- [x] 1.2 Create `remote_data/pyproject.toml` with deps: `yahooquery`, `httpx`, `pydantic`, `apscheduler`, `python-dotenv`
- [x] 1.3 Create `remote_data/.env.example` with all keys from `etf-config` spec
- [x] 1.4 Add `remote_data/.env` and `remote_data/data/` to root `.gitignore`
- [x] 1.5 Implement `remote_data/config.py` (load + validate per `etf-config` spec)
- [x] 1.6 Create `remote_data/README.md` (run instructions, systemd example)

## 2. Local Store

- [x] 2.1 Create `remote_data/store/schema.sql` with all tables per `etf-local-store` spec §1
- [x] 2.2 Implement `remote_data/store/local_db.py` — `init()`, `connect()`, `migrate()`
- [x] 2.3 Implement `insert_<data_type>()` / `fetch_pending()` / `mark_pushed()` / `mark_failed()` per data type
- [x] 2.4 Implement `prune()` with retention thresholds (90/30/30 days)
- [x] 2.5 Implement `record_push_attempt()` writing to `push_log`
- [x] 2.6 Implement dead-letter write path for 4xx (writes `etf_dead_letter` + sets `failed_at`)
- [x] 2.7 Unit tests: insert / pending / mark pushed / prune

## 3. Fetcher Layer

- [x] 3.1 Implement `remote_data/fetcher/base.py` (Ticker factory, retry/backoff helper per `etf-fetcher` spec §3)
- [x] 3.2 Implement `remote_data/fetcher/etf_quote.py` (`fetch_quotes`)
- [x] 3.3 Implement `remote_data/fetcher/etf_fundamentals.py` (`fetch_fundamentals`)
- [x] 3.4 Implement `remote_data/fetcher/etf_holdings.py` (`fetch_holdings`)
- [x] 3.5 Implement `remote_data/fetcher/etf_sector_weightings.py`
- [x] 3.6 Implement `remote_data/fetcher/etf_performance.py`
- [x] 3.7 Implement `remote_data/fetcher/etf_equity_holdings.py`
- [x] 3.8 Implement `remote_data/fetcher/etf_esg.py`
- [x] 3.9 Implement `remote_data/fetcher/etf_news.py`
- [x] 3.10 Unit tests: each fetcher with a mocked yahooquery response verifying normalized shape
- [x] 3.11 Unit test: one-symbol-fails-does-not-raise

## 4. Pusher Layer

- [x] 4.1 Implement `remote_data/pusher/signing.py` (HMAC-SHA256, ISO8601 timestamp)
- [x] 4.2 Implement `remote_data/pusher/payload.py` (per-`data_type` JSON serialization, batch_id generation)
- [x] 4.3 Implement `remote_data/pusher/client.py` (httpx client, HTTPS-only, timeout, retry/backoff per `etf-pusher` spec §3)
- [x] 4.4 Implement `remote_data/pusher/loop.py` (groups pending rows by `data_type`, ships batches, marks pushed / dead-letters 4xx)
- [x] 4.5 Unit tests: signing (known vector), window check, retry on 5xx, no-retry on 4xx
- [x] 4.6 Integration test: pusher against a local mock ingest server (FastAPI test client or `http.server`)

## 5. Scheduler

- [x] 5.1 Implement `remote_data/scheduler/jobs.py` with all 9 fetch jobs + backfill + push loop per `etf-scheduler` spec
- [x] 5.2 Implement market-hours detection (US/Eastern aware; pre/post-market cadence)
- [x] 5.3 Wire each fetch job to (fetcher → store insert) sequence
- [x] 5.4 Wire the push loop to the pusher
- [x] 5.5 Wire backfill: run only when `etf_fundamentals` is empty
- [x] 5.6 Implement top-level `if __name__ == "__main__"` and `python -m remote_data` entry in `main.py` — MUST call `local_db.init()` BEFORE `scheduler.start()` so scheduler never queries missing tables
- [x] 5.7 Unit test: scheduler logs but does not crash on a raising job

## 6. Backfill

- [x] 6.1 Implement `remote_data/jobs/backfill_fundamentals.py` (current snapshot for all symbols + best-effort 2y history)
- [x] 6.2 Wire into scheduler's startup hook
- [x] 6.3 Test: empty DB → backfill populates; non-empty DB → skipped

## 7. Observability & Ops

- [x] 7.1 Configure rotating file logger to `LOG_FILE` (default `data/etf_local.log`)
- [x] 7.2 Add structured log lines at fetch start/end, push start/end, dead-letter, retry exhaustion
- [x] 7.3 (Optional) `/health` HTTP endpoint on `127.0.0.1:8001` — liveness + last successful push timestamp
- [x] 7.4 Provide `systemd/remote-data.service` example in README

## 8. Bootstrap Scripts

The change ships three bootstrap entry points. They share the same `local_db.init()` call so all paths converge on one schema definition.

- [x] 8.1 Refine `remote_data/main.py` startup hook (task 5.6): call `local_db.init()` BEFORE `scheduler.start()`, so the scheduler never sees a missing-table error
- [x] 8.2 Add `remote_data/scripts/init_local_db.py` — standalone Python script; loads `.env` from `remote_data/`, calls `local_db.init()`, prints table list on stdout; exit 0 on success, non-zero on failure
- [x] 8.3 Make `init_local_db.py` create the parent directory of `LOCAL_DB_PATH` (default `data/etf_local.db`) if it doesn't exist (mirrors what `main.py` startup does)
- [x] 8.4 Make `init_local_db.py` load `.env` so `LOCAL_DB_PATH` override works without manually exporting
- [x] 8.5 Add `scripts/start-etf-fetcher.sh` — shell launcher following `start-backend.sh` pattern; ensures `data/` exists, runs `init_local_db.py` first, then `python -m remote_data`
- [x] 8.6 `start-etf-fetcher.sh` MUST work without `systemd` (so users who don't want systemd still get the same bootstrap contract)
- [x] 8.7 Document the relationship in `remote_data/README.md`: prefer systemd for production, but `start-etf-fetcher.sh` is the supported way to run the daemon ad-hoc / in foreground
- [x] 8.8 Smoke test: fresh clone → run `scripts/start-etf-fetcher.sh` → `sqlite3 data/etf_local.db ".tables"` shows all 8 business tables + `push_log` + `etf_dead_letter`
- [x] 8.9 Smoke test: run `remote_data/scripts/init_local_db.py` twice in a row → second run is a no-op, exit 0
- [x] 8.10 Smoke test: remove `data/etf_local.db` → run `python -m remote_data` directly (no shell wrapper) → all tables present (main.py startup hook covers the bare invocation path)

## 9. Smoke Test

- [x] 9.1 End-to-end manual run: `python -m remote_data` with a `REMOTE_INGEST_URL` pointing at a local mock ingest
- [x] 9.2 Verify: at least one `etf_quote` row in `etf_local.db`, marked `pushed_at`
- [x] 9.3 Verify: at least one `etf_fundamentals` row written by backfill
- [x] 9.4 Verify: kill network → records queue → restore network → records ship → `pushed_at` updated

## 10. Integration with Parallel Change

- [x] 10.1 Confirm payload schema and header names match the `etf-remote-data-persist` change's Pydantic models and middleware
- [x] 10.2 Confirm HMAC algorithm and timestamp window match (both sides: signing here, verifying there)
- [x] 10.3 Cross-team test: real overseas machine against real Chinese ingest endpoint
