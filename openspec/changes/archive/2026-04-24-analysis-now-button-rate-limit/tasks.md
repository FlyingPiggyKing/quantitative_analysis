## 1. Database Schema Changes

- [x] 1.1 Add `user_analysis_triggers` table to `trend_prediction_service.py`
  - Columns: `user_id` (text), `symbol` (text), `triggered_at` (timestamp)
  - Add primary key on (user_id, symbol)
  - Create index on (user_id, symbol, triggered_at) for efficient lookups

## 2. Backend Rate Limit Service

- [x] 2.1 Add `check_rate_limit(user_id, symbol)` method to `TrendPredictionService`
  - Query: SELECT triggered_at FROM user_analysis_triggers WHERE user_id=? AND symbol=? ORDER BY triggered_at DESC LIMIT 1
  - Return True if last trigger was within 1 hour, False otherwise

- [x] 2.2 Add `record_trigger(user_id, symbol)` method to `TrendPredictionService`
  - Insert new row with current timestamp
  - Handle duplicate key by updating triggered_at

- [x] 2.3 Add `get_rate_limit_remaining_seconds(user_id, symbol)` method
  - Return seconds until rate limit expires, or 0 if no active cooldown

## 3. Backend API Changes

- [x] 3.1 Modify `GET /api/trend-predictions/{symbol}` endpoint in `trend_prediction.py`
  - Add `Depends(get_current_user)` parameter
  - When `force=true`: check rate limit before processing
  - If rate limited: return HTTP 429 with `retry_after` header and JSON body

- [x] 3.2 Update `runForcedSingleAnalysis` frontend function to handle 429 response
  - Extract `retry_after` from response
  - Throw error with remaining seconds info

## 4. Frontend State Management

- [x] 4.1 Add cooldown state to stock detail page (`page.tsx`)
  - `cooldownEndTime: number | null` state
  - Check localStorage on mount: `analysis_cooldown_{user_id}_{symbol}`

- [x] 4.2 Add localStorage helper functions in `trendPrediction.ts`
  - `setCooldownEndTime(userId, symbol, endTime)`
  - `getCooldownEndTime(userId, symbol): number | null`
  - `clearCooldownEndTime(userId, symbol)`

- [x] 4.3 Update `handleRunAnalysis` to store cooldown on success
  - After successful API call, set cooldown end time (now + 1 hour)

## 5. Frontend UI Updates

- [x] 5.1 Update "立刻分析" button disabled logic
  - Button disabled when `analysisRunning` OR `cooldownEndTime` is set

- [x] 5.2 Add countdown display on button
  - When cooldown active: show "剩余 X:XX" instead of "立刻分析"
  - Update countdown every second using `setInterval`

- [x] 5.3 Clear cooldown when API returns 429
  - Display error message with remaining time
