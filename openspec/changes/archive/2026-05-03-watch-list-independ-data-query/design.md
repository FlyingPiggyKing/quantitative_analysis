## Context

The WatchList component currently fetches A-share and US stock data in a coupled manner. When a user loads the WatchList:

1. `Promise.all` fetches A-share and US watchlist items in parallel (correct)
2. Sequential fetch of trend predictions (blocks)
3. Single batch valuation request for ALL symbols combined (problematic)

The batch valuation request combines A-share and US symbols into one API call to `/api/stock/batch/valuation?symbols=...`. If US stock data is slow or fails, the entire valuation state update is blocked, causing the WatchList to show stale or no data.

The guest view (PresetStockList) demonstrates the desired pattern where A-share and US stocks load independently using `Promise.all` for each market's data.

## Goals / Non-Goals

**Goals:**
- A-share and US stock valuation data fetch independently
- Each market displays as soon as its data arrives
- Failures in one market do not affect the other market's display
- Trend predictions load independently per market

**Non-Goals:**
- No backend changes - continue using existing `/api/stock/batch/valuation` endpoint
- No changes to guest view (PresetStockList) - already working correctly
- No changes to authentication flow

## Decisions

### Decision: Split batch valuation into separate market-specific calls

**Option A: Separate API calls per market** (Selected)
- Fetch A-share symbols via `/api/stock/batch/valuation?symbols=A-share-symbols`
- Fetch US symbols via `/api/stock/batch/valuation?symbols=US-symbols`
- Both calls execute in parallel via `Promise.all`
- Each call updates its own state independently

**Option B: Single combined batch call with retry logic**
- Keep using combined batch call
- Add retry logic for failed symbols
- Rejected: Still couples the markets - if API fails entirely, nothing shows

**Option C: Individual stock valuation calls**
- Fetch each stock's valuation individually
- Rejected: Creates N+1 query problem, more network overhead

### Decision: Independent state management per market

Each market maintains its own state:
- `aShareValuations`: Record<string, ValuationData>
- `usValuations`: Record<string, ValuationData>
- `aSharePredictions`: Record<string, TrendPrediction>
- `usPredictions`: Record<string, TrendPrediction>

This allows each market to update independently without affecting the other.

### Decision: Use Promise.allSettled for fault isolation

```typescript
// Instead of Promise.all (fails fast)
const [aShareVal, usVal] = await Promise.all([
  fetchAShareValuation(symbols),
  fetchUSValuation(symbols),
]);

// Use Promise.allSettled (continues even if one fails)
const [aShareResult, usResult] = await Promise.allSettled([
  fetchAShareValuation(symbols),
  fetchUSValuation(symbols),
]);
```

This ensures that if US stock API fails, A-share data still populates.

## Risks / Trade-offs

[Risk] Increased number of API calls → Mitigation: Still 2 calls (one per market) instead of N individual calls. Acceptable trade-off for fault isolation.

[Risk] Different loading states per market may cause UI flicker → Mitigation: Accept initial loading state, both markets will settle quickly in normal operation.

[Risk] Empty state handling needs to be per-market → Mitigation: MarketWatchlist component already handles empty state independently.
