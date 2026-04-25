## ADDED Requirements

### Requirement: Fallback to most recent prediction

When a non-force GET request is made to `/api/trend-predictions/{symbol}` and no prediction exists for the current calendar day, the system SHALL return the most recent prediction from the database instead of returning HTTP 404.

#### Scenario: Today's prediction exists
- **WHEN** a GET request is made to `/api/trend-predictions/{symbol}` with `force=false`
- **AND** a prediction with `date(analyzed_at) = today` exists in the database with `confidence > 0`
- **THEN** the system SHALL return that prediction with `is_fallback: false`

#### Scenario: No prediction for today, but recent prediction exists
- **WHEN** a GET request is made to `/api/trend-predictions/{symbol}` with `force=false`
- **AND** no prediction exists for today
- **AND** at least one prediction exists in the database
- **THEN** the system SHALL return the most recent prediction by `analyzed_at` descending
- **AND** the response SHALL include `is_fallback: true`

#### Scenario: No prediction exists at all
- **WHEN** a GET request is made to `/api/trend-predictions/{symbol}` with `force=false`
- **AND** no predictions exist in the database for the given symbol
- **THEN** the system SHALL return HTTP 404

#### Scenario: Force analysis always runs fresh
- **WHEN** a GET request is made to `/api/trend-predictions/{symbol}` with `force=true`
- **AND** the user is authenticated and not rate-limited
- **THEN** the system SHALL run a fresh analysis
- **AND** the response SHALL include `is_fallback: false`
- **AND** the prediction SHALL be saved with today's date

### Requirement: Fallback signal in API response

The API response SHALL include an `is_fallback` boolean field indicating whether the returned prediction is from today or a previous day.

#### Scenario: Response includes is_fallback field
- **WHEN** a prediction is returned from `/api/trend-predictions/{symbol}`
- **THEN** the response SHALL include `is_fallback: false` if the prediction's `date(analyzed_at) = today`
- **AND** the response SHALL include `is_fallback: true` if the prediction's `date(analyzed_at) < today`

### Requirement: Fallback prediction selected by recency

When falling back, the system SHALL select the prediction with the most recent `analyzed_at` timestamp, regardless of how old it is.

#### Scenario: Multiple historical predictions exist
- **WHEN** falling back to most recent prediction for a symbol
- **AND** multiple predictions exist in the database
- **THEN** the system SHALL select the one with the highest `analyzed_at` value
