## 1. Add fetchWithTimeout utility

- [x] 1.1 Create `fetchWithTimeout` helper function in `frontend/src/services/trendPrediction.ts`
  - Function signature: `async function fetchWithTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T | null>`
  - Uses `Promise.race` between the original promise and a timeout promise
  - Returns `null` on timeout instead of throwing

## 2. Refactor ASharePresetList for independent loading

- [x] 2.1 Split loading state into three separate states: `infoLoading`, `valLoading`, `predLoading`
- [x] 2.2 Modify `fetchData` to await info and val results for loading state, but not predictions
- [x] 2.3 Wrap `getTrendPredictions()` call with `fetchWithTimeout(..., 5000)`
- [x] 2.4 Update component to display stock data when `infoMap` and `valMap` have data, regardless of `predLoading`
- [x] 2.5 Handle prediction timeout/failure gracefully (show "-" in prediction column)

## 3. Refactor USPresetList for independent loading

- [x] 3.1 Split loading state into three separate states: `infoLoading`, `valLoading`, `predLoading`
- [x] 3.2 Modify `fetchData` to await info and val results for loading state, but not predictions
- [x] 3.3 Wrap `getTrendPredictions()` call with `fetchWithTimeout(..., 5000)`
- [x] 3.4 Update component to display stock data when `infoMap` and `valMap` have data, regardless of `predLoading`
- [x] 3.5 Handle prediction timeout/failure gracefully (show "-" in prediction column)

## 4. Verify independence

- [ ] 4.1 Test that A-share data displays immediately when US tab is switched to but US data hasn't loaded
- [ ] 4.2 Test that US data displays immediately when A-share is still loading
- [ ] 4.3 Test that A-share data still displays when US predictions timeout or fail
- [ ] 4.4 Test that US data still displays when A-share predictions timeout or fail
