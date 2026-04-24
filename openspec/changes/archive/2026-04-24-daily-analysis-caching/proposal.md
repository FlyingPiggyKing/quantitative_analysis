## Why

Currently, every time a user views a stock's trend analysis, the system performs a full analysis (fetching K-line data, searching news, invoking LLM). This is wasteful when the same stock has already been successfully analyzed today — the result is unlikely to change within the same day. Adding a daily analysis cache reduces unnecessary LLM calls and improves response time.

## What Changes

- **Add daily analysis caching**: Before performing a new analysis, check if a successful prediction (confidence > 0) already exists for today. If yes, skip analysis and return cached result.
- **Add force-reanalysis interface**: Provide a way to bypass the cache and force a fresh analysis (useful for manual refresh and future cron-based updates).
- **Batch analysis respects cache**: When batch analyzing watchlist, stocks with valid cached results today are skipped.

## Capabilities

### New Capabilities
- `daily-analysis-cache`: Caches successful (confidence > 0) trend predictions per stock per day. On analysis request, checks if a valid cached result exists for today and returns it directly. Includes a `force=true` parameter to bypass cache.

### Modified Capabilities
- `stock-trend-prediction-storage`: Extend the existing storage service to support cache checking (query today's prediction for a symbol) and expose the force-update behavior.

## Impact

- **Backend**: `TrendPredictionService` gets a new method to check today's cached result. `analyze_stock_trend` (in `stock_trend_agent.py`) checks cache before invoking LLM. Batch analysis logic skips cached stocks.
- **API**: `POST /api/trend-predictions/batch` and the single-stock analysis endpoint accept optional `force=true` to bypass cache.
- **No database schema changes** — cache lives in existing `predictions` table (one per symbol per day already enforced).
