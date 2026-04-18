## MODIFIED Requirements

### Requirement: Trend Prediction Storage

The system SHALL store daily trend predictions in SQLite database for persistence and retrieval, including extended analysis data when available.

#### Scenario: Store prediction with extended analysis
- **WHEN** analysis completes for a stock and returns extended analysis (情绪分析, 技术分析, 趋势判断)
- **THEN** system SHALL store prediction with symbol, name, trend_direction, confidence, summary, analyzed_at, and extended_analysis
- **AND** system SHALL serialize extended_analysis as JSON in the database

#### Scenario: Store prediction without extended analysis
- **WHEN** analysis completes but returns no extended analysis fields
- **THEN** system SHALL store prediction with only the basic fields
- **AND** extended_analysis column SHALL be NULL

#### Scenario: Retrieve prediction with extended analysis
- **WHEN** client requests prediction for a specific stock symbol
- **THEN** system SHALL return the most recent prediction including extended_analysis if available
- **AND** return 404 if no prediction exists

#### Scenario: Background async analysis stores extended data
- **WHEN** batch-async endpoint submits analysis task to background queue
- **THEN** background worker SHALL pass extended_analysis to save_prediction when analysis completes
- **AND** stored prediction SHALL include all extended analysis fields when available

### Requirement: Trend Prediction API

The backend SHALL provide REST API endpoints for trend prediction operations.

#### Scenario: GET /api/trend-predictions/{symbol} returns extended analysis
- **WHEN** client sends GET request to /api/trend-predictions/{symbol}
- **THEN** response SHALL contain the latest prediction including 情绪分析, 技术分析, 趋势判断 when available
- **AND** return 404 if no prediction exists
