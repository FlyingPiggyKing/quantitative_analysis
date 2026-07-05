## ADDED Requirements

### Requirement: ETF-aware response shape
The system SHALL return additional optional fields on `/api/stock/{symbol}/valuation` when the requested symbol is recognised as a US ETF:
- top-level `is_etf: true`
- `latest.pe_ttm` overridden with the value from `etf_remote.db.etf_fundamentals.pe`
- `latest.pb` overridden with `etf_fundamentals.pb` when present
- `latest.dividend_yield` populated from `etf_fundamentals.dividend_yield`
- `latest.dividend_rate` populated from `etf_fundamentals.dividend_rate`
- `latest.as_of` populated from `etf_fundamentals.as_of` (yahooquery fetch timestamp)

#### Scenario: QQQ with full fundamentals row
- **WHEN** a GET request is made to `/api/stock/QQQ/valuation?days=100`
- **AND** `etf_fundamentals` has a row for QQQ with `{pe: 33.295002, pb: null, dividend_yield: 0.002403585, dividend_rate: 1.77, as_of: "2026-07-02T03:17:28Z"}`
- **THEN** the response JSON SHALL contain `is_etf: true` at the top level
- **AND** `latest.pe_ttm` SHALL equal `33.295002`
- **AND** `latest.dividend_yield` SHALL equal `0.002403585`
- **AND** `latest.dividend_rate` SHALL equal `1.77`
- **AND** `latest.as_of` SHALL equal `"2026-07-02T03:17:28Z"`
- **AND** `latest.total_mv` SHALL come from the Futu snapshot (not yahooquery)

#### Scenario: Non-ETF US stock response is byte-compatible with today
- **WHEN** a GET request is made to `/api/stock/AAPL/valuation?days=100`
- **AND** `AAPL` is not in `etf_fundamentals`
- **THEN** the response JSON SHALL contain `is_etf: false`
- **AND** `latest.dividend_yield` SHALL be `null`
- **AND** `latest.dividend_rate` SHALL be `null`
- **AND** `latest.as_of` SHALL be `null`
- **AND** all other fields SHALL be byte-identical to the pre-change Futu response

#### Scenario: A-share valuation response has no ETF fields
- **WHEN** a GET request is made to `/api/stock/600938/valuation?days=100`
- **THEN** the response JSON SHALL NOT contain `is_etf`, `dividend_yield`, `dividend_rate`, or `as_of`

#### Scenario: HK valuation response has no ETF fields
- **WHEN** a GET request is made to `/api/stock/00700/valuation?days=100`
- **THEN** the response JSON SHALL NOT contain `is_etf`, `dividend_yield`, `dividend_rate`, or `as_of`

### Requirement: ETF membership is determined dynamically
The system SHALL determine ETF membership from `etf_remote.db.etf_fundamentals` rather than from a hardcoded list. The symbol set SHALL be cached in memory and refreshable.

#### Scenario: New ETF becomes recognized after refresh
- **WHEN** a new ETF symbol `SCHD` is added to `etf_fundamentals` via the pusher
- **AND** `refresh_etf_symbols()` is invoked
- **THEN** subsequent calls to `is_etf("SCHD")` SHALL return `true`
- **AND** `/api/stock/SCHD/valuation` SHALL return `is_etf: true`

#### Scenario: Cache key is uppercased
- **WHEN** `is_etf("qqq")` is called and the cache contains `"QQQ"`
- **THEN** the system SHALL return `true`