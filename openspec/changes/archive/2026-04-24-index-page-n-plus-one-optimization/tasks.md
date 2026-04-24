## 1. Backend Batch API Implementation

- [x] 1.1 Add `get_daily_basic_batch()` method to `AkshareService` that accepts list of symbols and makes single Tushare API call
- [x] 1.2 Add `get_stock_info_batch()` method to `AkshareService` for batch stock info (if info endpoint needed)
- [x] 1.3 Create `GET /api/stock/batch/valuation` endpoint in `backend/api/stock.py`
- [x] 1.4 Create `GET /api/stock/batch/info` endpoint in `backend/api/stock.py`
- [x] 1.5 Add error handling for partial batch failures (return errors array)
- [ ] 1.6 Test batch endpoints with multiple symbols

## 2. Frontend WatchList Refactor

- [x] 2.1 Add batch fetch utility function or inline batch call in `WatchList.tsx`
- [x] 2.2 Replace per-stock `Promise.all` valuation loop with single batch API call
- [x] 2.3 Update response mapping to handle batch response format
- [x] 2.4 Verify WatchList loads correctly with batch API

## 3. Frontend PresetStockList Refactor

- [x] 3.1 Update `PresetStockList.tsx` to use batch valuation endpoint
- [x] 3.2 Replace dual per-stock requests (info + valuation) with batch equivalents
- [x] 3.3 Update response mapping for batch responses
- [x] 3.4 Verify PresetStockList loads correctly with batch API

## 4. Performance Verification

- [x] 4.1 Verify network requests reduced from N+1 to 1-2 per page load
- [x] 4.2 Test with various watchlist sizes (1, 5, 10, 20 stocks)
- [x] 4.3 Verify error handling works for partial batch failures
