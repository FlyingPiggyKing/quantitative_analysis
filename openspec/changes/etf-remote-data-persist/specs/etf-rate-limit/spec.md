## ADDED Requirements

### Requirement: IP-based sliding-window rate limit on the ingest endpoint
The system SHALL enforce a per-source-IP rate limit on `POST /api/etf/ingest` (and any other paths under `/api/etf/ingest/*`). The default limit is `INGEST_MAX_REQUESTS_PER_DAY` requests per 24-hour sliding window (default 50000). When exceeded, the endpoint returns HTTP 429 with `{"detail": "rate limit exceeded"}`.

#### Scenario: Within limit
- **WHEN** a source IP has made fewer than `INGEST_MAX_REQUESTS_PER_DAY` requests in the past 24 hours
- **THEN** the request is processed normally

#### Scenario: Limit exceeded
- **WHEN** a source IP has made `INGEST_MAX_REQUESTS_PER_DAY` requests in the past 24 hours
- **THEN** the next request returns HTTP 429 and the response is NOT processed by the ingest endpoint

#### Scenario: Configurable limit
- **WHEN** `INGEST_MAX_REQUESTS_PER_DAY=1000` is set in `.env`
- **THEN** the system enforces 1000 requests per 24h per IP

### Requirement: Source IP is parsed from `X-Forwarded-For` first, falling back to socket address
The rate limiter MUST extract the client IP using this priority:
1. The first IP in `X-Forwarded-For` (the leftmost, the original client) if the header is present
2. The socket `remote_addr` otherwise

#### Scenario: Behind nginx
- **WHEN** the request comes through nginx which sets `X-Forwarded-For: <client_ip>, <nginx_ip>` and the FastAPI socket sees `127.0.0.1`
- **THEN** the rate limiter uses `<client_ip>` as the key

#### Scenario: Direct connection
- **WHEN** the request comes from a direct connection with no `X-Forwarded-For`
- **THEN** the rate limiter uses the socket `remote_addr`

### Requirement: Rate-limit state survives backend restarts
The system MUST persist the rate-limit state to a SQLite table (`rate_limit_state`) at most every 60 seconds. On startup, the system MUST load the state from the table. This prevents an attacker from triggering a restart to reset the counter.

#### Scenario: State flushed
- **WHEN** the backend has been running and has accepted ingest requests
- **THEN** the `rate_limit_state` table contains rows of `(ip, window_start, count)` no older than 60 seconds

#### Scenario: Restart preserves limit
- **WHEN** the backend is restarted and an IP is at 45000/50000
- **THEN** after restart, that IP has 5000 remaining requests in the current 24h window

### Requirement: Rate limiter does not apply to read endpoints
The rate limiter MUST be scoped to the ingest path. Read endpoints (`/api/etf/quote/...`, etc.) are not rate-limited (they are CORS-protected and intended for frontend use).

#### Scenario: Read endpoint not rate-limited
- **WHEN** 10000 GET requests to read endpoints are made from a single IP within 24 hours
- **THEN** none of them return HTTP 429

### Requirement: 429 responses are logged
When the rate limiter rejects a request, the system MUST write a row to `etf_ingest_log` with `accepted=0, rejected=0, data_type='rate_limited'` so the operator can detect misbehavior or attacks.

#### Scenario: 429 logged
- **WHEN** a request is rejected with HTTP 429
- **THEN** `etf_ingest_log` contains a row identifying the source IP and `data_type='rate_limited'`
