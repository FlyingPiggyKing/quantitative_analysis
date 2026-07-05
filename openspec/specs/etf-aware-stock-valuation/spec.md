# etf-aware-stock-valuation Specification

## Purpose
Define how the backend determines whether a US symbol is an ETF and, when it is, merges yahooquery-sourced fundamentals (PE, PB, dividend yield, dividend rate, as-of timestamp) into the Futu-sourced valuation response exposed at `/api/stock/{symbol}/valuation`. The frontend renders the merged dividend fields as additional header chips when the response includes `is_etf: true`.
## Requirements
### Requirement: Dynamic ETF symbol set
The system SHALL determine "is this symbol an ETF?" dynamically by querying `etf_remote.db.etf_fundamentals` for distinct symbols and caching the result in memory.

#### Scenario: First request populates the cache
- **WHEN** `is_etf(symbol)` is called for the first time after backend startup
- **AND** `etf_fundamentals` contains rows for `QQQ`, `SPY`, `IVV`, `VOO`, `VTI`, `BND`, `AGG`, `ARKK`
- **THEN** the system SHALL execute `SELECT DISTINCT symbol FROM etf_fundamentals`
- **AND** the system SHALL cache the uppercased symbols in an in-memory `set[str]`

#### Scenario: Subsequent membership checks hit the cache
- **WHEN** `is_etf("QQQ")` is called after the cache is populated
- **THEN** the system SHALL return `true` via the cached set without querying the database

#### Scenario: Cache can be refreshed
- **WHEN** `refresh_etf_symbols()` is called (e.g. from the pusher or an admin endpoint)
- **THEN** the system SHALL discard the cached set
- **AND** the next `is_etf()` call SHALL repopulate it from `etf_fundamentals`

#### Scenario: Non-ETF symbol returns false
- **WHEN** `is_etf("AAPL")` is called and `AAPL` is not in `etf_fundamentals`
- **THEN** the system SHALL return `false`

#### Scenario: Symbol comparison is case-insensitive
- **WHEN** `is_etf("qqq")` is called and the cached set contains `"QQQ"`
- **THEN** the system SHALL return `true`

### Requirement: ETF-aware valuation merges yahooquery fundamentals with Futu market data
The system SHALL expose a function `get_etf_aware_daily_basic(symbol, days)` that:
- calls `FutuQuoteService.get_daily_basic(symbol, days)` to obtain the historical series and Futu-snapshot values for `total_mv`, `circ_mv`, `turnover_rate`, and the most recent K-line `pe_ttm` / `pb`
- when `is_etf(symbol)` is true, reads the most recent row from `etf_fundamentals` and merges `pe`, `pb` (when present), `dividend_yield`, `dividend_rate`, and `as_of` into the `latest` record
- when `is_etf(symbol)` is false, returns the Futu response unchanged and adds `is_etf: false` plus null dividend fields

#### Scenario: ETF symbol with row in etf_fundamentals
- **WHEN** `get_etf_aware_daily_basic("QQQ", 30)` is called
- **AND** `etf_fundamentals` has a row for QQQ with `{pe: 33.295002, pb: null, dividend_yield: 0.002403585, dividend_rate: 1.77, as_of: "2026-07-02T03:17:28Z"}`
- **THEN** the system SHALL return a dict with top-level `is_etf: true`
- **AND** `latest.pe_ttm` SHALL equal `33.295002` (overridden from yahooquery)
- **AND** `latest.pb` SHALL be `null` (yahooquery returned null)
- **AND** `latest.dividend_yield` SHALL equal `0.002403585`
- **AND** `latest.dividend_rate` SHALL equal `1.77`
- **AND** `latest.as_of` SHALL equal `"2026-07-02T03:17:28Z"`
- **AND** `latest.total_mv` SHALL come from the Futu snapshot
- **AND** `latest.turnover_rate` SHALL come from the Futu snapshot
- **AND** `data[]` (historical series) SHALL remain the Futu K-line time series

#### Scenario: Non-ETF US stock
- **WHEN** `get_etf_aware_daily_basic("AAPL", 30)` is called
- **AND** `AAPL` is not in the cached ETF set
- **THEN** the system SHALL return a dict with top-level `is_etf: false`
- **AND** `latest.pe_ttm` SHALL come from Futu (unchanged from today)
- **AND** `latest.dividend_yield` SHALL be `null`
- **AND** `latest.dividend_rate` SHALL be `null`
- **AND** `latest.as_of` SHALL be `null`
- **AND** all other fields SHALL match today's Futu response byte-for-byte

