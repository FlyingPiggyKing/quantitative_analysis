## ADDED Requirements

### Requirement: Analysis Trigger Rate Limit
The system SHALL enforce a rate limit on the "立刻分析" (force analysis) trigger: one trigger per user per stock per hour.

#### Scenario: Allow trigger when no recent trigger exists
- **WHEN** user clicks "立刻分析" button for a stock
- **AND** no analysis has been triggered by this user for this stock in the past hour
- **THEN** system SHALL process the analysis request
- **AND** system SHALL record the trigger timestamp for this user and stock

#### Scenario: Reject trigger during cooldown period
- **WHEN** user clicks "立刻分析" button for a stock
- **AND** an analysis was triggered by this user for this stock within the past hour
- **THEN** system SHALL return HTTP 429 (Too Many Requests) status
- **AND** response SHALL include `retry_after` header with remaining seconds until cooldown expires

#### Scenario: Successful trigger records timestamp
- **WHEN** force analysis completes successfully
- **THEN** system SHALL store the trigger record with:
  - `user_id`: the authenticated user's ID
  - `symbol`: the stock symbol
  - `triggered_at`: current timestamp

#### Scenario: Multiple stocks have independent rate limits
- **WHEN** user triggers analysis for stock A
- **AND** user triggers analysis for stock B within the same hour
- **THEN** both requests SHALL succeed
- **AND** each stock SHALL have its own cooldown timer

### Requirement: Rate Limit API Response
The API SHALL return appropriate error response when rate limit is exceeded.

#### Scenario: Rate limit exceeded response
- **WHEN** a force analysis request is rejected due to rate limit
- **THEN** response status SHALL be 429
- **AND** response body SHALL include JSON with `error` field set to "Rate limit exceeded"
- **AND** response body SHALL include `retry_after` field with integer seconds remaining
- **AND** `retry_after` header SHALL be set with same integer seconds

### Requirement: Frontend Rate Limit Display
The frontend SHALL display cooldown state when button is disabled.

#### Scenario: Show remaining cooldown time on button
- **WHEN** user visits stock detail page
- **AND** cooldown is active for this user and stock
- **THEN** "立刻分析" button SHALL be disabled
- **AND** button text SHALL show remaining time (e.g., "剩余 23:45" or "剩余 45分钟")

#### Scenario: Button re-enables after cooldown expires
- **WHEN** cooldown period expires on frontend
- **THEN** button SHALL become enabled
- **AND** button text SHALL return to "立刻分析"

#### Scenario: Persist cooldown across page refresh
- **WHEN** user refreshes the page during active cooldown
- **THEN** cooldown SHALL still be displayed correctly
- **AND** remaining time SHALL be accurate based on stored end time

### Requirement: Cooldown Persistence
The frontend SHALL persist cooldown end time to survive page refresh.

#### Scenario: Store cooldown end time
- **WHEN** force analysis is triggered successfully
- **AND** user has no active cooldown for this stock
- **THEN** frontend SHALL store cooldown end time in localStorage
- **AND** key format SHALL be `analysis_cooldown_{user_id}_{symbol}`

#### Scenario: Read cooldown on page load
- **WHEN** stock detail page loads
- **THEN** frontend SHALL check localStorage for cooldown end time
- **AND** if cooldown is active, button SHALL remain disabled
- **AND** countdown SHALL display remaining time
