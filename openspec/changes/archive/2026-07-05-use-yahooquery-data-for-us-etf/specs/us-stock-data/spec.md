## ADDED Requirements

### Requirement: US ETF valuation sources PE from yahooquery
The system SHALL source PE for US ETF symbols from `etf_remote.db.etf_fundamentals.pe` (populated by the yahooquery-based pusher) instead of from Futu, while continuing to source `total_mv`, `turnover_rate`, and the historical PE series from Futu.

#### Scenario: US ETF PE comes from yahooquery
- **WHEN** `get_daily_basic("QQQ", 30)` is called via `USStockService`
- **AND** `etf_fundamentals` has a row for QQQ with `pe: 33.295002`
- **THEN** the returned `latest.pe_ttm` SHALL equal `33.295002` (from yahooquery)
- **AND** the returned `latest.total_mv` SHALL come from Futu

#### Scenario: US non-ETF stock PE continues to come from Futu
- **WHEN** `get_daily_basic("AAPL", 30)` is called via `USStockService`
- **AND** `AAPL` is not in `etf_fundamentals`
- **THEN** the returned `latest.pe_ttm` SHALL come from Futu unchanged
- **AND** the response SHALL include `is_etf: false`

#### Scenario: US ETF dividend fields appear on the response
- **WHEN** `get_daily_basic("QQQ", 30)` is called via `USStockService`
- **AND** `etf_fundamentals` has a row for QQQ with `dividend_yield: 0.002403585, dividend_rate: 1.77`
- **THEN** the response SHALL include `latest.dividend_yield: 0.002403585`
- **AND** the response SHALL include `latest.dividend_rate: 1.77`

### Requirement: US valuation routes through ETF-aware wrapper
The system SHALL make `USStockService.get_daily_basic(symbol, days)` delegate to `etf_valuation.get_etf_aware_daily_basic(symbol, days)` rather than calling `FutuQuoteService.get_daily_basic` directly.

#### Scenario: Existing US callers see the new fields
- **WHEN** any caller invokes `USStockService.get_daily_basic("QQQ", 30)` after this change
- **THEN** the response SHALL include `is_etf`, `dividend_yield`, `dividend_rate`, and `as_of` keys

#### Scenario: Non-ETF US callers see no behaviour change
- **WHEN** any caller invokes `USStockService.get_daily_basic("AAPL", 30)` after this change
- **THEN** the response SHALL be byte-identical to the pre-change Futu response, with `is_etf: false` added