#### Scenario: Symbol is in the ETF set but has no row in etf_fundamentals
- **WHEN** `get_etf_aware_daily_basic("NEWETF", 30)` is called
- **AND** `NEWETF` is in the cached ETF set
- **AND** `etf_fundamentals` has no row for `NEWETF`
- **THEN** the system SHALL return a dict with top-level `is_etf: true`
- **AND** `latest.pe_ttm` SHALL come from Futu (no override applied)
- **AND** `latest.dividend_yield` SHALL be `null`
- **AND** `latest.dividend_rate` SHALL be `null`

#### Scenario: Underlying Futu call errors out
- **WHEN** `FutuQuoteService.get_daily_basic` returns `{"symbol": "QQQ", "error": "<msg>"}`
- **THEN** the system SHALL return that error dict with top-level `is_etf: false` added
- **AND** no exception SHALL propagate

### Requirement: USStockService routes valuation through the ETF-aware wrapper
The system SHALL make `USStockService.get_daily_basic(symbol, days)` call `etf_valuation.get_etf_aware_daily_basic(symbol, days)` instead of `FutuQuoteService.get_daily_basic(symbol, days)` directly.

#### Scenario: Single-symbol US valuation endpoint picks up ETF merge
- **WHEN** a GET request is made to `/api/stock/QQQ/valuation?days=100`
- **THEN** the response SHALL be the dict returned by `etf_valuation.get_etf_aware_daily_basic("QQQ", 100)`
- **AND** the response SHALL include the ETF-aware fields (`is_etf`, `dividend_yield`, `dividend_rate`, `as_of`)

#### Scenario: Single-symbol A-share valuation endpoint is unaffected
- **WHEN** a GET request is made to `/api/stock/600938/valuation?days=100`
- **THEN** the response SHALL be returned by `AShareService.get_daily_basic` unchanged (no `is_etf` / dividend fields)

#### Scenario: Single-symbol HK valuation endpoint is unaffected
- **WHEN** a GET request is made to `/api/stock/00700/valuation?days=100`
- **THEN** the response SHALL be returned by `HKStockService.get_daily_basic` unchanged (no `is_etf` / dividend fields)

#### Scenario: Batch valuation endpoint is unaffected in this change
- **WHEN** a GET request is made to `/api/stock/batch/valuation?symbols=QQQ,AAPL`
- **THEN** the response SHALL use `FutuQuoteService.get_daily_basic_batch` directly
- **AND** the response for QQQ SHALL NOT include the new `is_etf` / dividend fields
- **NOTE** Mirroring the merge in the batch path is a follow-up; this scenario documents the deliberate non-goal.

### Requirement: Frontend renders ETF-specific valuation chips when is_etf is true
The frontend SHALL render two additional chips in the stock detail page header valuation row when the `/api/stock/{symbol}/valuation` response includes `is_etf: true`:
- a `股息率` chip displaying `valuation.dividend_yield * 100` formatted as a percentage with 2 decimal places
- a `年股息` chip displaying `valuation.dividend_rate` formatted as USD with 2 decimal places and a leading `$`

#### Scenario: ETF page with both dividend fields populated
- **WHEN** the user opens `/stock/QQQ`
- **AND** the valuation response contains `is_etf: true`, `dividend_yield: 0.002403585`, `dividend_rate: 1.77`
- **THEN** the header SHALL show `股息率 0.24%`
- **AND** the header SHALL show `年股息 $1.77`
- **AND** the PE chip SHALL show `33.30` (sourced from yahooquery)

#### Scenario: Non-ETF page does not show dividend chips
- **WHEN** the user opens `/stock/AAPL`
- **AND** the valuation response contains `is_etf: false`
- **THEN** the header SHALL NOT render the `股息率` or `年股息` chips
- **AND** the existing PE / PB / 换手 / 市值 chips SHALL be unchanged

#### Scenario: ETF page with null dividend fields
- **WHEN** the user opens `/stock/NEWETF`
- **AND** the valuation response contains `is_etf: true` but `dividend_yield: null`
- **THEN** the header SHALL still render the dividend chips
- **AND** the `股息率` chip SHALL show `N/A`
- **AND** the `年股息` chip SHALL show `N/A` (or be hidden if `dividend_rate` is also null)

