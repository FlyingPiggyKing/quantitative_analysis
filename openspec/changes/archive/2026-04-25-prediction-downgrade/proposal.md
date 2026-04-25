## Why

The `get_prediction` API (and its frontend consumer `getTrendPrediction`) only returns predictions from the current day via `get_today_prediction`. When no analysis has been run today, the API returns 404 and the frontend displays "暂无分析数据" — even though yesterday's predictions are still fresh and relevant in the database. This creates a poor UX gap between daily analysis runs.

## What Changes

- Modify the `/api/trend-predictions/{symbol}` endpoint so that when `force=false` and no prediction exists for today, it falls back to returning the **most recent prediction** from the database instead of 404
- The frontend (`TrendAnalysisPanel` on stock detail page, `PresetStockList` on homepage) will always show available prediction data instead of "暂无分析数据"
- Force analysis behavior remains unchanged (requires auth, rate-limited, always runs fresh analysis)
- The "降级返回最近一次预测" label should be clearly communicated in the response so frontend can indicate data freshness to users

## Capabilities

### New Capabilities

- `prediction-fallback`: When no prediction exists for the current day, fall back to the most recent prediction in the database. Add a `is_fallback` boolean field to the API response so the frontend can indicate when data may be stale (not from today).

### Modified Capabilities

- `stock-trend-prediction-storage`: The `get_prediction` endpoint behavior changes — it now returns fallback data instead of 404 when today's cache is empty. No schema changes to the `predictions` table.

## Impact

- **Backend**: `backend/api/trend_prediction.py` — `get_prediction` endpoint (line ~93-138) — change 404 fallback behavior
- **Backend**: `backend/services/trend_prediction_service.py` — add `get_latest_prediction` already exists, no service changes needed
- **Frontend**: `frontend/src/app/stock/[symbol]/page.tsx` — already handles null `trendPrediction` gracefully, will now more frequently receive data
- **Frontend**: `frontend/src/components/PresetStockList.tsx` — will now receive predictions more frequently (from the fallback path)
