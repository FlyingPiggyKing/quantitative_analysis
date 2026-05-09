## MODIFIED Requirements

### Requirement: US stock symbol normalization
**Original text:** The system SHALL normalize US stock symbols to Tushare `SYMBOL.US` format for API calls.

**Updated text:** The system SHALL normalize US stock symbols to Futu `US.SYMBOL` format (e.g., `US.AAPL`, `US.TSLA`) for API calls.

#### Scenario: US stock symbol already has .US suffix
- **WHEN** `_us_symbol_to_futu_code("AAPL.US")` is called
- **THEN** returns `"US.AAPL"`

#### Scenario: US stock symbol is plain ticker
- **WHEN** `_us_symbol_to_futu_code("AAPL")` is called
- **THEN** returns `"US.AAPL"`

#### Scenario: US stock symbol is lowercase
- **WHEN** `_us_symbol_to_futu_code("tsla")` is called
- **THEN** returns `"US.TSLA"`

### Requirement: US stock basic info retrieval
**Original text:** The system SHALL fetch basic US stock information (name, market, sector) via Tushare `us_stock_basic` endpoint.

**Updated text:** The system SHALL fetch basic US stock information (name, market, sector) via Futu OpenAPI `get_stock_info` endpoint.

#### Scenario: Fetch existing US stock info
- **WHEN** user requests `/api/stock/AAPL`
- **AND** stock exists in Futu US database
- **THEN** system returns JSON with symbol, name, market="US", sector fields

#### Scenario: Fetch non-existent US stock
- **WHEN** user requests `/api/stock/INVALID`
- **THEN** system returns error message indicating stock not found

### Requirement: US stock K-line data retrieval
**Original text:** The system SHALL fetch historical K-line data for US stocks via Tushare `us_daily` endpoint.

**Updated text:** The system SHALL fetch historical K-line data for US stocks via Futu OpenAPI `get_kline` endpoint.

#### Scenario: Fetch US stock daily K-line
- **WHEN** user requests `/api/stock/AAPL/kline?days=100`
- **THEN** system returns K-line data with date, open, close, high, low, volume, change_pct fields

#### Scenario: Fetch US stock with insufficient data
- **WHEN** user requests K-line for a stock with no data
- **THEN** system returns error message "No data found"

### Requirement: US stock real-time quote
**Original text:** The system SHALL fetch real-time quote data for US stocks.

**Updated text:** The system SHALL fetch real-time quote data for US stocks via Futu OpenAPI `get_snapshot` endpoint.

#### Scenario: Fetch US stock realtime quote
- **WHEN** user requests `/api/stock/AAPL/realtime`
- **THEN** system returns current price, change_pct, volume, high, low, open, close_prev fields

### Requirement: US stock valuation metrics
**Original text:** The system SHALL fetch US stock daily basic metrics (PE, PB, turnover_rate) when available from Tushare.

**Updated text:** The system SHALL fetch US stock valuation metrics (PE TTM, PB, turnover_rate, market_cap) via Futu OpenAPI `get_snapshot` endpoint.

#### Scenario: Fetch US stock valuation metrics
- **WHEN** user requests `/api/stock/AAPL/valuation`
- **THEN** system returns pe_ttm, pb, turnover_rate, total_mv, circ_mv fields from Futu snapshot

#### Scenario: US stock valuation data not available
- **WHEN** Futu does not provide valuation data for a US stock
- **THEN** system returns null values for pe_ttm, pb, turnover_rate without error
