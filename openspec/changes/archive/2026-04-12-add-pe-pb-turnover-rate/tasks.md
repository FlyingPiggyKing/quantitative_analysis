## 1. Backend API - Valuation Data

- [x] 1.1 Add `get_valuation_data` method to `backend/services/akshare_service.py` using Tushare `daily_basic` endpoint
- [x] 1.2 Create new API endpoint `GET /api/stock/{symbol}/valuation` in `backend/api/stock.py`
- [x] 1.3 Test the new endpoint returns correct JSON structure with `current` and `history` fields

## 2. Frontend - Watch List Enhancement

- [x] 2.1 Add `fetch('/api/stock/{symbol}/valuation')` call in `WatchList.tsx` for each stock
- [x] 2.2 Add PE and PB columns to the watch list table in `WatchList.tsx`
- [x] 2.3 Handle null/missing PE/PB values by displaying "-" placeholder
- [x] 2.4 Test watch list displays PE and PB correctly

## 3. Frontend - Stock Detail Page Enhancement

- [x] 3.1 Add valuation data fetch in `frontend/src/app/stock/[symbol]/page.tsx`
- [x] 3.2 Add PE, PB, and turnover rate display in the stock detail header area
- [x] 3.3 Test detail page shows current valuation metrics correctly

## 4. Frontend - StockChart PE/PB Line Series

- [x] 4.1 Modify `StockChart.tsx` to accept optional `peData` and `pbData` arrays
- [x] 4.2 Add line series for PE (yellow #fbbf24) using `addSeries(LineSeries)`
- [x] 4.3 Add line series for PB (purple #8b5cf6) using `addSeries(LineSeries)`
- [x] 4.4 Configure separate price scale for PE/PB series on the right axis
- [x] 4.5 Add chart legend showing PE and PB labels with current values
- [x] 4.6 Handle null data points gracefully (skip or interpolate)
- [x] 4.7 Test chart displays PE/PB lines below volume correctly

## 5. Integration Testing

- [x] 5.1 Test full flow: add stock to watch list → view detail page → verify PE/PB charts render
- [x] 5.2 Test edge case: stock with null PE/PB (new listing) displays correctly
- [x] 5.3 Verify Tushare rate limiting doesn't break functionality with multiple stocks
