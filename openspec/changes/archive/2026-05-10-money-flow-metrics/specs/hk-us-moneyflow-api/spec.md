## ADDED Requirements

### Requirement: Fetch HK/US Main Force Net Inflow via Futu OpenAPI
The system SHALL fetch HK and US stock main force net inflow using Futu `get_capital_flow` API, returning 30-day daily history including main_in_flow.

#### Scenario: Successful fetch for HK stock
- **WHEN** `get_hk_us_moneyflow("HK.00700", days=30)` is called
- **THEN** the service SHALL return a dict with `symbol`, `market: "HK"`, `data` (list of daily records), and `latest` (most recent record)
- **AND** each record SHALL include: `date`, `main_in_flow` (HKD, positive = net inflow)

#### Scenario: Successful fetch for US stock
- **WHEN** `get_hk_us_moneyflow("US.AAPL", days=30)` is called
- **THEN** the service SHALL return a dict with `symbol`, `market: "US"`, `data` (list of daily records), and `latest` (most recent record)
- **AND** each record SHALL include: `date`, `main_in_flow` (USD, positive = net inflow)

#### Scenario: Futu connection error
- **WHEN** Futu `get_capital_flow` raises an exception
- **THEN** the service SHALL catch the exception and return `{"symbol": <symbol>, "market": <market>, "error": <error message>}`

#### Scenario: Market detection from symbol
- **WHEN** `get_hk_us_moneyflow("HK.00700")` is called
- **THEN** the market SHALL be detected as "HK" from the "HK." prefix
- **AND** when `get_hk_us_moneyflow("US.AAPL")` is called, market SHALL be detected as "US"

### Requirement: Unified Money Flow API Endpoint
The system SHALL expose a single GET endpoint at `/api/stock/{symbol}/moneyflow` that handles all markets (A-share, HK, US) by detecting market from symbol prefix.

#### Scenario: A-share symbol routing
- **WHEN** GET request to `/api/stock/SH600000/moneyflow`
- **THEN** route to Tushare `moneyflow_ths` service
- **AND** return data with `market: "A-share"`

#### Scenario: HK symbol routing
- **WHEN** GET request to `/api/stock/HK.00700/moneyflow`
- **THEN** route to Futu `get_capital_flow` service
- **AND** return data with `market: "HK"`

#### Scenario: US symbol routing
- **WHEN** GET request to `/api/stock/US.AAPL/moneyflow`
- **THEN** route to Futu `get_capital_flow` service
- **AND** return data with `market: "US"`

#### Scenario: Unsupported symbol format
- **WHEN** GET request to `/api/stock/INVALID/moneyflow`
- **THEN** return `{"error": "Unknown market for symbol: INVALID"}` with status 400
