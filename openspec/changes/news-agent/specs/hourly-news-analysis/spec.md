## ADDED Requirements

### Requirement: Hourly news collection
The system SHALL collect news from Tushare API at the end of each hour during trading hours using the `tushare_news` interface.

### Requirement: News analysis with structured output
The system SHALL use a news analysis agent to analyze collected news and produce a structured summary containing:
- Top 3 news points (most impactful to market funds or index)
- Market impact (资金流入/流出 prediction with reason)
- Sector impact (affected一级行业 sectors with brief explanation)

### Requirement: Separate background thread execution
The news analysis SHALL run in a dedicated background thread pool (max_workers=1) that does not affect user-initiated analysis or website interactions.

### Requirement: News summary storage
The system SHALL store each hourly news summary in the `hourly_news` table with fields: id, hour_timestamp, summary_json, created_at.

### Requirement: Scheduled hourly execution
The system SHALL execute news collection and analysis automatically every hour using a scheduler, independent of user requests.

#### Scenario: Successful hourly news collection
- **WHEN** the scheduler triggers at the end of hour X
- **THEN** system fetches news from Tushare for the past 60 minutes
- **AND** system invokes the news analysis agent with the news list
- **AND** system stores the resulting summary in the database

#### Scenario: LLM API failure with retry
- **WHEN** the news analysis agent fails due to LLM error
- **AND** retry count is less than 3
- **THEN** system retries the analysis after a 5-second delay
- **AND** retry count increments by 1
- **IF** all retries fail
- **THEN** system stores an error summary with error message

#### Scenario: Database storage
- **WHEN** news analysis completes successfully
- **THEN** system stores a JSON object containing: hour_timestamp, top3_news (array), market_impact (object with direction and reason), sector_impact (array of {sector, reason} objects), created_at

#### Scenario: Cleanup old news
- **WHEN** the system starts up
- **THEN** system deletes all hourly_news records older than 7 days
