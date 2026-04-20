## ADDED Requirements

### Requirement: Today date utility function
The system SHALL provide a `get_today_date()` utility function that returns the current date as a string in "YYYY-MM-DD" format.

#### Scenario: Get today's date
- **WHEN** `get_today_date()` is called
- **THEN** it SHALL return a string in format "YYYY-MM-DD" representing the current date

### Requirement: System prompt includes today's date
The stock trend analysis agent's system prompt SHALL include today's date for temporal context.

#### Scenario: Agent creation with today's date
- **WHEN** `create_stock_trend_agent()` is called
- **THEN** the agent SHALL be created with a system prompt that includes today's date in the format "Today is YYYY-MM-DD"

#### Scenario: Date used in news search context
- **WHEN** the agent processes a stock analysis request
- **THEN** the system prompt SHALL indicate today's date so the agent can properly evaluate news freshness and temporal relevance
