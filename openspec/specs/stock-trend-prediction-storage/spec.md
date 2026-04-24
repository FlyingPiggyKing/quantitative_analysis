## ADDED Requirements

### Requirement: Trend Prediction Storage
The system SHALL store daily trend predictions in SQLite database for persistence and retrieval.

#### Scenario: Store prediction
- **WHEN** analysis completes for a stock
- **THEN** system SHALL store prediction with symbol, name, trend_direction, confidence, summary, and timestamp
- **AND** system SHALL enforce one prediction per symbol per day (upsert behavior)
- **AND** if a prediction with confidence > 0 already exists for today, a new analysis with confidence = 0 SHALL NOT overwrite it

#### Scenario: Get cached prediction for today
- **WHEN** `get_today_prediction(symbol)` is called
- **THEN** system SHALL return the prediction record where symbol matches AND date(analyzed_at) = today AND confidence > 0
- **AND** return None if no such record exists

#### Scenario: Return None when only failed analysis exists
- **WHEN** a stock has a prediction record from today but confidence = 0 (failed analysis)
- **THEN** `get_today_prediction(symbol)` SHALL return None
- **AND** the caller SHALL treat this as a cache miss

#### Scenario: Get latest prediction for symbol
- **WHEN** client requests prediction for a specific stock symbol
- **THEN** system SHALL return the most recent prediction for that symbol
- **AND** return 404 if no prediction exists

#### Scenario: List all latest predictions
- **WHEN** client requests all predictions
- **THEN** system SHALL return the latest prediction for each stock that has been analyzed
- **AND** results SHALL be ordered by analyzed_at descending

#### Scenario: Batch analyze watchlist
- **WHEN** batch analysis is triggered
- **THEN** system SHALL retrieve all stocks from watchlist
- **AND** run analysis for each stock
- **AND** store results in database
- **AND** return summary of analyzed count

### Requirement: Trend Prediction API
The backend SHALL provide REST API endpoints for trend prediction operations.

#### Scenario: GET /api/trend-predictions
- **WHEN** client sends GET request to /api/trend-predictions
- **THEN** response SHALL contain array of latest predictions for all analyzed stocks
- **AND** each prediction SHALL include symbol, name, trend_direction, confidence, summary, analyzed_at

#### Scenario: GET /api/trend-predictions/{symbol}
- **WHEN** client sends GET request to /api/trend-predictions/{symbol}
- **THEN** response SHALL contain the latest prediction for that symbol
- **AND** return 404 if no prediction exists

#### Scenario: POST /api/trend-predictions/batch
- **WHEN** client sends POST request to /api/trend-predictions/batch
- **THEN** system SHALL run trend analysis for all stocks in watchlist
- **AND** store each prediction in database
- **AND** return {"analyzed": N, "failed": M} count

#### Scenario: Database schema
- **WHEN** system initializes
- **THEN** database SHALL create predictions table if not exists with schema:
  - id (INTEGER PRIMARY KEY)
  - symbol (TEXT NOT NULL)
  - name (TEXT NOT NULL)
  - trend_direction (TEXT NOT NULL) -- 'up', 'down', 'neutral'
  - confidence (INTEGER NOT NULL) -- 0-100
  - summary (TEXT NOT NULL)
  - analyzed_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
