## 1. Modify WatchList State Structure

- [x] 1.1 Split `valuations` state into separate `aShareValuations` and `usValuations` states
- [x] 1.2 Split `predictions` state into separate `aSharePredictions` and `usPredictions` states

## 2. Implement Independent Valuation Fetching

- [x] 2.1 Create helper function `fetchValuationByMarket(symbols, market)` to fetch valuation for specific market
- [x] 2.2 Modify `useEffect` to use `Promise.allSettled` for A-share and US valuation fetches
- [x] 2.3 Update state independently when each market's valuation data arrives

## 3. Implement Independent Prediction Fetching

- [x] 3.1 Modify prediction fetching to split by market (filter `aShareItems` and `usItems` symbols)
- [x] 3.2 Use `Promise.allSettled` to fetch A-share and US predictions independently
- [x] 3.3 Update `aSharePredictions` and `usPredictions` states independently

## 4. Update MarketWatchlist Props

- [x] 4.1 Change `valuations` prop to accept `aShareValuations` or `usValuations` based on market
- [x] 4.2 Change `predictions` prop to accept `aSharePredictions` or `usPredictions` based on market

## 5. Verify Fault Isolation

- [ ] 5.1 Test that A-share data displays when US API fails
- [ ] 5.2 Test that US data displays when A-share API fails
- [ ] 5.3 Test that each market's loading/error state is independent
