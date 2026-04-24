## Why

Currently, when a user navigates to a stock detail page, the trend analysis automatically runs on page load. This creates two problems: (1) unnecessary API calls for stocks the user may only glance at, and (2) confusion between the stock detail page's analysis and the home page's batch analysis queue for watch list stocks. The user wants explicit control over when to trigger a forced single-stock analysis, separate from the batch queue system.

## What Changes

- Remove automatic trend analysis fetch on stock detail page load
- Add a visible "Force Analysis Now" (立刻分析) button on the trend analysis block
- The button triggers a forced single-stock analysis via direct API call (not batch queue)
- The button should appear regardless of whether existing prediction data exists (user can re-analyze)
- The home page batch analysis queue remains unchanged - it is only for watch list stocks

## Capabilities

### New Capabilities

- `single-stock-force-analysis`: A dedicated single-stock forced analysis capability triggered by user action on the stock detail page. This bypasses the batch queue and performs immediate synchronous analysis for the specific stock.

### Modified Capabilities

- `stock-trend-display`: The stock detail page behavior changes - auto-fetch on load is replaced with on-demand button-triggered analysis.

## Impact

- **Frontend**: Stock detail page (`/stock/[symbol]`) - remove auto-fetch useEffect, add Force Analysis button
- **Backend**: No new endpoints needed - existing `GET /api/trend-predictions/{symbol}?force=true` provides the required functionality
- **User Experience**: Clear separation between home page batch analysis and stock detail page single-stock analysis
