## 1. Frontend Changes

- [x] 1.1 Import `TrendPrediction` type and `getTrendPredictions` in `PresetStockList.tsx`
- [x] 1.2 Add state for predictions: `Record<string, TrendPrediction>`
- [x] 1.3 Fetch trend predictions alongside existing batch fetches in `useEffect`
- [x] 1.4 Add `TrendIndicator` function component (reused from WatchList pattern)
- [x] 1.5 Add "AI下周预测" column to desktop table view header
- [x] 1.6 Render trend indicator in desktop table body for each stock
- [x] 1.7 Add trend indicator to mobile card view

## 2. Verification

- [ ] 2.1 Test guest view displays predictions when available
- [ ] 2.2 Test guest view shows "-" when no prediction exists
- [ ] 2.3 Verify colors match logged-in view (green/red/gray)
