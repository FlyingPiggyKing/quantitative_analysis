## MODIFIED Requirements

### Requirement: Stock Trend Analysis Agent
The DeepAgent SHALL analyze stock price trends based on latest news, macro environment, technical indicators, and valuation metrics, predicting whether the stock will go up or down in the next 2 weeks.

#### Scenario: Analyze stock with Tavily search
- **WHEN** agent receives stock symbol and name
- **THEN** agent SHALL search Tavily for recent news about the specific stock using `topic="finance"`
- **AND** agent SHALL search Tavily for macro environment factors (interest rates, GDP, industry trends)
- **AND** agent SHALL analyze sentiment from search results
- **AND** agent SHALL return prediction with trend direction, confidence percentage, and summary

#### Scenario: Return prediction structure
- **WHEN** agent completes analysis
- **THEN** response SHALL include:
  - `symbol`: stock symbol
  - `name`: stock name
  - `trend_direction`: "up", "down", or "neutral"
  - `confidence`: integer 0-100
  - `summary`: text summary of analysis reasoning

#### Scenario: Handle insufficient news
- **WHEN** Tavily returns no results for a stock
- **THEN** agent SHALL return "neutral" trend with 0% confidence
- **AND** summary SHALL state "Insufficient recent news data for analysis"

#### Scenario: Confidence scoring
- **WHEN** agent determines prediction
- **THEN** confidence SHALL be higher when:
  - Multiple relevant news sources found
  - News sentiment is consistent across sources
  - Macro environment factors are clear and relevant
- **AND** confidence SHALL be lower when:
  - Few or no news results found
  - Sentiment is mixed or contradictory
  - Macro environment is unclear or conflicting

#### Scenario: Valuation context included in agent reasoning
- **WHEN** `format_data_context()` assembles the LLM prompt context
- **THEN** it SHALL include the latest valuation metrics if available: PE(TTM), PB, turnover rate (换手率), and total market cap
- **AND** these SHALL appear alongside existing technical indicators in the context block

#### Scenario: Graceful handling of missing valuation data
- **WHEN** the valuation data dict contains an `error` key or is absent
- **THEN** `format_data_context()` SHALL omit the valuation section entirely
- **AND** the agent SHALL proceed with analysis using only available technical indicators

## ADDED Requirements

### Requirement: Frontend valuation panel on stock analysis page
The frontend stock analysis/detail page SHALL display a valuation section showing PE(TTM), PB ratio, turnover rate, and total market cap, with a mini PE(TTM) sparkline showing recent history.

#### Scenario: Valuation data available
- **WHEN** the valuation API returns valid data for a stock
- **THEN** the page SHALL display: PE(TTM) value with mini sparkline, PB ratio, turnover rate (%), and total market cap (万元)

#### Scenario: Valuation data unavailable
- **WHEN** the valuation API returns an error or no data
- **THEN** each metric field SHALL display "N/A"
- **AND** the sparkline SHALL be hidden or show an empty state
