## MODIFIED Requirements

### Requirement: Stock Trend Analysis Agent
The DeepAgent SHALL analyze stock price trends based on latest news, macro environment, technical indicators, and valuation metrics, predicting whether the stock will go up or down in the next 2 weeks.

#### Scenario: Analyze stock with fallback search
- **WHEN** agent receives stock symbol and name
- **THEN** agent SHALL attempt to search Tavily for recent news about the specific stock using `topic="finance"`
- **AND** if Tavily returns an error or empty results, agent SHALL fall back to MiniMax MCP search
- **AND** agent SHALL analyze sentiment from search results
- **AND** agent SHALL return prediction with trend direction, confidence percentage, and summary

#### Scenario: Secondary search when Tavily unavailable
- **WHEN** Tavily search returns an error message (e.g., "TAVILY_API_KEY not configured", rate limit)
- **THEN** agent SHALL automatically invoke MiniMax MCP search as secondary source
- **AND** agent SHALL continue analysis using MiniMax MCP results

#### Scenario: Return prediction structure
- **WHEN** agent completes analysis
- **THEN** response SHALL include:
  - `symbol`: stock symbol
  - `name`: stock name
  - `trend_direction`: "up", "down", or "neutral"
  - `confidence`: integer 0-100
  - `summary`: text summary of analysis reasoning

#### Scenario: Handle insufficient news from both sources
- **WHEN** both Tavily and MiniMax MCP return no results or errors
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

#### Scenario: A-stock finance metrics context included in agent reasoning
- **WHEN** `format_data_context()` assembles the LLM prompt context for an A-share stock
- **THEN** it SHALL include the latest financial fundamentals if available: report label, announcement date, EPS, BPS, ROE, gross margin, net profit margin, EPS YoY, net profit YoY, revenue YoY, debt-to-assets ratio, current ratio, total revenue, net income
- **AND** these SHALL appear alongside existing technical indicators in the context block

#### Scenario: Graceful handling of missing finance metrics for A-stock
- **WHEN** the financial fundamentals data dict contains an `error` key or is absent
- **THEN** `format_data_context()` SHALL omit the finance metrics section entirely
- **AND** the agent SHALL proceed with analysis using only available technical indicators

#### Scenario: Finance metrics output in technical analysis
- **WHEN** agent outputs technical analysis for an A-share stock with available financial fundamentals
- **THEN** the `技术分析` block SHALL include a `财务指标` sub-block
- **AND** the sub-block SHALL contain: a summary of key financial metrics (report period, EPS, ROE, margins, growth rates) and their interpretation
- **AND** the structure SHALL match the prompt example format

#### Scenario: Non-A-share stocks do not include finance metrics
- **WHEN** agent outputs technical analysis for HK or US stocks
- **THEN** the `技术分析` block SHALL NOT include a `财务指标` sub-block
- **AND** the output SHALL match the existing format for non-A-share stocks

#### Scenario: System prompt is separated by market
- **WHEN** `get_system_prompt()` is called
- **THEN** it SHALL return an A-share-specific prompt with `finance_metrics` example when `market == "A"`
- **AND** it SHALL return a HK/US-specific prompt WITHOUT `finance_metrics` example when `market == "HK"` or `market == "US"`
- **AND** both prompts SHALL use Chinese language for all content

### Requirement: Frontend valuation panel on stock analysis page
The frontend stock analysis/detail page SHALL display a valuation section showing PE(TTM), PB ratio, turnover rate, and total market cap, with a mini PE(TTM) sparkline showing recent history.

#### Scenario: Valuation data available
- **WHEN** the valuation API returns valid data for a stock
- **THEN** the page SHALL display: PE(TTM) value with mini sparkline, PB ratio, turnover rate (%), and total market cap (万元)

#### Scenario: Valuation data unavailable
- **WHEN** the valuation API returns an error or no data
- **THEN** each metric field SHALL display "N/A"
- **AND** the sparkline SHALL be hidden or show an empty state

### Requirement: Frontend technical analysis includes finance metrics for A-stocks
The frontend SHALL display financial metrics summary within the technical analysis section for A-share stocks.

#### Scenario: Display finance metrics in technical analysis for A-share
- **WHEN** `TechnicalAnalysis` component receives valid financial metrics data
- **THEN** it SHALL display a `财务指标` block within the technical analysis section
- **AND** the block SHALL show key financial indicators with their interpretations

#### Scenario: Finance metrics block renders after money_flow block
- **WHEN** `TrendAnalysisPanel.tsx` `TechnicalSection` renders
- **THEN** the `finance_metrics` block SHALL be rendered after the `money_flow` block if present
- **AND** it SHALL use optional chaining (`data.finance_metrics &&`) to ensure HK/US stocks render nothing

#### Scenario: Finance metrics field is optional in TypeScript interface
- **WHEN** TypeScript `TechnicalAnalysis` interface is defined
- **THEN** the `finance_metrics` field SHALL be optional (`finance_metrics?:`)
- **AND** this ensures compatibility with HK/US stocks that do not include this field
