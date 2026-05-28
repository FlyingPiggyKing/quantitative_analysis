## ADDED Requirements

### Requirement: Hourly news display block
The system SHALL display a "小时资讯" block in the investment analysis module that shows news summaries from the past 3 hours.

### Requirement: Time-labeled news summaries
Each hourly news summary SHALL be displayed with a time label (e.g., "9:00", "10:00", "11:00") indicating the hour the news was collected.

### Requirement: New sub-module tab for news
The system SHALL add "盘面新闻" as a new sub-module tab in the analysis module, accessible alongside existing tabs (龙虎榜, 资金流向, 指数指标).

### Requirement: News summary content display
The hourly news summary SHALL display:
- Top 3 news points as a numbered or bulleted list
- Market impact as a one-line summary with direction indicator
- Sector impact as a list of sectors with brief explanations

### Requirement: API endpoint for news retrieval
The system SHALL provide a REST API endpoint `/api/hourly_news` that returns the last 3 hours of news summaries in JSON format.

#### Scenario: Display 3 hours of news
- **WHEN** user navigates to the "盘面新闻" sub-module tab
- **THEN** system fetches the last 3 hourly news summaries from the API
- **AND** displays each summary with its hour timestamp (e.g., "9:00")
- **AND** shows Top 3 news, market impact, and sector impact for each hour

#### Scenario: No news available
- **WHEN** user navigates to "盘面新闻" but no news summaries exist in the database
- **THEN** system displays a message "暂无小时资讯数据"
- **AND** does not crash or show error

#### Scenario: News API response format
- **WHEN** client calls GET /api/hourly_news
- **THEN** response SHALL be a JSON array of up to 3 objects
- **AND** each object SHALL contain: hour (string, e.g., "09:00"), top3_news (array of strings), market_impact ({direction: string, reason: string}), sector_impact (array of {sector: string, reason: string}), created_at (ISO timestamp)
