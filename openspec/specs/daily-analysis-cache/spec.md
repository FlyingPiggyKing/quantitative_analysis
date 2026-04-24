## ADDED Requirements

### Requirement: Daily Analysis Cache
The system SHALL cache successful trend predictions (confidence > 0) per stock per day. When an analysis request arrives for a stock that already has a valid cached result for today, the system SHALL return the cached result directly without invoking the LLM.

#### Scenario: Return cached result when available
- **WHEN** an analysis request is made for a stock that has a prediction from today with confidence > 0
- **THEN** the system SHALL return the cached prediction without calling analyze_stock_trend
- **AND** the response SHALL include the cached data with its original analyzed_at timestamp

#### Scenario: Bypass cache with force flag
- **WHEN** an analysis request is made with force=true for a stock that has a valid cached result today
- **THEN** the system SHALL invoke analyze_stock_trend to perform fresh analysis
- **AND** the new result SHALL replace the cached result in the database

#### Scenario: Analyze when no cache exists
- **WHEN** an analysis request is made for a stock with no prediction from today
- **THEN** the system SHALL invoke analyze_stock_trend normally
- **AND** the result SHALL be saved to the database

#### Scenario: Cache miss on failed analysis
- **WHEN** an analysis request is made and the LLM returns confidence = 0 (failure)
- **THEN** no cache entry SHALL be created or updated
- **AND** a subsequent request without force SHALL still skip analysis and return the existing valid cache if one exists

### Requirement: Batch Analysis Respects Cache
The system SHALL skip analysis for stocks in the watchlist that already have a valid cached result for today (when force is not set).

#### Scenario: Batch analyze skips cached stocks by default
- **WHEN** batch analysis is triggered with force=false (default)
- **THEN** for each stock in the watchlist, the system SHALL check if a cached result exists for today
- **AND** stocks with valid cache SHALL be skipped without invoking analyze_stock_trend
- **AND** stocks without cache SHALL be analyzed normally

#### Scenario: Batch analyze with force=true processes all stocks
- **WHEN** batch analysis is triggered with force=true
- **THEN** the system SHALL analyze ALL stocks regardless of existing cache
- **AND** each stock SHALL be processed through analyze_stock_trend
