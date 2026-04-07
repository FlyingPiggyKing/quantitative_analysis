## ADDED Requirements

### Requirement: Stock Trend Analysis Agent
The DeepAgent SHALL analyze stock price trends based on latest news and macro environment, predicting whether the stock will go up or down in the next 2 weeks.

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
