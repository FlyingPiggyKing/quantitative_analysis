## ADDED Requirements

### Requirement: Valuation metrics API endpoint
The system SHALL provide a backend API endpoint to fetch PE, PB, and turnover rate data for stocks via Tushare Pro API.

#### Scenario: Fetch current valuation metrics
- **WHEN** client requests `GET /api/stock/{symbol}/valuation`
- **THEN** system returns JSON with `symbol`, `current` object containing `pe`, `pb`, `turnover_rate`
- **AND** `current.pe` and `current.pb` SHALL be numbers or null if unavailable
- **AND** `current.turnover_rate` SHALL be a number representing percentage

#### Scenario: Fetch historical valuation data
- **WHEN** client requests `GET /api/stock/{symbol}/valuation`
- **THEN** system returns `history` array with daily PE and PB values
- **AND** each history entry SHALL contain `date`, `pe`, `pb`
- **AND** history SHALL contain up to 100 days of data by default

#### Scenario: Handle missing valuation data
- **WHEN** stock has no PE/PB data (e.g., new listing)
- **THEN** system SHALL return `null` for pe and pb fields
- **AND** system SHALL NOT return an error for missing data

#### Scenario: Handle invalid stock symbol
- **WHEN** client requests valuation for non-existent stock
- **THEN** system SHALL return `{"symbol": "...", "error": "Stock not found"}`

### Requirement: Valuation metrics display on watch list
The frontend SHALL display current PE and PB values for each stock in the watch list table.

#### Scenario: Display PE and PB columns
- **WHEN** watch list is rendered with stock data
- **THEN** table SHALL include columns for "市盈率(PE)" and "市净率(PB)"
- **AND** each row SHALL display the latest available PE and PB values

#### Scenario: Display placeholder for missing values
- **WHEN** PE or PB value is null for a stock
- **THEN** system SHALL display "-" instead of the number
- **AND** system SHALL NOT display an error state

### Requirement: Valuation metrics display on stock detail page
The frontend SHALL display current PE, PB, and turnover rate in the stock detail page header area.

#### Scenario: Display metrics in detail header
- **WHEN** stock detail page is loaded
- **THEN** header area SHALL display PE, PB, and turnover rate values
- **AND** values SHALL be labeled clearly (市盈率, 市净率, 换手率)

### Requirement: PE/PB daily chart
The frontend SHALL display daily PE and PB as line charts below the volume histogram on the stock detail page.

#### Scenario: Render PE line chart
- **WHEN** stock detail page loads with valuation data
- **THEN** system SHALL display PE as a line chart below volume
- **AND** chart SHALL span the same date range as K-line data

#### Scenario: Render PB line chart
- **WHEN** stock detail page loads with valuation data
- **THEN** system SHALL display PB as a line chart below volume
- **AND** PB chart SHALL share the same time axis as PE chart

#### Scenario: Chart handles missing data points
- **WHEN** some historical days have null PE or PB
- **THEN** chart SHALL connect available data points with lines
- **AND** gaps SHALL be handled gracefully without breaking the chart
