## 1. Schema & Database

- [x] 1.1 Create `backend/migrations/etf_schema.sql` with all 9 tables per `etf-persistence` spec
- [x] 1.2 Add startup hook in `backend/main.py` to run the schema (idempotent)
- [x] 1.3 Implement `backend/services/etf_db.py` — connection helper, `init()`, `get_conn()`
- [x] 1.4 Add `data/etf_remote.db` to `backend/.gitignore`

## 2. Pydantic Schemas

- [x] 2.1 Create `backend/schemas/etf.py` with per-`data_type` request/response models
- [x] 2.2 Add discriminated union (`Annotated[Union[EtfQuoteBatch, ...], Field(discriminator="data_type")]`) for the ingest request
- [x] 2.3 Cross-check field names and types against `etf-fetcher-pusher/specs/etf-pusher/spec.md` payload schema
- [x] 2.4 Unit test: each schema rejects missing required fields and wrong types

## 3. HMAC Auth Middleware

- [x] 3.1 Implement `backend/middleware/hmac_auth.py` per `etf-ingest-auth` spec
- [x] 3.2 Read `ETF_PIPELINE_SECRET` and `TIME_WINDOW_SECONDS` from config
- [x] 3.3 Use `hmac.compare_digest` for constant-time comparison
- [x] 3.4 Scope middleware to `/api/etf/ingest` path only (do NOT wrap read endpoints)
- [x] 3.5 Return 401 with `{"detail": "unauthorized"}` on any failure; do NOT write to ingest log
- [x] 3.6 Unit tests: valid sig, missing sig, tampered body, stale timestamp, future timestamp

## 4. Rate Limit Middleware

- [x] 4.1 Implement `backend/middleware/rate_limit.py` per `etf-rate-limit` spec
- [x] 4.2 Sliding window counter (per 24h) keyed by `X-Forwarded-For` first segment or socket `remote_addr`
- [x] 4.3 Persist state to `rate_limit_state` table every `RATE_LIMIT_FLUSH_SECONDS` (default 60s)
- [x] 4.4 Load state from `rate_limit_state` on startup
- [x] 4.5 Scope to `/api/etf/ingest` only (read endpoints not limited)
- [x] 4.6 On 429, log a row to `etf_ingest_log` with `data_type='rate_limited'`
- [x] 4.7 Unit tests: under limit, at limit, restart preserves state, X-Forwarded-For parsing

## 5. Ingest Endpoint

- [x] 5.1 Implement `backend/api/etf_ingest.py` — POST `/api/etf/ingest`
- [x] 5.2 Apply HMAC middleware → rate-limit middleware → Pydantic validation → dispatch
- [x] 5.3 Implement `backend/services/etf_ingest_service.py` — dispatcher (`data_type` → per-type UPSERT)
- [x] 5.4 Per-record validation with partial success (HTTP 207)
- [x] 5.5 Enforce `INGEST_MAX_BODY_BYTES` (1 MB default), return 413 on overflow
- [x] 5.6 On any error, write a row to `etf_ingest_log` (except HMAC 401, which is silent)
- [x] 5.7 Unit tests: each data_type happy path, partial success, schema failure, oversized body, unknown data_type

## 6. Persistence Service

- [x] 6.1 Implement `backend/services/etf_service.py` with typed read methods per `etf-persistence` spec
- [x] 6.2 UPSERT using `INSERT ... ON CONFLICT(...) DO UPDATE` for all tables except `etf_news`
- [x] 6.3 `etf_news` uses `INSERT OR IGNORE` on `url` PK
- [x] 6.4 Store `holdings` / `sectors` / `equity_holdings` / `esg` arrays as JSON in `payload_json`
- [x] 6.5 Implement `list_symbols()` (DISTINCT across tables, alphabetical)
- [x] 6.6 Unit tests: UPSERT dedupe, INSERT OR IGNORE on news, JSON round-trip

## 7. Read API

- [x] 7.1 Implement `backend/api/etf_read.py` with all 9 GET endpoints per `etf-read-api` spec
- [x] 7.2 `GET /api/etf/symbols` — distinct sorted symbol list
- [x] 7.3 `GET /api/etf/quote/{symbol}?limit=N` — newest first
- [x] 7.4 `GET /api/etf/fundamentals/{symbol}` — single latest
- [x] 7.5 `GET /api/etf/holdings/{symbol}`, `/sector-weights/{symbol}`, `/equity-holdings/{symbol}`, `/performance/{symbol}`, `/esg/{symbol}` — single latest
- [x] 7.6 `GET /api/etf/news/{symbol}?page=N&page_size=M` — paginated, newest first
- [x] 7.7 Return HTTP 404 with `{"detail": "no <type> for <symbol>"}` for missing data
- [x] 7.8 Register router in `backend/main.py`
- [x] 7.9 Unit tests: each endpoint happy path, 404 on missing, pagination

## 8. Health Integration

- [x] 8.1 Extend existing `/health` endpoint (or add `/api/etf/health`) to include ETF status
- [x] 8.2 Add `etf_last_ingest_at`, `etf_last_batch_id`, `etf_symbols_covered` fields
- [x] 8.3 If `/health` is shared, query the latest `etf_ingest_log` row + `COUNT(DISTINCT symbol)` across data tables

## 9. Config

- [x] 9.1 Update `backend/.env.example` with all new keys per `etf-config` spec
- [x] 9.2 Implement config validation at startup (fail-fast on missing `ETF_PIPELINE_SECRET`)
- [x] 9.3 Verify secret value is never logged (startup messages use presence-only format)

## 10. Cross-Change Integration Test

- [x] 10.1 Start backend with a known `ETF_PIPELINE_SECRET`
- [x] 10.2 Start a local `etf-fetcher-pusher` instance pointed at this backend
- [x] 10.3 Wait one quote-tick cycle (5 min) and verify at least one `etf_quote` row + ingest log entry
- [x] 10.4 Verify read API: `GET /api/etf/quote/QQQ` returns the pushed data
- [x] 10.5 Verify HMAC failure: send a tampered body → 401, no ingest log entry
- [x] 10.6 Verify rate limit: set `INGEST_MAX_REQUESTS_PER_DAY=2`, push 3 → first 2 succeed, third 429
- [x] 10.7 Verify restart persistence: push enough to consume 40000/50000, restart backend, push 10001 more → 429
- [x] 10.8 Verify UPSERT dedupe: push same `(symbol, ts)` twice → exactly one row in DB
- [x] 10.9 Verify news dedupe: push same `url` twice → exactly one row in DB
- [x] 10.10 Verify partial success: send a 5-record batch with 1 invalid → HTTP 207, 4 accepted, 1 rejected
