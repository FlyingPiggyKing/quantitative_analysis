## ADDED Requirements

### Requirement: HK stock symbol normalization
The system SHALL normalize HK stock symbols to Futu `HK.XXXXX` format for API calls.

#### Scenario: HK stock symbol already has HK. prefix
- **WHEN** `_symbol_to_hk_futu_code("HK.00700")` is called
- **THEN** returns `"HK.00700"`

#### Scenario: HK stock symbol without prefix
- **WHEN** `_symbol_to_hk_futu_code("00700")` is called
- **THEN** returns `"HK.00700"`

#### Scenario: HK stock symbol with leading zeros
- **WHEN** `_symbol_to_hk_futu_code("00700")` is called
- **THEN** returns `"HK.00700"` with leading zeros preserved

#### Scenario: Reverse conversion from Futu code
- **WHEN** `_hk_futu_code_to_symbol("HK.00700")` is called
- **THEN** returns `"00700"`

### Requirement: HK stock symbol detection
The system SHALL detect HK stock symbols by pattern (4-5 digits) and route to HK stock service.

#### Scenario: 5-digit HK stock symbol detected
- **WHEN** `_is_hk_stock_symbol("00700")` is called
- **THEN** returns `True`

#### Scenario: 4-digit HK stock symbol detected
- **WHEN** `_is_hk_stock_symbol("9988")` is called
- **THEN** returns `True`

#### Scenario: 6-digit A-share symbol not detected as HK
- **WHEN** `_is_hk_stock_symbol("600938")` is called
- **THEN** returns `False`

#### Scenario: US stock letter symbol not detected as HK
- **WHEN** `_is_hk_stock_symbol("AAPL")` is called
- **THEN** returns `False`

### Requirement: HK stock basic info retrieval
The system SHALL fetch basic HK stock information (name, market, sector) via Futu OpenAPI.

#### Scenario: Fetch existing HK stock info
- **WHEN** user requests `/api/stock/00700`
- **AND** the symbol is detected as HK stock
- **THEN** system returns JSON with symbol, name, market="HK", sector fields
- **AND** name is returned in English (e.g., "TENCENT" for 腾讯) as provided by Futu API

#### Scenario: Fetch non-existent HK stock
- **WHEN** user requests `/api/stock/99999`
- **AND** the symbol is detected as HK stock but does not exist
- **THEN** system returns error message indicating stock not found

### Requirement: HK stock K-line data retrieval
The system SHALL fetch historical K-line data for HK stocks via Futu OpenAPI.

#### Scenario: Fetch HK stock daily K-line
- **WHEN** user requests `/api/stock/00700/kline?days=100`
- **THEN** system returns K-line data with date, open, close, high, low, volume, change_pct fields

#### Scenario: Fetch HK stock with different periods
- **WHEN** user requests `/api/stock/00700/kline?days=100&period=weekly`
- **THEN** system returns weekly K-line data

#### Scenario: Fetch HK stock with adjustment options
- **WHEN** user requests `/api/stock/00700/kline?days=100&adjust=qfq`
- **THEN** system returns forward-adjusted K-line data

### Requirement: HK stock real-time quote
The system SHALL fetch real-time quote data for HK stocks.

#### Scenario: Fetch HK stock realtime quote
- **WHEN** user requests `/api/stock/00700/realtime`
- **THEN** system returns current price, change_pct, volume, high, low, open, close_prev fields

### Requirement: HK stock valuation metrics
The system SHALL fetch HK stock daily basic metrics (PE, PB, turnover_rate) via Futu K-line data.

#### Scenario: Fetch HK stock valuation
- **WHEN** user requests `/api/stock/00700/valuation`
- **THEN** system returns pe_ttm, pb, turnover_rate, total_mv, circ_mv fields if available

#### Scenario: HK stock valuation data not available
- **WHEN** Futu does not provide valuation data for a HK stock
- **THEN** system returns null values for pe_ttm, pb, turnover_rate without error

### Requirement: HK stock technical indicators
The system SHALL calculate and return technical indicators (MACD, RSI, MA) for HK stocks.

#### Scenario: Fetch HK stock indicators
- **WHEN** user requests `/api/stock/00700/indicators`
- **THEN** system returns MACD, RSI, MA data computed from K-line data
