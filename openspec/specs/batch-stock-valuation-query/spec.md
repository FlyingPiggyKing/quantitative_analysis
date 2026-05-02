## ADDED Requirements

### Requirement: Batch valuation query endpoint
The system SHALL expose a GET endpoint at `/api/stock/batch/valuation` that accepts multiple stock symbols and returns valuation metrics for all symbols in a single response.

#### Scenario: Valid batch request with multiple symbols
- **WHEN** a GET request is made to `/api/stock/batch/valuation?symbols=600938,601899,300750`
- **THEN** the response SHALL return a JSON object with `results` array containing valuation data for each symbol
- **AND** each result SHALL include `symbol`, `data` (list of daily records), and `latest` (most recent record)
- **AND** each record SHALL include `trade_date`, `pe_ttm`, `pb`, `turnover_rate`, `total_mv`, `circ_mv`

#### Scenario: Single symbol in batch request
- **WHEN** a GET request is made to `/api/stock/batch/valuation?symbols=600938`
- **THEN** the response SHALL have the same format as single-symbol `/api/stock/{symbol}/valuation`
- **AND** backward compatibility SHALL be maintained

#### Scenario: Partial failure - some symbols invalid
- **WHEN** a GET request is made with mixed valid and invalid symbols
- **THEN** the response SHALL include `results` with data for valid symbols
- **AND** the response SHALL include `errors` array with error info for invalid symbols
- **AND** valid symbols SHALL still return complete data

#### Scenario: All symbols invalid
- **WHEN** a GET request is made with only invalid symbols
- **THEN** the response SHALL return `results: []` and `errors` array with all failures
- **AND** no HTTP error SHALL be returned (200 OK with error details in body)

### Requirement: Batch info query endpoint
The system SHALL expose a GET endpoint at `/api/stock/batch/info` that accepts multiple stock symbols and returns basic stock information for all symbols in a single response.

#### Scenario: Valid batch info request
- **WHEN** a GET request is made to `/api/stock/batch/info?symbols=600938,601899`
- **THEN** the response SHALL return a JSON object with `results` array containing info for each symbol
- **AND** each result SHALL include `symbol`, `name`, and basic stock details

### Requirement: AkshareService batch support
The `AkshareService` SHALL support batch fetching of `daily_basic` data when given a list of symbols, making a single Tushare API call per batch instead of one call per symbol.

#### Scenario: Batch symbols to Tushare API
- **WHEN** `get_daily_basic_batch(symbols: List[str], days: int)` is called with multiple symbols
- **THEN** the service SHALL make a single Tushare `daily_basic` API call with comma-separated ts_codes
- **AND** the response SHALL be parsed and grouped by symbol
- **AND** return format SHALL match single-symbol response structure per symbol

### Requirement: Batch valuation handles mixed market symbols
The system SHALL handle batch valuation requests containing both A-share and US stock symbols.

#### Scenario: Mixed market batch request
- **WHEN** GET request to `/api/stock/batch/valuation?symbols=600938,GOOGL,TSLA`
- **THEN** the response SHALL include valuation data for both A-share and US stocks
- **AND** A-share stocks use Tushare `daily_basic` endpoint
- **AND** US stocks use Tushare `us_daily` endpoint (or return null for unavailable fields)
- **AND** results array contains data for all valid symbols

### Requirement: Batch info handles mixed market symbols
The system SHALL handle batch info requests containing both A-share and US stock symbols.

#### Scenario: Mixed market batch info request
- **WHEN** GET request to `/api/stock/batch/info?symbols=600938,GOOGL`
- **THEN** the response SHALL include info for both A-share and US stocks
- **AND** each result SHALL include `market` field indicating "A" or "US"
