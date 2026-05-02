## ADDED Requirements

### Requirement: Fetch US stock fundamental metrics from Yahoo Finance
The system SHALL fetch US stock fundamental metrics via Yahoo Finance `ticker.info` API using the `yfinance` library.

#### Scenario: Fetch fundamental metrics for valid US stock
- **WHEN** `USStockService.get_info("AAPL")` is called
- **THEN** system returns dictionary containing: `trailingPE`, `priceToBook`, `trailingEps`, `dividendYield`, `marketCap`, `currentPrice`, `fiftyTwoWeekHigh`, `fiftyTwoWeekLow`

#### Scenario: Fetch fundamental metrics for symbol with .US suffix
- **WHEN** `USStockService.get_info("AAPL.US")` is called
- **THEN** system strips `.US` suffix and fetches from Yahoo Finance; returns same data as without suffix

#### Scenario: Handle missing fundamental field
- **WHEN** `ticker.info` does not contain a requested field
- **THEN** system returns `None` for that field without error

#### Scenario: Handle invalid/empty symbol
- **WHEN** `USStockService.get_info("INVALID_SYMBOL_123")` is called
- **THEN** system returns `None` for all fields or raises `YfDataNotFoundError`

### Requirement: Fetch US stock daily K-line (OHLCV) from Yahoo Finance
The system SHALL fetch historical daily K-line data via Yahoo Finance `ticker.history()` API.

#### Scenario: Fetch daily K-line data
- **WHEN** `USStockService.get_kline_data("AAPL", days=100, period="daily", adjust="")` is called
- **THEN** system returns DataFrame with columns: date, open, close, high, low, volume

#### Scenario: Fetch K-line with .US suffix symbol
- **WHEN** `USStockService.get_kline_data("TSLA.US", days=50, period="daily", adjust="")` is called
- **THEN** system strips `.US` suffix and fetches from Yahoo Finance

#### Scenario: Handle insufficient K-line data
- **WHEN** requested `days` exceeds available data for a symbol
- **THEN** system returns all available data without error

### Requirement: Symbol normalization for Yahoo Finance
The system SHALL normalize US stock symbols before calling Yahoo Finance API.

#### Scenario: Symbol already clean (no suffix)
- **WHEN** `_normalize_us_symbol("AAPL")` is called
- **THEN** returns `"AAPL"`

#### Scenario: Symbol has .US suffix
- **WHEN** `_normalize_us_symbol("AAPL.US")` is called
- **THEN** returns `"AAPL"`

#### Scenario: Symbol is lowercase
- **WHEN** `_normalize_us_symbol("tsla")` is called
- **THEN** returns `"TSLA"`

### Requirement: US stock real-time quote from Yahoo Finance
The system SHALL fetch real-time quote data for US stocks via Yahoo Finance `ticker.fast_info` or `ticker.info`.

#### Scenario: Fetch realtime quote
- **WHEN** `USStockService.get_realtime("AAPL")` is called
- **THEN** system returns: currentPrice, previousClose, volume, dayHigh, dayLow, dayOpen

### Requirement: US stock valuation metrics from Yahoo Finance
The system SHALL fetch US stock valuation metrics via Yahoo Finance.

#### Scenario: Fetch valuation metrics
- **WHEN** `USStockService.get_valuation("AAPL")` is called
- **THEN** system returns: pe_ttm (trailingPE), pb (priceToBook), market_cap (marketCap), dividend_yield (dividendYield)

#### Scenario: Valuation data not available in Yahoo Finance
- **WHEN** Yahoo Finance returns `None` for a valuation field
- **THEN** system returns `None` for that field without error
