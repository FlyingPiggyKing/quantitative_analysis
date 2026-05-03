## ADDED Requirements

### Requirement: Independent A-share valuation data loading
The system SHALL fetch A-share valuation data independently without waiting for US stock data to load.

#### Scenario: A-share valuation loads before US valuation
- **WHEN** user views WatchList with A-share and US stocks
- **AND** A-share stocks are already in the watchlist
- **AND** A-share valuation data arrives
- **AND** US stock data is still loading or fails
- **THEN** system displays A-share valuation data immediately
- **AND** US stock section shows loading indicator or error state independently

### Requirement: Independent US stock valuation data loading
The system SHALL fetch US stock valuation data independently without waiting for A-share data to load.

#### Scenario: US valuation loads before A-share valuation
- **WHEN** user views WatchList with A-share and US stocks
- **AND** US stocks are already in the watchlist
- **AND** US stock valuation data arrives
- **AND** A-share stock data is still loading or fails
- **THEN** system displays US stock valuation data immediately
- **AND** A-share section shows loading indicator or error state independently

### Requirement: A-share valuation unaffected by US stock failure
The system SHALL continue to display A-share valuation data even if US stock data queries fail completely.

#### Scenario: US stock valuation query fails
- **WHEN** user views WatchList
- **AND** A-share valuation data is available
- **AND** US stock valuation query fails with an error
- **THEN** system displays A-share valuation data
- **AND** system shows error or empty state only for US stock tab

### Requirement: US stock valuation unaffected by A-share failure
The system SHALL continue to display US stock valuation data even if A-share stock data queries fail completely.

#### Scenario: A-share valuation query fails
- **WHEN** user views WatchList
- **AND** US stock valuation data is available
- **AND** A-share valuation query fails with an error
- **THEN** system displays US stock valuation data
- **AND** system shows error or empty state only for A-share tab

### Requirement: Independent trend prediction fetching
The system SHALL fetch trend predictions independently per market without blocking display.

#### Scenario: Predictions endpoint is slow or fails for one market
- **WHEN** user views WatchList
- **AND** A-share predictions are available but US predictions are slow or failing
- **THEN** system displays A-share predictions immediately
- **AND** US predictions show as loading or "-" placeholder
