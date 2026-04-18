## MODIFIED Requirements

### Requirement: Stock Trend Analysis Agent
The DeepAgent SHALL analyze stock price trends based on latest news, macro environment, technical indicators, and valuation metrics, predicting whether the stock will go up or down in the next 2 weeks. The agent SHALL return a structured JSON output with three sections: sentiment analysis (情绪分析), technical analysis (技术分析), and trend judgment (趋势判断), while maintaining the existing prediction fields.

#### Scenario: Return structured prediction with three analysis sections
- **WHEN** agent completes analysis
- **THEN** response SHALL include:
  - `symbol`: stock symbol
  - `name`: stock name
  - `trend_direction`: "up", "down", or "neutral"
  - `confidence`: integer 0-100
  - `情绪分析`: object containing news array and summary
  - `技术分析`: object containing technical indicators analysis
  - `趋势判断`: object containing forecast and operation suggestions

#### Scenario: Sentiment analysis contains recent market news
- **WHEN** agent searches for stock news via Tavily
- **THEN** `情绪分析.news` SHALL contain up to 5 recent news items from the past 5 days
- **AND** each news item SHALL include: title, source, date, and summary
- **AND** `情绪分析.summary` SHALL provide an overall sentiment summary in 2-3 sentences

#### Scenario: Technical analysis contains data indicator analysis
- **WHEN** agent analyzes technical indicators
- **THEN** `技术分析` SHALL include analysis of: MACD signals, RSI zone, MA position, volume trends, and valuation metrics (PE, PB, turnover rate)
- **AND** each indicator SHALL include current value and interpretation (e.g., "金叉(看多)", "超买区")

#### Scenario: Trend judgment contains forecast and operation suggestions
- **WHEN** agent forms final prediction
- **THEN** `趋势判断` SHALL include:
  - `forecast`: string describing expected trend for the next week
  - `suggestion`: one of "加仓", "减仓", "持有", "建仓", "观望"
  - `reasoning`: explanation of why this suggestion is given
- **AND** `趋势判断.suggestion` SHALL be consistent with `trend_direction`

#### Scenario: Handle insufficient news gracefully
- **WHEN** Tavily returns fewer than 5 results for a stock
- **THEN** `情绪分析.news` SHALL contain all available news items
- **AND** `情绪分析.summary` SHALL note "新闻数据有限" if less than 3 news items

#### Scenario: Handle parsing failures with fallback
- **WHEN** the structured JSON parsing fails on agent response
- **THEN** system SHALL attempt to extract the original fields (trend_direction, confidence, summary)
- **AND** if original fields are found, SHALL return them with null/empty extended fields
- **AND** logging SHALL record the parsing failure for monitoring
