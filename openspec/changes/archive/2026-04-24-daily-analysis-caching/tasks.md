## 1. TrendPredictionService — Add get_today_prediction

- [x] 1.1 Add `get_today_prediction(symbol: str) -> Optional[dict]` static method to `TrendPredictionService`
  - Query `SELECT ... FROM predictions WHERE symbol = ? AND date(analyzed_at) = ? AND confidence > 0 ORDER BY analyzed_at DESC LIMIT 1`
  - Return the row as dict (same shape as `get_latest_prediction`) or None

## 2. API Layer — Add force parameter to single-stock endpoint

- [x] 2.1 Update `GET /api/trend-predictions/{symbol}` to accept optional `force: bool = False` query parameter
  - When `force=false` (default): check `get_today_prediction(symbol)`, return cached if found
  - When `force=true`: run fresh `analyze_stock_trend`, save result, return

## 3. API Layer — Add force parameter to batch endpoints

- [x] 3.1 Update `POST /api/trend-predictions/batch` to accept optional `force: bool = False` in request body
  - When `force=false`: iterate watchlist, call `get_today_prediction` first, skip stocks with valid cache
  - When `force=true`: analyze all stocks regardless of cache
  - Include cached results in response for skipped stocks

- [x] 3.2 Update `POST /api/trend-predictions/batch-async` to accept optional `force: bool = False`
  - Pass `force` flag through to `submit_analysis_task`

## 4. Task Queue — Respect cache in background batch

- [x] 4.1 Modify `submit_analysis_task` to accept `force: bool = False` parameter
- [x] 4.2 In `_run_analysis`, when `force=False`: check `get_today_prediction` before calling `analyze_stock_trend`
  - Skip analysis and reuse cached result for stocks with valid cache
