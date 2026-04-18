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
