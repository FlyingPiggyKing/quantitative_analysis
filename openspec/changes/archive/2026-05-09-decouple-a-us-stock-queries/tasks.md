## 1. State Refactoring

- [x] 1.1 Replace single `loading` state with `aShareLoading` and `usLoading` booleans in WatchList.tsx
- [x] 1.2 Create separate state setters for each market's data loading

## 2. Watchlist Fetch Logic

- [x] 2.1 Modify `useEffect` to fetch A-share watchlist first when activeTab is "A"
- [x] 2.2 Fetch US watchlist independently (after A-share or in parallel based on activeTab)
- [x] 2.3 Set `aShareLoading` to false when A-share watchlist completes
- [x] 2.4 Set `usLoading` to false when US watchlist completes

## 3. Valuation Fetch Logic

- [x] 3.1 Fetch valuations per-market without waiting for both markets
- [x] 3.2 Set valuation state per-market independently as results arrive
- [x] 3.3 Handle valuation fetch errors per-market without blocking the other

## 4. Prediction Fetch Logic

- [x] 4.1 Keep predictions as non-blocking fetch (already uses try/catch)
- [x] 4.2 Ensure predictions don't affect loading state for either market

## 5. UI Updates

- [x] 5.1 Update loading indicator to show per-market loading state
- [x] 5.2 Show A-share data immediately when `aShareLoading` becomes false
- [x] 5.3 Show US data immediately when `usLoading` becomes false
- [x] 5.4 Handle tab switching to initiate fetch when switching to unloaded market

## 6. Testing

- [ ] 6.1 Verify A-share displays immediately without waiting for US stock
- [ ] 6.2 Verify US stock displays immediately without waiting for A-share
- [ ] 6.3 Verify A-share works when US stock API fails
- [ ] 6.4 Verify tab switching loads data correctly
