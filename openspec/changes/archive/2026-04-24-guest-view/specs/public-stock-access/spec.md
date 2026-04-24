## ADDED Requirements

### Requirement: Public stock list access
The system SHALL allow unauthenticated users to view the home page stock list.

#### Scenario: Guest user visits home page
- **WHEN** an unauthenticated user visits the home page
- **THEN** system SHALL display the preset stock list
- **AND** no login prompt SHALL be shown

#### Scenario: Guest user views stock list
- **WHEN** unauthenticated user views the stock list
- **THEN** system SHALL show stock symbol, name, and basic metrics
- **AND** user SHALL be able to click to view stock details

### Requirement: Public stock search
The system SHALL allow unauthenticated users to search for stocks by symbol.

#### Scenario: Guest user searches for stock
- **WHEN** unauthenticated user enters a valid stock code in search
- **THEN** system SHALL return matching stock information
- **AND** system SHALL navigate to stock detail page

#### Scenario: Guest user searches for invalid stock
- **WHEN** unauthenticated user enters an invalid stock code
- **THEN** system SHALL display "Stock not found" message
- **AND** user SHALL remain on search page

### Requirement: Public stock detail access
The system SHALL allow unauthenticated users to view stock detail pages.

#### Scenario: Guest user views stock details
- **WHEN** unauthenticated user navigates to `/stock/{symbol}`
- **THEN** system SHALL display stock quote, K-line chart, and indicators
- **AND** system SHALL display trend analysis section with existing data (if available)

#### Scenario: Guest user attempts trend analysis
- **WHEN** unauthenticated user clicks "立刻分析" button on stock detail page
- **THEN** system SHALL display login/register prompt
- **AND** analysis SHALL NOT be triggered
- **AND** user SHALL remain on the same page
