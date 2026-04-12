## Why

The stock trend agent currently makes predictions based purely on news sentiment, ignoring the rich technical indicator data (MACD, RSI, MA) that is already computed in `akshare_service.py`. This is the single biggest gap limiting prediction quality — the agent never sees actual price action, volume trends, or chart signals.

## What Changes

1. Modify `analyze_stock_trend()` in `stock_trend_agent.py` to fetch 60 days of K-line data and compute technical indicators before invoking the LLM agent
2. Create `format_data_context()` helper to convert quantitative data into a readable text block for LLM context
3. Update the agent's system prompt to instruct the LLM to weigh technical signals (40%) alongside news sentiment (60%)
4. The prediction output format (`trend_direction`, `confidence`, `summary`) remains unchanged — no frontend changes required

## Capabilities

### New Capabilities
- `trend-analysis-technical-enrichment`: Feeds existing K-line data and technical indicators into the LLM agent's context so it makes decisions based on both news AND price data

### Modified Capabilities
- `stock-trend-analysis-agent`: The agent's input context expands from just symbol/name to include structured technical data (price trend, MACD, RSI, MA signals). The weighting of technical vs sentiment analysis is now specified in requirements.

## Impact

- **Modified**: `backend/stock_trend_agent.py` — adds data fetching, formatting, and prompt enrichment
- **No frontend changes**: Prediction output format unchanged
- **No new dependencies**: Uses existing `AkshareService.get_kline_data()` and `AkshareService.calculate_indicators()`
