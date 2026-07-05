# etf-fetcher Specification

## Purpose
TBD - created by archiving change etf-fetcher-pusher. Update Purpose after archive.
## Requirements
### Requirement: ETF data fetcher returns normalized records per data type
The system SHALL provide a fetcher module under `remote_data/fetcher/` with one function per `data_type`. Each function MUST accept a list of symbols and return a list of normalized record dicts (one per symbol per applicable time/key). The function MUST NOT depend on any code outside `remote_data/`.

#### Scenario: Fetch current quotes
- **WHEN** `fetch_quotes(["QQQ", "SPY"])` is called
- **THEN** the system returns a list with one record per symbol containing `symbol`, `ts`, `price`, `pre_market_price`, `post_market_price`, `volume`

#### Scenario: Fetch fundamentals snapshot
- **WHEN** `fetch_fundamentals(["QQQ"])` is called
- **THEN** the system returns a list with one record per symbol containing `symbol`, `as_of` (ISO8601 UTC), `pe`, `pb`, `dividend_yield`, `dividend_rate`

#### Scenario: Fetch top 10 holdings
- **WHEN** `fetch_holdings(["QQQ"])` is called
- **THEN** the system returns a list with one record per symbol containing `symbol`, `as_of_date`, `holdings` (array of {symbol, name, weight_pct})

#### Scenario: Fetch sector weightings
- **WHEN** `fetch_sector_weightings(["QQQ"])` is called
- **THEN** the system returns a list with one record per symbol containing `symbol`, `as_of_date`, `sectors` (array of {sector, weight_pct})

#### Scenario: Fetch multi-period performance
- **WHEN** `fetch_performance(["QQQ"])` is called
- **THEN** the system returns a list with one record per symbol containing `symbol`, `as_of_date`, and `ytd`, `1y`, `3y`, `5y`, `10y` returns (decimal fractions; nullable for unavailable)

#### Scenario: Fetch equity holdings with portfolio PE/PB/PS
- **WHEN** `fetch_equity_holdings(["QQQ"])` is called
- **THEN** the system returns a list with one record per symbol containing `symbol`, `as_of_date`, `holdings` (array including per-holding PE/PB/PS)

#### Scenario: Fetch ESG scores
- **WHEN** `fetch_esg(["QQQ"])` is called
- **THEN** the system returns a list with one record per symbol containing `symbol`, `as_of_date`, `total_esg`, `environment`, `social`, `governance` (nullable fields OK)

#### Scenario: One symbol fails during batch fetch
- **WHEN** `fetch_quotes(["QQQ", "BAD_SYMBOL"])` is called and yahooquery raises for `BAD_SYMBOL`
- **THEN** the system returns records for the successful symbols and writes a row to `fetch_log` for the failed one; it MUST NOT raise

### Requirement: Fetcher normalizes raw yahooquery output
The system MUST convert raw yahooquery responses to the normalized record shapes described above before returning. Downstream pusher and store modules MUST NOT import from `yahooquery` directly.

#### Scenario: Timestamp fields are always ISO8601 UTC
- **WHEN** any fetcher returns records with a timestamp
- **THEN** that timestamp MUST be a string in ISO8601 UTC form with a `Z` suffix

#### Scenario: Timestamp inputs from yahooquery may be epoch or ISO date string
- **WHEN** the fetcher receives a `regularMarketTime`, `preMarketTime`, or `postMarketTime` value from yahooquery
- **THEN** the fetcher MUST accept both shapes: an integer/float epoch in seconds AND an ISO date string (with or without trailing `Z`); both shapes are converted to a single canonical ISO8601 UTC `Z`-suffixed string before being placed in the record; values that cannot be parsed in either form are treated as missing and the corresponding record is dropped with a `fetch_log` error entry

#### Scenario: Missing fields are null, not absent
- **WHEN** a yahooquery field is unavailable (e.g., `preMarketPrice` for a non-trading moment)
- **THEN** the normalized record MUST include the key with value `null`

### Requirement: Fetcher handles rate limits and transient failures
The fetcher MUST retry up to `YAHOOQUERY_MAX_RETRIES` (default 3) times with exponential backoff starting at `YAHOOQUERY_BACKOFF_SECONDS` (default 2) on transient errors (HTTP 429, 5xx, connection errors).

#### Scenario: Hit rate limit
- **WHEN** yahooquery returns HTTP 429
- **THEN** the fetcher waits the backoff and retries up to the configured cap; if all retries fail, the record is logged and the function returns the partial result without raising

#### Scenario: Network timeout
- **WHEN** the yahooquery call times out
- **THEN** the fetcher retries with backoff; final failure is logged and the function returns successfully with whatever subset of symbols was retrieved

