## Why

Users need to make informed decisions about stock prices based on real-time news and macro environment. Currently, the watch list only tracks stocks without providing price trend predictions. Adding AI-powered trend analysis based on latest news will help users understand potential price movements in the following 2 weeks.

## What Changes

1. **Stock Trend Analysis Agent**: Create a DeepAgent specialized for stock analysis that uses Tavily search to gather latest news and macro environment data
2. **Daily Analysis Job**: Run trend analysis for all stocks in the watch list once per day
3. **Trend Prediction Storage**: Store analysis summaries with trend direction (up/down), confidence percentage, and analysis date
4. **Watch List Display Enhancement**: Show trend indicator (up/down arrow) and confidence % on each stock in the watch list
5. **Detail Page Summary**: Display the latest trend analysis summary on the stock detail page

## Capabilities

### New Capabilities

- `stock-trend-analysis-agent`: DeepAgent that receives stock symbol/name, searches Tavily for latest news, analyzes macro environment, and predicts price trend (up/down) for next 2 weeks with confidence percentage
- `stock-trend-prediction-storage`: SQLite table and service to store daily trend predictions for each watched stock
- `stock-trend-display`: Frontend display of trend direction and confidence on watch list and detail pages

### Modified Capabilities

- (none)

## Impact

- **Backend**: New `backend/services/trend_analysis_agent.py` with DeepAgent, new `backend/services/trend_prediction_service.py` for storage, new `backend/api/trend_prediction.py` API routes
- **Frontend**: Modified watch list component to show trend indicators, modified stock detail page to show analysis summary
- **Dependencies**: `deepagents` package, `tavily` package, `TAVILY_API_KEY` environment variable
- **Database**: New `trend_predictions.db` SQLite database with `predictions` table
