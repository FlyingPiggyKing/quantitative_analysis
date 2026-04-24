## MODIFIED Requirements

### Requirement: Trend Prediction Storage
The system SHALL store daily trend predictions in SQLite database for persistence and retrieval.

#### Scenario: Store prediction (updated)
- **WHEN** analysis completes for a stock
- **THEN** system SHALL store prediction with symbol, name, trend_direction, confidence, summary, and timestamp
- **AND** system SHALL enforce one prediction per symbol per day (upsert behavior)
- **AND** if a prediction with confidence > 0 already exists for today, a new analysis with confidence = 0 SHALL NOT overwrite it

## ADDED Requirements

### Requirement: Get Today's Cached Prediction
The service SHALL provide a method to retrieve the cached prediction for a specific stock for today (if it exists with confidence > 0).

#### Scenario: Get cached prediction for today
- **WHEN** `get_today_prediction(symbol)` is called
- **THEN** system SHALL return the prediction record where symbol matches AND date(analyzed_at) = today AND confidence > 0
- **AND** return None if no such record exists

#### Scenario: Return None when only failed analysis exists
- **WHEN** a stock has a prediction record from today but confidence = 0 (failed analysis)
- **THEN** `get_today_prediction(symbol)` SHALL return None
- **AND** the caller SHALL treat this as a cache miss
