## Context

Currently, `ASharePresetList` and `USPresetList` components each fetch stock data and trend predictions using `Promise.all`. The `getTrendPredictions()` call is treated as blocking - if it's slow or fails, the entire component stays in loading state even if stock info and valuation data have already arrived.

This causes the user-perceived delay where A-share data doesn't display until US stock queries complete (or fail).

## Goals / Non-Goals

**Goals:**
- A-share data displays immediately when A-share stock data arrives, regardless of US stock query state
- US stock data displays immediately when US stock data arrives, regardless of A-share query state
- Each market's loading/error state is independent
- Failed queries for one market do not affect the other market's display

**Non-Goals:**
- Not changing the backend API structure
- Not adding new API endpoints
- Not implementing global request deduplication or caching (already exists)

## Decisions

### 1. Decouple predictions from blocking loading state

**Choice**: Trend predictions fetched via `getTrendPredictions()` will be treated as non-critical data. Stock info and valuation are critical and blocking.

**Why**: Trend predictions are supplementary display data. The user should see stock information immediately even if AI predictions are unavailable or loading slowly.

**Implementation**:
- Each preset list component will have independent state for: `infoLoading`, `valLoading`, `predLoading`
- Component loading state is `infoLoading || valLoading` (predictions excluded)
- Component shows data when `info` and `val` are available, even if `predictions` are still loading

### 2. Add timeout wrapper for predictions fetch

**Choice**: Wrap `getTrendPredictions()` with a 5-second timeout to prevent slow predictions endpoint from blocking display.

**Why**: External API (`/api/trend-predictions`) is not critical path. A 5-second timeout balances between allowing some wait time and ensuring responsiveness.

**Implementation**:
```typescript
async function fetchWithTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T | null> {
  const timeoutPromise = new Promise<T | null>((resolve) =>
    setTimeout(() => resolve(null), timeoutMs)
  );
  return Promise.race([promise, timeoutPromise]);
}
```

### 3. Separate loading states per market

**Choice**: Each market (A-share, US) maintains its own loading states in parent component.

**Why**: Independent components (`ASharePresetList`, `USPresetList`) already have independent states. The issue is how loading is computed within each component.

**Implementation**:
- `ASharePresetList`:
  - `infoLoading`: true until stock info fetched or failed
  - `valLoading`: true until valuation fetched or failed
  - `predLoading`: true until predictions fetched, failed, or timed out
  - `isLoading` = `infoLoading && valLoading` (predictions excluded)
- Same pattern for `USPresetList`

## Risks / Trade-offs

**[Risk] Race condition when switching tabs during load** → Users switching between A/US tabs rapidly might see inconsistent state if one tab's data arrives after user switched away. **Mitigation**: Components use `fetchedRef` guard to prevent duplicate fetches. Data arrival after tab switch is acceptable (user will see it if they switch back).

**[Risk] Duplicate predictions fetch** → Both `ASharePresetList` and `USPresetList` call `getTrendPredictions()` separately. **Mitigation**: This is acceptable since predictions are cached server-side and a 5-second timeout prevents long waits. Future enhancement could deduplicate at component level.

**[Trade-off] Timeout loses predictions** → 5-second timeout might cut off predictions that would have arrived at 6 seconds. **Mitigation**: 5 seconds is generous for a cached API endpoint. Most responses arrive in < 1 second.
