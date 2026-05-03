## Why

The current WatchList component couples A-share and US stock data fetching - the batch valuation request combines all symbols into a single API call, causing US stock failures to block A-share data display. The user wants independent data fetching where each market's data loads separately, similar to the guest view (stock detail page) behavior.

## What Changes

- Modify WatchList to fetch A-share and US stock valuations independently
- Each market tab should load its own valuation data without waiting for the other
- Failures in one market's data should not affect the other market's display
- Trend predictions should also be fetched independently per market

## Capabilities

### New Capabilities
- `watch-list-independ-valuation-query`: Fetch A-share and US stock valuation data independently in WatchList, allowing each market to display its data as soon as available without blocking on the other market

### Modified Capabilities
- `watch-list-display`: Update to reflect that valuation data is now fetched per-market independently, not as a single batch

## Impact

**Frontend**: `frontend/src/components/WatchList.tsx` - modify data fetching logic to separate A-share and US stock valuation queries
**Backend**: No changes required - existing batch API endpoints can handle single-market requests
