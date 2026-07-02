# etf-ingest-auth Specification

## Purpose
TBD - created by archiving change etf-remote-data-persist. Update Purpose after archive.
## Requirements
### Requirement: HMAC-SHA256 + timestamp window middleware protects `/api/etf/ingest`
The system SHALL provide a FastAPI middleware (or dependency) that, for every request to `/api/etf/ingest`:
1. Reads `X-ETF-Pipeline-Timestamp` and `X-ETF-Pipeline-Signature` from the request headers
2. Computes the expected signature as `HMAC-SHA256(secret, timestamp_utf8 + b"\n" + body_utf8)` where `secret` is read from `ETF_PIPELINE_SECRET`
3. Uses `hmac.compare_digest` to compare expected vs provided signature
4. Parses the timestamp as ISO8601 UTC and rejects if `|now_utc - timestamp| > TIME_WINDOW_SECONDS` (default 300)
5. Returns HTTP 401 with body `{"detail": "unauthorized"}` on any failure (without writing to the ingest log)

#### Scenario: Valid signature
- **WHEN** a request arrives with `X-ETF-Pipeline-Timestamp` = `2026-06-29T03:14:00Z` and `X-ETF-Pipeline-Signature` = the correct HMAC of `2026-06-29T03:14:00Z\n<body>` and the timestamp is within ±5 minutes of server time
- **THEN** the middleware passes the request through to the endpoint

#### Scenario: Missing signature header
- **WHEN** a request arrives without `X-ETF-Pipeline-Signature`
- **THEN** the middleware returns HTTP 401 and the request body is NOT processed

#### Scenario: Tampered body
- **WHEN** a request arrives with a valid signature but the body has been modified in transit
- **THEN** the middleware's `hmac.compare_digest` returns False and the middleware returns HTTP 401

#### Scenario: Stale timestamp
- **WHEN** a request arrives with `X-ETF-Pipeline-Timestamp` more than 5 minutes in the past
- **THEN** the middleware returns HTTP 401 (anti-replay)

#### Scenario: Future timestamp
- **WHEN** a request arrives with `X-ETF-Pipeline-Timestamp` more than 5 minutes in the future
- **THEN** the middleware returns HTTP 401 (prevents pre-computed signature abuse)

#### Scenario: Constant-time comparison
- **WHEN** the middleware compares signatures
- **THEN** it MUST use `hmac.compare_digest` (constant-time) and never `==` to prevent timing attacks

### Requirement: HMAC middleware only protects the ingest path
The HMAC middleware MUST be scoped to `/api/etf/ingest` (and any future ingest sub-paths). It MUST NOT be applied to read endpoints (`/api/etf/quote/...`, `/api/etf/fundamentals/...`, etc.), `/docs`, `/health`, or any other path.

#### Scenario: Read endpoint is not HMAC-protected
- **WHEN** a GET request arrives at `/api/etf/fundamentals/QQQ` without any HMAC headers
- **THEN** the request is processed normally; the middleware does NOT reject it

#### Scenario: Docs endpoint is not HMAC-protected
- **WHEN** a GET request arrives at `/docs`
- **THEN** the request is served as normal Swagger UI

### Requirement: HMAC secret is loaded from environment only
The middleware MUST read `ETF_PIPELINE_SECRET` from the process environment. It MUST fail-fast at startup if the variable is unset or empty.

#### Scenario: Secret missing
- **WHEN** the backend process starts and `ETF_PIPELINE_SECRET` is not set
- **THEN** startup aborts with a clear error message naming the missing variable

