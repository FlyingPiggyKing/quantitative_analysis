## ADDED Requirements

### Requirement: Fetch US stock snapshot via Futu OpenAPI
The system SHALL fetch US stock market snapshot data (PE, PB, turnover rate, market cap) via Futu OpenAPI `get_snapshot` endpoint.

#### Scenario: Successful snapshot fetch returns valuation metrics
- **WHEN** `FutuQuoteService.get_snapshot("US.AAPL")` is called
- **THEN** the service SHALL return a dict with `symbol`, `name`, `pe_ttm`, `pb`, `turnover_rate`, `market_cap`
- **AND** the response SHALL match the existing `USStockService.get_daily_basic` response format

#### Scenario: Stock not found
- **WHEN** `FutuQuoteService.get_snapshot("US.INVALID")` is called with a non-existent symbol
- **THEN** the service SHALL return `{"symbol": "US.INVALID", "error": "Stock not found"}`

#### Scenario: Futu API connection failure
- **WHEN** Futu OpenD is not reachable
- **THEN** the service SHALL catch the exception and return `{"symbol": <symbol>, "error": <error message>}`

### Requirement: Fetch US stock K-line data via Futu OpenAPI
The system SHALL fetch historical K-line data for US stocks via Futu OpenAPI `get_kline` endpoint.

#### Scenario: Fetch daily K-line data
- **WHEN** `FutuQuoteService.get_kline("US.AAPL", days=100, ktype="1d")` is called
- **THEN** the service SHALL return K-line data with `date`, `open`, `close`, `high`, `low`, `volume`, `change_pct` fields
- **AND** the response SHALL match the existing `USStockService.get_kline_data` response format

#### Scenario: Fetch weekly K-line data
- **WHEN** `FutuQuoteService.get_kline("US.AAPL", days=52, ktype="1w")` is called
- **THEN** the service SHALL return weekly K-line data

#### Scenario: No K-line data available
- **WHEN** Futu returns empty data for the requested symbol
- **THEN** the service SHALL return `{"symbol": <symbol>, "error": "No data found"}`

### Requirement: Fetch US stock info via Futu OpenAPI
The system SHALL fetch basic US stock information (name, market, sector) via Futu OpenAPI.

#### Scenario: Fetch existing US stock info
- **WHEN** `FutuQuoteService.get_stock_info("US.AAPL")` is called
- **THEN** the service SHALL return JSON with `symbol`, `name`, `market="US"`, `sector` fields
- **AND** the response SHALL match the existing `USStockService.get_stock_info` response format

#### Scenario: Fetch non-existent US stock
- **WHEN** `FutuQuoteService.get_stock_info("US.INVALID")` is called
- **THEN** the service SHALL return error message indicating stock not found

### Requirement: US stock realtime quote via Futu OpenAPI
The system SHALL fetch real-time quote data for US stocks via Futu OpenAPI snapshot.

#### Scenario: Fetch realtime quote
- **WHEN** `FutuQuoteService.get_realtime_quote("US.AAPL")` is called
- **THEN** the service SHALL return current `price`, `change_pct`, `volume`, `high`, `low`, `open`, `close_prev`
- **AND** the response SHALL match the existing `USStockService.get_realtime_quote` response format

### Requirement: Reuse existing caching mechanism
The system SHALL use the existing `_YFCache` pattern with 5-minute TTL for Futu queries to avoid rate limiting.

#### Scenario: Cache hit returns cached data
- **WHEN** a second request for the same symbol is made within 5 minutes
- **THEN** the service SHALL return cached data without calling Futu API

#### Scenario: Cache miss fetches from Futu
- **WHEN** no cached data exists or cache has expired
- **THEN** the service SHALL call Futu API and cache the result

### Requirement: Support batch operations
The system SHALL support batch fetching of multiple US stock symbols in a single request.

#### Scenario: Batch fetch stock info
- **WHEN** `FutuQuoteService.get_stock_info_batch(["US.AAPL", "US.TSLA"])` is called
- **THEN** the service SHALL return results for all symbols in a single response
- **AND** errors SHALL be collected separately from results

#### Scenario: Batch fetch valuation metrics
- **WHEN** `FutuQuoteService.get_daily_basic_batch(["US.AAPL", "US.TSLA"], days=30)` is called
- **THEN** the service SHALL return results for all symbols
- **AND** the response SHALL match the existing batch response format
