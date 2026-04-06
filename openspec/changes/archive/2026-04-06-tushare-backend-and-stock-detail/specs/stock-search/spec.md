## ADDED Requirements

### Requirement: Stock search interface
The frontend SHALL provide a web interface for entering stock codes.

#### Scenario: Display search page
- **WHEN** user visits the home page
- **THEN** system SHALL display an input field for stock code entry
- **AND** system SHALL show example stock codes (000001, 600000, 300059)

#### Scenario: Navigate to stock detail
- **WHEN** user enters a valid stock code and submits
- **THEN** system SHALL navigate to `/stock/{symbol}` page
- **AND** display the stock's K-line chart and indicators

#### Scenario: Handle invalid stock code
- **WHEN** user enters an invalid stock code
- **THEN** system SHALL display error message
- **AND** offer option to return to search page

### Requirement: Stock detail page
The frontend SHALL display comprehensive stock information on the detail page.

#### Scenario: Display stock header
- **WHEN** stock detail page loads
- **THEN** header SHALL show stock name, symbol, latest price
- **AND** display price change percentage with color coding

#### Scenario: Display recent quotes table
- **WHEN** stock detail page loads
- **THEN** system SHALL display a table with recent 10 trading days
- **AND** table SHALL include: date, open, close, high, low, volume, change_pct
