## ADDED Requirements

### Requirement: Fetch A-Share Main Force Net Inflow via Tushare
The system SHALL fetch A-share main force net inflow using Tushare Pro `moneyflow_ths` API, returning 30-day daily history including net_amount, buy_lg_amount, and net_d5_amount.

#### Scenario: Successful fetch returns 30-day history
- **WHEN** `get_ashare_moneyflow(symbol, days=30)` is called with a valid A-share symbol (SH prefix)
- **THEN** the service SHALL return a dict with `symbol`, `market: "A-share"`, `data` (list of 30 daily records), and `latest` (most recent record)
- **AND** each record SHALL include: `trade_date`, `net_amount` (万元), `buy_lg_amount` (万元), `net_d5_amount` (万元)
- **AND** `net_5d_total` SHALL be the sum of last 5 trading days `buy_lg_amount`

#### Scenario: No data available
- **WHEN** Tushare returns an empty DataFrame for the requested date range
- **THEN** the service SHALL return `{"symbol": <symbol>, "market": "A-share", "data": [], "error": "No moneyflow_ths data"}`

#### Scenario: Tushare API error
- **WHEN** Tushare raises an exception during the API call
- **THEN** the service SHALL catch the exception and return `{"symbol": <symbol>, "market": "A-share", "error": <error message>}`

#### Scenario: Invalid A-share symbol (not SH/SZ prefix)
- **WHEN** `get_ashare_moneyflow` is called with a non A-share symbol
- **THEN** the service SHALL return `{"symbol": <symbol>, "market": "A-share", "error": "Not an A-share symbol"}`

### Requirement: A-Share Money Flow REST Endpoint
The system SHALL expose a GET endpoint at `/api/stock/{symbol}/moneyflow` that returns A-share money flow data when the symbol has SH or SZ prefix.

#### Scenario: Valid A-share request
- **WHEN** a GET request is made to `/api/stock/SH600000/moneyflow`
- **THEN** the response SHALL return the result of `get_ashare_moneyflow("SH600000", days=30)` as JSON

#### Scenario: Error response passthrough
- **WHEN** `get_ashare_moneyflow` returns an error dict
- **THEN** the endpoint SHALL return that dict as JSON with appropriate status code (200 for no-data, 500 for API errors)
