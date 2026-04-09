## Why

Current stock news search with Tavily has no time range restriction, potentially returning outdated news. For effective short-term trend analysis (2-week prediction), we need to focus on the most recent news from the current week to ensure the analysis reflects the latest market sentiment and developments.

## What Changes

1. **Reduce Tavily search time range**: Limit Tavily news search to the current week only, ensuring only the latest news is retrieved
2. **Optimize max_results**: Ensure we search for exactly 5 latest news items per stock
3. **Update DeepAgent system prompt**: Modify the agent instructions to emphasize focusing on latest news

## Capabilities

### New Capabilities
- `stock-news-time-range`: Configures Tavily search to only return news from the current week (past 7 days) with exactly 5 results per search

### Modified Capabilities
- `stock-trend-analysis-agent`: Update the system prompt to instruct the agent to prioritize and focus analysis on the latest (most recent) news

## Impact

- **Modified Files**:
  - `backend/services/tavily_search_tool.py` - Add `days` parameter to Tavily search
  - `backend/services/stock_trend_agent.py` - Update system prompt for latest news focus
- **Tavily API**: Uses `days=7` parameter to filter to current week
