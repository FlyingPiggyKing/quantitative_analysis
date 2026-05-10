## ADDED Requirements

### Requirement: Calculate Money Flow Score
The system SHALL calculate a money flow score (-100 to +100) based on main force net inflow data for use in multi-factor scoring.

#### Scenario: Score positive when net inflow
- **WHEN** stock's 5-day main force net inflow is positive
- **THEN** money_flow_score SHALL be positive (range 0 to +100)
- **AND** score SHALL reflect magnitude relative to stock's average daily volume

#### Scenario: Score negative when net outflow
- **WHEN** stock's 5-day main force net inflow is negative
- **THEN** money_flow_score SHALL be negative (range 0 to -100)
- **AND** score SHALL reflect magnitude relative to stock's average daily volume

#### Scenario: Score neutral when no data
- **WHEN** money flow data is unavailable or error
- **THEN** money_flow_score SHALL be 0
- **AND** no exception SHALL propagate to the caller

### Requirement: Integrate Money Flow Score into Composite Scoring
The multi-factor scoring system SHALL include money flow score at 10% weight.

#### Scenario: Composite score includes money flow
- **WHEN** `calculate_composite_score()` is called with all factor scores
- **THEN** the composite score SHALL include `money_flow` with weight 0.10 (10%)
- **AND** other weights SHALL proportionally sum to 0.90

#### Scenario: Money flow score component in breakdown
- **WHEN** composite score is returned
- **THEN** the breakdown SHALL include `money_flow` with fields: `score` (number), `signals` (list of strings), `source` (data source identifier)
