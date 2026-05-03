## ADDED Requirements

### Requirement: Independent A-share stock data display
The system SHALL display A-share stock data as soon as it is available, without waiting for US stock data to load.

#### Scenario: A-share data arrives before US data
- **WHEN** user loads the preset stock page
- **AND** A-share stock info and valuation data arrives
- **AND** US stock data is still loading
- **THEN** system displays A-share stock data immediately
- **AND** US stock data shows loading indicator

#### Scenario: A-share data arrives after US data
- **WHEN** user loads the preset stock page
- **AND** US stock data arrives first
- **AND** A-share stock data arrives later
- **THEN** system displays US stock data first
- **AND** system displays A-share stock data when it arrives

### Requirement: Independent US stock data display
The system SHALL display US stock data as soon as it is available, without waiting for A-share stock data to load.

#### Scenario: US data arrives before A-share data
- **WHEN** user loads the preset stock page
- **AND** US stock info and valuation data arrives
- **AND** A-share stock data is still loading
- **THEN** system displays US stock data immediately
- **AND** A-share stock data shows loading indicator

#### Scenario: US data arrives after A-share data
- **WHEN** user loads the preset stock page
- **AND** A-share stock data arrives first
- **AND** US stock data arrives later
- **THEN** system displays A-share data first
- **AND** system displays US stock data when it arrives

### Requirement: A-share display unaffected by US stock failure
The system SHALL continue to display A-share stock data even if US stock queries fail completely.

#### Scenario: US stock query fails
- **WHEN** user loads the preset stock page
- **AND** A-share stock data is available
- **AND** US stock query fails with an error
- **THEN** system displays A-share stock data
- **AND** system shows error or empty state only for US stock tab

### Requirement: US stock display unaffected by A-share stock failure
The system SHALL continue to display US stock data even if A-share stock queries fail completely.

#### Scenario: A-share stock query fails
- **WHEN** user loads the preset stock page
- **AND** US stock data is available
- **AND** A-share stock query fails with an error
- **THEN** system displays US stock data
- **AND** system shows error or empty state only for A-share tab

### Requirement: Trend predictions are non-blocking
The system SHALL treat trend prediction data as non-critical and SHALL NOT block stock data display while fetching predictions.

#### Scenario: Predictions endpoint is slow
- **WHEN** user loads the preset stock page
- **AND** stock info and valuation data arrives within 2 seconds
- **AND** trend predictions take longer than 5 seconds to load
- **THEN** system displays stock data within 2 seconds
- **AND** trend predictions show as loading or unavailable

#### Scenario: Predictions endpoint fails
- **WHEN** user loads the preset stock page
- **AND** stock info and valuation data is available
- **AND** trend predictions endpoint returns an error
- **THEN** system displays stock data immediately
- **AND** trend prediction column shows "-"
