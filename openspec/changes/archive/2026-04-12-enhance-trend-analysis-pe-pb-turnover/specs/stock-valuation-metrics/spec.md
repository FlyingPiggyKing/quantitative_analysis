## ADDED Requirements

### Requirement: Fetch daily valuation metrics from Tushare
The system SHALL fetch daily valuation metrics for a given stock symbol using Tushare Pro `daily_basic` API, returning PE(TTM), PB ratio, turnover rate, total market cap, and circulation market cap.

#### Scenario: Successful fetch returns historical and latest data
- **WHEN** `get_daily_basic(symbol, days)` is called with a valid A-share symbol
- **THEN** the service SHALL return a dict with `symbol`, `data` (list of daily records), and `latest` (most recent record)
- **AND** each record SHALL include: `trade_date`, `pe_ttm`, `pb`, `turnover_rate`, `total_mv`, `circ_mv`

#### Scenario: No data available
- **WHEN** Tushare returns an empty DataFrame for the requested date range
- **THEN** the service SHALL return `{"symbol": <symbol>, "error": "No daily_basic data"}`
- **AND** no exception SHALL propagate to the caller

#### Scenario: Tushare API error
- **WHEN** Tushare raises an exception during the API call
- **THEN** the service SHALL catch the exception and return `{"symbol": <symbol>, "error": <error message>}`

### Requirement: Valuation metrics REST endpoint
The system SHALL expose a GET endpoint at `/api/stock/{symbol}/valuation` that returns daily valuation metrics for the requested stock.

#### Scenario: Valid request
- **WHEN** a GET request is made to `/api/stock/{symbol}/valuation` with optional `days` query param (default 30, range 1–365)
- **THEN** the response SHALL return the result of `get_daily_basic(symbol, days)` as JSON

#### Scenario: Error response passthrough
- **WHEN** `get_daily_basic` returns an error dict
- **THEN** the endpoint SHALL return that dict as JSON (not raise an HTTP error)
