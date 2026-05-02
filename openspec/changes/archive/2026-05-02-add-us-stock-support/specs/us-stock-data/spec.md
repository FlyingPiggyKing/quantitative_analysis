# us-stock-data Specification

## Purpose
Enable fetching US stock data (Google, Microsoft, NVIDIA, Tesla, Coca-Cola, etc.) via Tushare Pro API using SYMBOL.US format.

## ADDED Requirements

### Requirement: US stock symbol normalization
The system SHALL normalize US stock symbols to Tushare `SYMBOL.US` format for API calls.

#### Scenario: US stock symbol already has .US suffix
- **WHEN** `_us_symbol_to_ts_code("GOOGL.US")` is called
- **THEN** returns `"GOOGL.US"`

#### Scenario: US stock symbol without suffix
- **WHEN** `_us_symbol_to_ts_code("GOOGL")` is called
- **THEN** returns `"GOOGL.US"`

#### Scenario: US stock symbol is lower case
- **WHEN** `_us_symbol_to_ts_code("tsla")` is called
- **THEN** returns `"TSLA.US"`

### Requirement: US stock basic info retrieval
The system SHALL fetch basic US stock information (name, market, sector) via Tushare `us_stock_basic` endpoint.

#### Scenario: Fetch existing US stock info
- **WHEN** user requests `/api/stock/GOOGL`
- **AND** stock exists in Tushare US database
- **THEN** system returns JSON with symbol, name, market="US", sector fields

#### Scenario: Fetch non-existent US stock
- **WHEN** user requests `/api/stock/INVALID`
- **THEN** system returns error message indicating stock not found

### Requirement: US stock K-line data retrieval
The system SHALL fetch historical K-line data for US stocks via Tushare `us_daily` endpoint.

#### Scenario: Fetch US stock daily K-line
- **WHEN** user requests `/api/stock/GOOGL/kline?days=100`
- **THEN** system returns K-line data with date, open, close, high, low, volume fields

#### Scenario: Fetch US stock with insufficient data
- **WHEN** user requests K-line for a stock with no data
- **THEN** system returns error message "No data found"

### Requirement: US stock real-time quote
The system SHALL fetch real-time quote data for US stocks.

#### Scenario: Fetch US stock realtime quote
- **WHEN** user requests `/api/stock/TSLA/realtime`
- **THEN** system returns current price, change_pct, volume, high, low, open fields

### Requirement: US stock valuation metrics
The system SHALL fetch US stock daily basic metrics (PE, PB, turnover_rate) when available from Tushare.

#### Scenario: Fetch US stock daily basic
- **WHEN** user requests `/api/stock/GOOGL/valuation`
- **THEN** system returns pe_ttm, pb, turnover_rate if available; returns null for unavailable fields

#### Scenario: US stock valuation data not available
- **WHEN** Tushare does not provide valuation data for a US stock
- **THEN** system returns null values for pe_ttm, pb, turnover_rate without error
