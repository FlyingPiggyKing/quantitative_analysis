# etf-read-api Specification

## Purpose
TBD - created by archiving change etf-remote-data-persist. Update Purpose after archive.
## Requirements
### Requirement: Read endpoints mirror data types and return JSON
The system SHALL expose the following GET endpoints, all returning JSON responses, all under the `/api/etf/` prefix:

| Method | Path | Returns |
|---|---|---|
| `GET` | `/api/etf/symbols` | `{"symbols": ["QQQ", "SPY", ...]}` (distinct, sorted) |
| `GET` | `/api/etf/quote/{symbol}?limit=480` | `{"symbol": "QQQ", "quotes": [{ts, price, pre_market_price, post_market_price, volume}, ...]}` (newest first) |
| `GET` | `/api/etf/fundamentals/{symbol}` | `{"symbol": "QQQ", "as_of": "...", "pe": 32.4, "pb": null, "dividend_yield": 0.0025, "dividend_rate": 1.77}` |
| `GET` | `/api/etf/holdings/{symbol}` | `{"symbol": "QQQ", "as_of_date": "...", "holdings": [{symbol, name, weight_pct}, ...]}` |
| `GET` | `/api/etf/sector-weights/{symbol}` | `{"symbol": "QQQ", "as_of_date": "...", "sectors": [{sector, weight_pct}, ...]}` |
| `GET` | `/api/etf/equity-holdings/{symbol}` | `{"symbol": "QQQ", "as_of_date": "...", "holdings": [{symbol, name, weight_pct, pe, pb, ps}, ...]}` |
| `GET` | `/api/etf/performance/{symbol}` | `{"symbol": "QQQ", "as_of_date": "...", "ytd": 0.12, "1y": 0.25, "3y": 0.40, "5y": 0.95, "10y": 4.10}` |
| `GET` | `/api/etf/esg/{symbol}` | `{"symbol": "QQQ", "as_of_date": "...", "total_esg": 18.2, "environment": 5.0, "social": 7.1, "governance": 6.1}` |
| `GET` | `/api/etf/news/{symbol}?page=1&page_size=20` | `{"symbol": "QQQ", "page": 1, "page_size": 20, "total": 47, "news": [{url, title, publisher, published_at, summary}, ...]}` |

#### Scenario: Quote endpoint with limit
- **WHEN** `GET /api/etf/quote/QQQ?limit=10` is called
- **THEN** the response contains the 10 most recent quote rows for QQQ, ordered by `ts` DESC

#### Scenario: Fundamentals endpoint missing symbol
- **WHEN** `GET /api/etf/fundamentals/QQQ` is called and there is no `etf_fundamentals` row for QQQ
- **THEN** the response is HTTP 404 with `{"detail": "no fundamentals for QQQ"}`

#### Scenario: News pagination
- **WHEN** `GET /api/etf/news/QQQ?page=2&page_size=20` is called and there are 47 total news items
- **THEN** the response contains news items 21-40, ordered by `published_at` DESC, and `total: 47`

#### Scenario: Symbols endpoint
- **WHEN** `GET /api/etf/symbols` is called and 17 distinct symbols have any data
- **THEN** the response is `{"symbols": ["AGG", "ARKK", "BND", ..., "VTI"]}` (alphabetical, deduplicated)

### Requirement: Read endpoints are not protected by HMAC
The read endpoints MUST NOT be wrapped by the HMAC middleware. They are protected only by CORS (already configured for the frontend) and the IP rate limiter.

#### Scenario: Read endpoint with no HMAC headers
- **WHEN** `GET /api/etf/fundamentals/QQQ` is called with no HMAC headers
- **THEN** the response is served normally

### Requirement: Read endpoints emit CORS headers compatible with the existing frontend
The read endpoints MUST emit `Access-Control-Allow-Origin` headers consistent with the rest of the backend (already configured at the FastAPI app level).

#### Scenario: CORS preflight
- **WHEN** a preflight `OPTIONS` request is sent to a read endpoint from a known frontend origin
- **THEN** the response includes the appropriate CORS headers

### Requirement: Read endpoints expose last-ingest metadata on the existing `/health`
The system MUST extend the existing `/health` endpoint (or add `/api/etf/health` if `/health` is too constrained) to include a snapshot of the most recent ingest for diagnostic purposes:
```json
{
  "status": "ok",
  "etf": {
    "last_ingest_at": "2026-06-29T03:14:00Z",
    "last_batch_id": "2026-06-29T03:14:00Z-etf_quote",
    "symbols_covered": 17
  }
}
```

#### Scenario: Health check with ETF status
- **WHEN** `GET /health` is called and at least one ingest has succeeded
- **THEN** the response includes `etf.last_ingest_at` and `etf.symbols_covered`

#### Scenario: Health check with no ingest yet
- **WHEN** `GET /health` is called before any ingest
- **THEN** the response includes `etf.last_ingest_at: null`

