## Why

Yahoo Finance contains high-quality, timely analysis articles for US stocks that are more relevant than generic news searches. For US stock analysis, prioritizing Yahoo Finance news (e.g., `https://finance.yahoo.com/markets/stocks/articles/...`) will improve prediction accuracy. A-shares (A股) will continue using the existing search logic which works well for Chinese markets.

## What Changes

1. **US stocks**: Prioritize Yahoo Finance news search before fallback to generic search
2. **A-shares**: No change - continue using existing `search_with_fallback` logic unchanged
3. **Detection**: Use existing `market` variable ("US" vs "A") to determine search strategy

## Capabilities

### New Capabilities
- `yahoo-finance-us-search`: Capability to perform Yahoo Finance-specific search for US stock news, with fallback to generic search

### Modified Capabilities
- `stock-news-time-range`: Extend to support market-specific search strategies (Yahoo Finance for US, generic for A-share)

## Impact

- **Modified files**: `backend/services/stock_trend_agent.py`
- **New dependencies**: None (Yahoo Finance is publicly accessible)
- **Search behavior**: US stocks use Yahoo Finance as primary source, A-shares unchanged
