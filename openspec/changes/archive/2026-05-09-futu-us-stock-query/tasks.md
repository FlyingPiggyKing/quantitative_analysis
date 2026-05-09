## 1. Setup and Dependencies

- [x] 1.1 Verify `futu-api` SDK is installed (`pip show futu-api` or check requirements.txt)
- [x] 1.2 Add `futu-api >= 10.4.6408` to requirements.txt if not present
- [x] 1.3 Add `FUTU_OPEND_HOST=127.0.0.1` and `FUTU_OPEND_PORT=11111` to backend .env file
- [x] 1.4 Verify OpenD is running and accessible

## 2. Create FutuQuoteService

- [x] 2.1 Create `backend/services/futu_quote_service.py` with `OpenQuoteContext` connection management
- [x] 2.2 Implement `_symbol_to_futu_code()` helper (e.g., `AAPL` → `US.AAPL`)
- [x] 2.3 Implement `FutuQuoteService.get_snapshot()` - PE, PB, turnover_rate, market_cap
- [x] 2.4 Implement `FutuQuoteService.get_kline()` - historical K-line data
- [x] 2.5 Implement `FutuQuoteService.get_stock_info()` - basic info (name, sector)
- [x] 2.6 Implement `FutuQuoteService.get_realtime_quote()` - realtime price data

## 3. Implement Caching

- [x] 3.1 Create `_FutuCache` class similar to `_YFCache` with 5-minute TTL
- [x] 3.2 Integrate caching into `FutuQuoteService` methods
- [x] 3.3 Implement stale-on-error fallback (return stale cache if Futu fails)

## 4. Implement Batch Operations

- [x] 4.1 Implement `FutuQuoteService.get_stock_info_batch()` - batch stock info
- [x] 4.2 Implement `FutuQuoteService.get_daily_basic_batch()` - batch valuation metrics
- [x] 4.3 Use ThreadPoolExecutor for concurrent fetching

## 5. Integrate with Existing API

- [x] 5.1 Modify `backend/services/akshare_service.py` - update `USStockService` to use `FutuQuoteService`
- [x] 5.2 Ensure API response format matches existing endpoints (`/api/stock/{symbol}/valuation`, etc.)
- [x] 5.3 Verify all existing API routes work without frontend changes

## 6. Testing

- [ ] 6.1 Test `/api/stock/AAPL/valuation` returns PE, PB, turnover_rate
- [ ] 6.2 Test `/api/stock/AAPL/kline` returns historical K-line data
- [ ] 6.3 Test `/api/stock/AAPL/realtime` returns current price
- [ ] 6.4 Test `/api/stock/AAPL` returns basic info
- [ ] 6.5 Test batch endpoints work correctly
- [ ] 6.6 Test error handling (invalid symbol, OpenD not running)
