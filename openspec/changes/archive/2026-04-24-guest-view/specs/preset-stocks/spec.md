## ADDED Requirements

### Requirement: Preset stock list
The system SHALL display a predefined list of 5 stocks for unauthenticated users.

#### Scenario: Load preset stocks for guest users
- **WHEN** an unauthenticated user visits the home page
- **THEN** system SHALL display these 5 preset stocks:
  - 601318 (Ping An Insurance)
  - 300750 (CATL)
  - 688981 (SMIC)
  - 601899 (Zijin Mining)
  - 600938 (China Oilfield Services)

#### Scenario: Preset stocks are read-only
- **WHEN** unauthenticated user views preset stock list
- **THEN** no "add to watchlist" button SHALL be visible
- **AND** no "remove" option SHALL be available

### Requirement: Stock symbol format
All preset stocks SHALL use standard 6-digit Chinese stock codes.

#### Scenario: Stock symbol format
- **WHEN** preset stocks are displayed
- **THEN** each stock SHALL be shown with its 6-digit symbol
- **AND** system SHALL automatically append exchange suffix (.SH or .SZ) based on prefix rules
