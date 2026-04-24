## Context

Currently every call to `analyze_stock_trend` invokes the LLM, regardless of whether a valid result was already obtained today. The `TrendPredictionService.save_prediction` already enforces one prediction per symbol per day (upsert), but the **analysis itself** is not skipped — it still runs and then overwrites or is skipped at save time.

This means batch analysis does full LLM work even for stocks analyzed earlier the same day, wasting API calls and time.

## Goals / Non-Goals

**Goals:**
- Skip LLM analysis for stocks that already have a successful prediction (confidence > 0) today
- Return cached result directly when available
- Support force-reanalysis via a `force=true` parameter (for future use by manual refresh or cron)
- Batch analysis skips cached stocks by default

**Non-Goals:**
- This change does NOT add a TTL or expiry mechanism beyond "same day"
- Force-reanalysis UI is not in scope (just the backend interface)
- Changing database schema (one-per-day is already enforced)

## Decisions

### 1. Cache check lives in `TrendPredictionService`

A new static method `get_today_prediction(symbol)` returns the cached prediction for today if it exists and has confidence > 0, otherwise None.

**Why:** Keeps cache logic co-located with storage. The existing `get_latest_prediction` returns the globally latest, not specifically today's.

**Alternatives considered:**
- Check cache inside `analyze_stock_trend` itself — rejected because `analyze_stock_trend` shouldn't know about the DB; separation of concerns.
- Add a new `force` field to `save_prediction` — rejected because the decision to skip analysis should be made before calling `analyze_stock_trend`.

### 2. Cache bypass parameter added at API layer

The `force` parameter is added to:
- `GET /api/trend-predictions/{symbol}` — forces fresh analysis
- `POST /api/trend-predictions/batch` — forces fresh analysis for all stocks
- `POST /api/trend-predictions/batch-async` — forces fresh analysis for all stocks

**Why:** The API layer is where the "should I skip or run" decision is made, and it has access to both the cache check and the analysis call.

**Alternatives considered:**
- Adding `force` to `analyze_stock_trend` — rejected because the agent function shouldn't track daily cache semantics.
- Adding `force` only to batch endpoints — rejected because single-stock view also needs force refresh capability.

### 3. Batch analysis skips cached stocks silently

When `force=false` (default), batch analysis iterates the watchlist, checks cache, and only calls `analyze_stock_trend` for stocks without a valid cached result. Results from cache are included in the response.

**Why:** Consistent with the goal — reduce unnecessary analysis. The response shows all stocks with their current (cached or fresh) status.

### 4. New method: `get_today_prediction`

```python
@staticmethod
def get_today_prediction(symbol: str) -> Optional[dict]:
```

Returns the prediction for `symbol` where `date(analyzed_at) = today` and `confidence > 0`. Returns None if no such record exists.

## Risks / Trade-offs

- **[Risk]** If news is truly time-sensitive (e.g., earnings surprise at 4pm), a cached result from this morning is stale by evening.
  - **Mitigation:** `force=true` is always available for users who need fresh analysis.
  - **Future:** A time-based threshold (e.g., refresh if older than 6 hours) can be added later.
