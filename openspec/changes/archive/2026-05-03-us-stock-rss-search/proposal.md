## Why

Current US stock news search relies on MiniMax MCP which returns inconsistent results (Chinese sources, incomplete content). By using Yahoo Finance RSS as the primary news source and enhancing with MiniMax search, we can improve news relevance and quality for US stock analysis at zero additional cost.

## What Changes

1. **New RSS-based news fetching**: For US stocks, fetch Yahoo Finance RSS feed via proxy to get authoritative news list
2. **Agent-driven news selection**: Pass RSS news list to Agent to select Top 5 based on importance and timeliness
3. **Enhanced search workflow**: Use selected Top 5 news titles to perform focused MiniMax searches for additional details
4. **Combined analysis**: Merge RSS news + MiniMax search results with existing technical data for final analysis
5. **A-share unchanged**: Continue using existing news search logic for A-shares

## Capabilities

### New Capabilities
- `yahoo-finance-rss-fetch`: Capability to fetch Yahoo Finance RSS feed via proxy, parse news items (title, summary, URL, date)
- `rss-news-selection`: Capability for Agent to select Top 5 news from RSS list based on importance and timeliness
- `focused-news-search`: Capability to perform focused search using selected news titles

### Modified Capabilities
- `stock-news-time-range`: Extend to support market-specific search strategies (RSS + MiniMax for US, existing logic for A-share)

## Impact

- **Modified files**: `backend/services/stock_trend_agent.py`
- **New dependencies**: `requests` library for RSS fetching (if not already installed), proxy configuration
- **Search behavior**: US stocks use RSS + MiniMax search, A-shares unchanged
- **Cost**: Zero (uses existing MiniMax MCP, only adds RSS fetch)
