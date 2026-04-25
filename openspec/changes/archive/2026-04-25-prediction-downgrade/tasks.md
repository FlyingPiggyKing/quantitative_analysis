## 1. Backend Changes

- [x] 1.1 Add `is_fallback` field to `PredictionResponse` Pydantic model in `backend/api/trend_prediction.py`
- [x] 1.2 Modify `get_prediction` endpoint — when `force=false` and `get_today_prediction` returns None, call `get_latest_prediction` instead of raising 404
- [x] 1.3 Set `is_fallback=true` when returning a fallback prediction, `is_fallback=false` when returning today's prediction

## 2. Frontend Changes

- [x] 2.1 Add `is_fallback?: boolean` field to `TrendPrediction` interface in `frontend/src/services/trendPrediction.ts`

## 3. Verification

- [ ] 3.1 Verify `/api/trend-predictions/300750` returns fallback data with `is_fallback=true` when called without today's analysis
- [ ] 3.2 Verify force analysis still returns `is_fallback=false`
- [ ] 3.3 Verify frontend stock detail page displays fallback predictions correctly
