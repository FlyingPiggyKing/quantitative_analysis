## ADDED Requirements

### Requirement: Dragon Tiger List includes valuation metrics
The system SHALL join PE TTM and market cap (市值) into each DragonTigerItem when returning the dragon-tiger-list API response.

#### Scenario: Valuation data available for a stock
- **WHEN** `get_dragon_tiger_list(days)` returns a stock with a valid ts_code
- **AND** `get_daily_basic(ts_code, days=1)` returns valid data
- **THEN** the DragonTigerItem SHALL include `pe_ttm` (from `pe_ttm` field) and `total_mv_yi` (computed as `total_mv / 1e8`)
- **AND** `total_mv_yi` SHALL be formatted to 2 decimal places in 亿元

#### Scenario: Valuation data unavailable for a stock
- **WHEN** `get_daily_basic(ts_code, days=1)` returns an error or empty data
- **THEN** the DragonTigerItem SHALL include `pe_ttm: null` and `total_mv_yi: null`
- **AND** the list SHALL still return successfully with other stocks

#### Scenario: Market cap is zero or negative (suspended stock)
- **WHEN** `get_daily_basic` returns `total_mv = 0` or negative
- **THEN** `total_mv_yi` SHALL be set to `null` and displayed as "-"
