## ADDED Requirements

### Requirement: Pusher authenticates every request with HMAC-SHA256 and timestamp window
The pusher MUST sign every HTTP request to the remote ingest endpoint with HMAC-SHA256 over `timestamp + "\n" + body`, and the remote endpoint MUST reject any request whose `X-ETF-Pipeline-Timestamp` is more than `TIME_WINDOW_SECONDS` (default 300) away from its current UTC time.

#### Scenario: Signing a request
- **WHEN** the pusher sends a request with body `{"data_type":"etf_quote","records":[...]}` and timestamp `2026-06-29T03:14:00Z`
- **THEN** the request MUST include the headers `X-ETF-Pipeline-Timestamp: 2026-06-29T03:14:00Z` and `X-ETF-Pipeline-Signature: <hex>` where `<hex>` is `hmac_sha256(secret, "2026-06-29T03:14:00Z\n" + body_bytes)`

#### Scenario: Window rejects old timestamp
- **WHEN** the remote receives a request whose `X-ETF-Pipeline-Timestamp` is 10 minutes in the past relative to its own clock
- **THEN** the remote returns HTTP 401 and the pusher does NOT mark the source rows as pushed

#### Scenario: Constant-time comparison
- **WHEN** the remote verifies the signature
- **THEN** it MUST use `hmac.compare_digest` (constant-time) and not `==`

### Requirement: Pusher batches by data type and ships one request per data type per push loop
The pusher MUST group pending rows by `data_type` and emit one HTTP POST per data type per push cycle, carrying up to 500 records per request.

#### Scenario: Single data type per request
- **WHEN** the push loop runs and there are 30 pending `etf_quote` rows and 50 pending `etf_fundamentals` rows
- **THEN** the pusher issues exactly two POSTs: one for `etf_quote` (30 records) and one for `etf_fundamentals` (50 records)

#### Scenario: Batch size cap
- **WHEN** there are 1500 pending `etf_quote` rows
- **THEN** the pusher issues 3 sequential POSTs of 500 records each (or, if concurrency is enabled, up to 3 in parallel)

### Requirement: Pusher retries on transient failures with exponential backoff
The pusher MUST retry on HTTP 5xx, 408, 429, and on network errors. Retry intervals MUST be 1s, 4s, 16s, 64s, capped at 5 attempts per batch. The pusher MUST NOT retry on 4xx (other than 408/429).

#### Scenario: 503 from remote
- **WHEN** the ingest returns HTTP 503
- **THEN** the pusher waits the configured backoff and retries the same batch; `retry_count` is incremented in `push_log`

#### Scenario: 400 from remote
- **WHEN** the ingest returns HTTP 400 (schema rejection)
- **THEN** the pusher writes the records to `etf_dead_letter`, marks `failed_at` on the source rows, and does NOT retry

#### Scenario: Persistent 5xx
- **WHEN** the ingest returns 5xx for 5 consecutive attempts of the same batch
- **THEN** the pusher stops retrying for this push cycle; the records remain `pushed_at IS NULL` and will be picked up on the next push cycle

### Requirement: Pusher uses HTTPS and respects HTTP timeout
The pusher MUST use HTTPS (HTTP rejected) and MUST enforce a per-request timeout of `HTTP_TIMEOUT_SECONDS` (default 15).

#### Scenario: HTTPS required
- **WHEN** `REMOTE_INGEST_URL` starts with `http://`
- **THEN** the pusher refuses to start and logs a fatal error

#### Scenario: Timeout
- **WHEN** the remote does not respond within `HTTP_TIMEOUT_SECONDS`
- **THEN** the pusher treats it as a transient error and retries per the backoff schedule

### Requirement: Payload schema is self-describing and matches the contract in `etf-remote-data-persist`
The pusher MUST serialize each batch as JSON with the shape:
```json
{
  "data_type": "<name>",
  "batch_id": "<ISO8601 UTC + '-' + data_type>",
  "records": [ ... ]
}
```
Field types per `data_type` MUST exactly match the remote's Pydantic models (defined in the parallel `etf-remote-data-persist` change).

#### Scenario: ETF quote batch body
- **WHEN** the pusher ships a batch of `etf_quote` records
- **THEN** the body matches `{ "data_type": "etf_quote", "batch_id": "<iso>-etf_quote", "records": [{ "symbol": ..., "ts": ..., "price": ..., "pre_market_price": ..., "post_market_price": ..., "volume": ... }] }`

#### Scenario: ETF news batch body
- **WHEN** the pusher ships a batch of `etf_news` records
- **THEN** the body matches `{ "data_type": "etf_news", "batch_id": "<iso>-etf_news", "records": [{ "url": ..., "symbol": ..., "title": ..., "publisher": ..., "published_at": ..., "summary": ... }] }`
