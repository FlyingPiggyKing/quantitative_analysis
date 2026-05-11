## ADDED Requirements

### Requirement: Fetch financial fundamentals from Tushare
The system SHALL fetch quarterly financial fundamentals for a given A-share symbol using Tushare Pro `fina_indicator` and `income` APIs, returning EPS, ROE, profit margins, growth rates, and revenue data.

#### Scenario: Successful fetch returns latest quarter data
- **WHEN** `AShareService.get_financial_fundamentals(symbol)` is called with a valid A-share symbol
- **THEN** the service SHALL fetch the latest record from `fina_indicator` table
- **AND** the service SHALL fetch the latest record from `income` table (gracefully handles rate limit errors)
- **AND** the result SHALL contain: `period`, `ann_date`, `report_label`, `eps`, `bps`, `roe`, `roe_yearly`, `gross_margin`, `netprofit_margin`, `basic_eps_yoy`, `netprofit_yoy`, `tr_yoy`, `debt_to_assets`, `current_ratio`, `total_revenue`, `n_income`
- **AND** the service SHALL return `{"symbol": <symbol>, "data": {...}}`

#### Scenario: gross_margin is a percentage, not an amount
- **WHEN** Tushare `fina_indicator.gross_margin` returns a value > 1000 (i.e., gross profit in 元, not a percentage)
- **THEN** the service SHALL compute the correct gross margin percentage as `(gross_margin / revenue) × 100`
- **AND** store the percentage value in `gross_margin`

#### Scenario: income API rate limited or fails
- **WHEN** Tushare `income` API raises an exception (e.g., rate limit)
- **THEN** the service SHALL gracefully catch the exception and continue using `fina_indicator` data
- **AND** `gross_margin` SHALL still be computed correctly using the heuristic above if `revenue` is available

#### Scenario: No data available
- **WHEN** Tushare returns empty DataFrames for both `fina_indicator` and `income`
- **THEN** the service SHALL return `{"symbol": <symbol>, "error": "No financial data", "data": null}`

### Requirement: Financial fundamentals REST endpoint
The system SHALL expose a GET endpoint at `/api/stock/{symbol}/fundamentals` that returns quarterly financial data for A-share stocks.

#### Scenario: Valid A-share request
- **WHEN** a GET request is made to `/api/stock/{symbol}/fundamentals` with a 6-digit A-share symbol
- **THEN** the endpoint SHALL call `AShareService.get_financial_fundamentals(symbol)`
- **AND** the response SHALL return that result as JSON

#### Scenario: Non A-share request
- **WHEN** a GET request is made to `/api/stock/{symbol}/fundamentals` with a HK or US stock symbol
- **THEN** the endpoint SHALL return `{"symbol": <symbol>, "error": "暂不适用", "data": null}`

### Requirement: Financial indicators display panel
The frontend SHALL display financial indicators in a dedicated panel block on the stock detail page, below the "AI趋势分析" section.

#### Scenario: Display panel for A-share stock
- **WHEN** `FinancialIndicatorsPanel` component receives valid financial data
- **THEN** it SHALL display a collapsible panel titled "财务指标"
- **AND** it SHALL show a 4-column grid layout with grouped indicators
- **AND** it SHALL display `report_label` (e.g., "2026年一季报") in the panel header
- **AND** it SHALL display `ann_date` (e.g., "2026-04-25发布") in the panel header

#### Scenario: Display panel for non A-share stock
- **WHEN** `FinancialIndicatorsPanel` component receives error with "暂不适用"
- **THEN** it SHALL display "暂不适用" message instead of data grid

#### Scenario: Null field values
- **WHEN** a financial indicator field is `null` or `None`
- **THEN** the panel SHALL display `--` instead of the null value

#### Scenario: Loading state
- **WHEN** the component is in loading state
- **THEN** it SHALL display a skeleton loader with 3 rows of pulsing bars
