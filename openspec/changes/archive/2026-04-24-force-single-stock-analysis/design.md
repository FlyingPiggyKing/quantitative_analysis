## Context

Currently, the stock detail page (`/stock/[symbol]`) automatically fetches trend prediction on page load via a `useEffect` hook. The `handleRunAnalysis` button only appears when `!trendPrediction && !trendLoading` (no existing prediction). The batch analysis endpoint (`POST /api/trend-predictions/batch-async`) is designed for the home page watch list queue.

## Goals / Non-Goals

**Goals:**
- Remove automatic trend prediction fetch on stock detail page load
- Add a "Force Analysis Now" (立刻分析) button that triggers immediate forced single-stock analysis
- Use existing backend endpoint `GET /api/trend-predictions/{symbol}?force=true` for the forced analysis
- Clear separation between stock detail page analysis and home page batch queue

**Non-Goals:**
- No new backend endpoints required
- Not modifying the batch analysis queue system
- Not changing the home page trend analysis behavior

## Decisions

### Decision: Use existing `force=true` endpoint instead of new endpoint

**Choice:** Call `GET /api/trend-predictions/{symbol}?force=true` directly on button click.

**Rationale:** The existing endpoint already provides forced single-stock analysis. Creating a redundant endpoint would increase maintenance burden without benefit.

**Alternatives considered:**
- Create `POST /api/trend-predictions/single/{symbol}` - rejected; existing endpoint suffices

### Decision: Always show the Force Analysis button

**Choice:** The button appears regardless of whether a prediction exists.

**Rationale:** User may want to refresh/re-analyze even when cached data exists. The button provides explicit control over when analysis triggers.

**Alternatives considered:**
- Only show when no prediction exists - rejected; doesn't support re-analysis use case

### Decision: Synchronous analysis call (no background queue)

**Choice:** Direct API call that waits for result, not batch-async queue.

**Rationale:** Stock detail page analysis is for a single stock and completes quickly. Using the batch queue would confuse the user's mental model between single-stock and batch analysis.

## Risks / Trade-offs

- **Risk:** User clicks button multiple times rapidly
  - **Mitigation:** Disable button during loading state

- **Risk:** Analysis takes time and user doesn't understand what's happening
  - **Mitigation:** Show loading state on button and in the trend section

## Open Questions

None - the implementation is straightforward with existing endpoints.
