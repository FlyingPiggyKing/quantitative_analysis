## ADDED Requirements

### Requirement: K-line data retrieval
The system SHALL provide historical K-line (OHLCV) data for Chinese A-shares stocks.

#### Scenario: Fetch daily K-line data
- **WHEN** user requests `/api/stock/{symbol}/kline?days=100&period=daily`
- **THEN** system returns up to 100 days of daily OHLCV data
- **AND** dates are in yyyy-mm-dd format
- **AND** data includes: date, open, high, low, close, volume, amount, change_pct

#### Scenario: Fetch weekly K-line data
- **WHEN** user requests `/api/stock/{symbol}/kline?period=weekly`
- **THEN** system returns weekly aggregated OHLCV data

#### Scenario: Fetch monthly K-line data
- **WHEN** user requests `/api/stock/{symbol}/kline?period=monthly`
- **THEN** system returns monthly aggregated OHLCV data

#### Scenario: K-line with adjustment
- **WHEN** user requests `/api/stock/{symbol}/kline?adjust=qfq` (default)
- **THEN** system returns forward-adjusted prices
- **WHEN** user requests `/api/stock/{symbol}/kline?adjust=no`
- **THEN** system returns unadjusted prices

### Requirement: K-line chart visualization
The frontend SHALL display K-line data as an interactive candlestick chart.

#### Scenario: Display candlestick chart
- **WHEN** stock data is loaded
- **THEN** chart SHALL display candlestick series with up/down colors
- **AND** red candles for price increase, green candles for price decrease

#### Scenario: Display volume histogram
- **WHEN** stock data is loaded
- **THEN** chart SHALL display volume as histogram below candlesticks
- **AND** volume bars colored according to price direction

#### Scenario: Chart time scale
- **WHEN** chart is rendered
- **THEN** time scale SHALL fit to data range
- **AND** time labels SHALL be visible
