## Why

When refreshing the watchlist from mobile, A-share stock data takes 7+ seconds to display because it waits for US stock data to load, even though A-share and US stock are independent markets. The root cause is the frontend uses a shared `loading` state that blocks both markets until all data (including slow US stock) is fetched.

## What Changes

1. **Separate loading states** for A-share and US stock data in the WatchList component
2. **Independent data fetching** per market - each market's watchlist, valuations, and predictions load without blocking the other
3. **Graceful degradation** - A-share continues to display even if US stock fails or is slow
4. **Lazy valuation fetching** - only fetch valuations for the currently active tab initially

## Capabilities

### New Capabilities
- `independent-watchlist-loading`: Independent loading states per market tab, allowing A-share to display without waiting for US stock

### Modified Capabilities
- `watch-list-display`: Update to require per-market loading states instead of shared loading state (no delta spec needed - implementation change only)

## Impact

- **Frontend**: WatchList.tsx component needs refactoring to use separate loading states per market
- **Backend**: No changes required - API already supports independent queries per market
