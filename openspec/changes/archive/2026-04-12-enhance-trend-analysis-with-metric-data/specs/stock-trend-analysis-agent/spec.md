## MODIFIED Requirements

### Requirement: Stock Trend Analysis Agent
The DeepAgent SHALL analyze stock price trends based on latest news AND technical indicators, predicting whether the stock will go up or down in the next 2 weeks.

#### Scenario: Analyze stock with technical data and Tavily search
- **WHEN** agent receives stock symbol and name
- **THEN** agent SHALL fetch 60 days of K-line data and compute technical indicators (MACD, RSI, MA)
- **AND** agent SHALL format recent 10-day price summary and indicator signals as text context
- **AND** agent SHALL search Tavily for recent news about the specific stock using `topic="finance"`
- **AND** agent SHALL search Tavily for macro environment factors (interest rates, GDP, industry trends)
- **AND** agent SHALL analyze sentiment from search results
- **AND** agent SHALL combine technical signals (40% weight) with news sentiment (60% weight) to form prediction
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

#### Scenario: Handle technical data fetch failure
- **WHEN** K-line data fetch fails
- **THEN** agent SHALL proceed with news-only analysis
- **AND** summary SHALL note "Technical data unavailable"

#### Scenario: Confidence scoring
- **WHEN** agent determines prediction
- **THEN** confidence SHALL be higher when:
  - Multiple relevant news sources found
  - News sentiment is consistent across sources
  - Technical signals confirm the direction indicated by news
  - Macro environment factors are clear and relevant
- **AND** confidence SHALL be lower when:
  - Few or no news results found
  - Sentiment is mixed or contradictory
  - Technical signals conflict with news direction
  - Macro environment is unclear or conflicting

#### Scenario: Technical signal interpretation
- **WHEN** agent analyzes technical data
- **THEN** agent SHALL consider:
  - Price trend direction over recent 10 days
  - Volume ratio (recent vs average) - above 1 indicates volume expansion
  - MACD golden/death cross signals
  - RSI zone (overbought >80, oversold <20, normal 20-80)
  - Price position relative to MA5 and MA20
