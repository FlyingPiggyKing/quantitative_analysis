## ADDED Requirements

### Requirement: Single ingest endpoint accepts all data types
The system SHALL expose `POST /api/etf/ingest` which accepts a JSON body of the shape:
```json
{
  "data_type": "etf_quote | etf_fundamentals | etf_holdings | etf_sector_weights | etf_performance | etf_equity_holdings | etf_esg | etf_news",
  "batch_id": "<ISO8601 UTC string with optional '-' suffix>",
  "records": [ ... per-type records, see schemas ... ]
}
```

#### Scenario: ETF quote ingest
- **WHEN** a request with `data_type=etf_quote` and `records=[{symbol, ts, price, pre_market_price, post_market_price, volume}]` is received
- **THEN** the endpoint UPSERTs each record into `etf_quote` keyed by `(symbol, ts)` and returns `{"accepted": N, "rejected": 0, "batch_id": "..."}`

#### Scenario: ETF fundamentals ingest
- **WHEN** a request with `data_type=etf_fundamentals` and `records=[{symbol, as_of, pe, pb, dividend_yield, dividend_rate}]` is received
- **THEN** the endpoint UPSERTs each record into `etf_fundamentals` keyed by `(symbol, as_of)` and returns the accepted count

#### Scenario: ETF holdings ingest
- **WHEN** a request with `data_type=etf_holdings` and `records=[{symbol, as_of_date, holdings: [{symbol, name, weight_pct}, ...]}]` is received
- **THEN** the endpoint UPSERTs each record into `etf_holdings` keyed by `(symbol, as_of_date)` (the `holdings` array is stored as JSON) and returns the accepted count

#### Scenario: ETF news ingest
- **WHEN** a request with `data_type=etf_news` and `records=[{url, symbol, title, publisher, published_at, summary}]` is received
- **THEN** the endpoint inserts each record into `etf_news` keyed by `url` (INSERT OR IGNORE — duplicate URLs are silently dropped) and returns the accepted count

#### Scenario: Unknown data_type
- **WHEN** a request with `data_type=etf_kline` (a type not in the supported set) is received
- **THEN** the endpoint returns HTTP 400 with `{"detail": "unsupported data_type 'etf_kline'"}`

### Requirement: Per-record validation with partial-success semantics
The endpoint MUST validate each record against its per-type Pydantic model. Records that fail validation are dropped (and counted in `rejected`); records that pass are inserted. The endpoint MUST return HTTP 207 if any record is rejected, HTTP 200 if all pass.

#### Scenario: One record invalid
- **WHEN** a batch of 5 records is sent and 1 record has a missing required field
- **THEN** the endpoint returns HTTP 207 with `{"accepted": 4, "rejected": 1, "batch_id": "...", "errors": [{"index": 2, "error": "field required: ts"}]}`

#### Scenario: All records invalid
- **WHEN** a batch of 5 records is sent and all 5 fail validation
- **THEN** the endpoint returns HTTP 400 with `{"accepted": 0, "rejected": 5, "batch_id": "...", "errors": [...]}`

### Requirement: Ingest log records every call (success, partial, error)
The endpoint MUST write one row to `etf_ingest_log` for every request that gets past the HMAC middleware. The row MUST include: `batch_id`, `data_type`, `source_ip`, `accepted`, `rejected`, `received_at` (UTC).

#### Scenario: Successful ingest
- **WHEN** a 200 OK response is sent back
- **THEN** a row is written to `etf_ingest_log` with the actual `accepted` and `rejected` counts

#### Scenario: Failed validation
- **WHEN** a 400 response is sent
- **THEN** a row is written to `etf_ingest_log` with `accepted=0` and `rejected=N`

#### Scenario: HMAC failure not logged
- **WHEN** the HMAC middleware returns 401
- **THEN** NO row is written to `etf_ingest_log` (avoid log pollution from brute-force probes)

### Requirement: Body size limit protects against large payloads
The endpoint MUST enforce a max body size of 1 MB. Requests larger than this return HTTP 413.

#### Scenario: Oversized body
- **WHEN** a request body exceeds 1 MB
- **THEN** the endpoint returns HTTP 413 and writes a row to `etf_ingest_log` with `rejected` counting the (unparseable) batch as 1
