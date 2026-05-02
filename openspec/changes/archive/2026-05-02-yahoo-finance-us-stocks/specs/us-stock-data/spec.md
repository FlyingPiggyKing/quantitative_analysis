## MODIFIED Requirements

### Requirement: US stock symbol normalization

**Original**: The system SHALL normalize US stock symbols to Tushare `SYMBOL.US` format for API calls.

**Updated**: The system SHALL normalize US stock symbols to uppercase without exchange suffix for Yahoo Finance API calls.

#### Scenario: US stock symbol already normalized
- **WHEN** `_us_symbol_to_yf_code("AAPL")` is called
- **THEN** returns `"AAPL"`

#### Scenario: US stock symbol with .US suffix
- **WHEN** `_us_symbol_to_yf_code("GOOGL.US")` is called
- **THEN** strips suffix and returns `"GOOGL"`

#### Scenario: US stock symbol is lower case
- **WHEN** `_us_symbol_to_yf_code("tsla")` is called
- **THEN** returns `"TSLA"`

### Requirement: US stock basic info retrieval

**Original**: The system SHALL fetch basic US stock information (name, market, sector) via Tushare `us_stock_basic` endpoint.

**Updated**: The system SHALL fetch basic US stock information (name, market, sector) via Yahoo Finance `ticker.info` API.

#### Scenario: Fetch existing US stock info
- **WHEN** user requests `/api/stock/GOOGL`
- **AND** stock exists in Yahoo Finance US database
- **THEN** system returns JSON with symbol, name, market="US", sector fields

#### Scenario: Fetch non-existent US stock
- **WHEN** user requests `/api/stock/INVALID`
- **THEN** system returns error message indicating stock not found

### Requirement: US stock K-line data retrieval

**Original**: The system SHALL fetch historical K-line data for US stocks via Tushare `us_daily` endpoint.

**Updated**: The system SHALL fetch historical K-line data for US stocks via Yahoo Finance `ticker.history()` API.

#### Scenario: Fetch US stock daily K-line
- **WHEN** user requests `/api/stock/GOOGL/kline?days=100`
- **THEN** system returns K-line data with date, open, close, high, low, volume fields

#### Scenario: Fetch US stock with insufficient data
- **WHEN** user requests K-line for a stock with no data
- **THEN** system returns error message "No data found"

### Requirement: US stock real-time quote

**Original**: The system SHALL fetch real-time quote data for US stocks.

**Updated**: The system SHALL fetch real-time quote data for US stocks via Yahoo Finance.

#### Scenario: Fetch US stock realtime quote
- **WHEN** user requests `/api/stock/TSLA/realtime`
- **THEN** system returns current price, change_pct, volume, high, low, open fields

### Requirement: US stock valuation metrics

**Original**: The system SHALL fetch US stock daily basic metrics (PE, PB, turnover_rate) when available from Tushare.

**Updated**: The system SHALL fetch US stock valuation metrics (PE, PB, EPS, dividend yield, market cap) from Yahoo Finance `ticker.info` API.

#### Scenario: Fetch US stock valuation
- **WHEN** user requests `/api/stock/GOOGL/valuation`
- **THEN** system returns pe_ttm (trailingPE), pb (priceToBook), market_cap (marketCap), dividend_yield (dividendYield)

#### Scenario: US stock valuation data not available
- **WHEN** Yahoo Finance does not provide valuation data for a US stock
- **THEN** system returns null values for pe_ttm, pb, market_cap, dividend_yield without error
