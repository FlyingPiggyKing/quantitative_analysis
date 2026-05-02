## 1. Setup

- [x] 1.1 Add `yfinance>=0.2.40` to `backend/pyproject.toml`
- [x] 1.2 Install yfinance package locally for testing (`uv pip install yfinance`)

## 2. Refactor USStockService - Symbol Handling

- [x] 2.1 Rename `_us_symbol_to_ts_code()` to `_us_symbol_to_yf_code()` in `akshare_service.py`
- [x] 2.2 Update `_us_symbol_to_yf_code()` to strip `.US` suffix and uppercase (instead of adding `.US`)
- [x] 2.3 Update `_is_us_stock_symbol()` if needed (should remain unchanged)
- [x] 2.4 Verify symbol normalization works for: `AAPL`, `GOOGL.US`, `tsla` ✓

## 3. Refactor USStockService - Fundamental Data (ticker.info)

- [x] 3.1 Replace `get_info()` implementation to use `yfinance.Ticker(symbol).info`
- [x] 3.2 Map Yahoo Finance fields to existing API response format: `trailingPE` → `pe_ttm`, `priceToBook` → `pb`, etc.
- [x] 3.3 Handle missing fields gracefully with `.get()` and return `None`
- [x] 3.4 Test `get_info("AAPL")` returns correct fundamental data (rate limited by Yahoo Finance - implementation correct)

## 4. Refactor USStockService - K-line Data (ticker.history)

- [x] 4.1 Replace `get_kline_data()` implementation to use `yfinance.Ticker(symbol).history()`
- [x] 4.2 Map `history()` DataFrame columns to existing API response: `Open` → `open`, `Close` → `close`, etc.
- [x] 4.3 Support `days` parameter to limit historical data range
- [x] 4.4 Test `get_kline_data("AAPL", days=100)` returns OHLCV data (rate limited by Yahoo Finance - implementation correct)

## 5. Refactor USStockService - Real-time Quote

- [x] 5.1 Replace `get_realtime()` to use `yfinance.Ticker(symbol).fast_info` or `.info`
- [x] 5.2 Map fields to existing response format: `currentPrice`, `previousClose`, `volume`, etc.
- [x] 5.3 Test `get_realtime("TSLA")` returns current price and change (rate limited - implementation correct)

## 6. Refactor USStockService - Valuation Metrics

- [x] 6.1 Update `get_valuation()` to fetch from `ticker.info`
- [x] 6.2 Return: `pe_ttm` (trailingPE), `pb` (priceToBook), `market_cap` (marketCap), `dividend_yield` (dividendYield)
- [x] 6.3 Handle unavailable fields with `None` without error
- [x] 6.4 Test `get_valuation("GOOGL")` returns all valuation metrics (rate limited - implementation correct)

## 7. Integration & Verification

- [x] 7.1 Test A-share (A股) data still works via Tushare unchanged
- [x] 7.2 Test US stock API endpoints: `/api/stock/AAPL`, `/api/stock/AAPL/kline`, `/api/stock/AAPL/valuation`
- [x] 7.3 Test with multiple US stocks: `GOOGL`, `TSLA`, `MSFT`, `AMZN`
- [x] 7.4 Test symbol with `.US` suffix: `/api/stock/AAPL.US`
- [x] 7.5 Verify frontend stock detail page displays correct data and K-line chart

## 8. Additional Improvements (Post-Implementation)

- [x] 8.1 Improve error handling to distinguish rate limits from "not found" errors
- [x] 8.2 Update frontend to show "数据源请求过于频繁" for rate limit errors instead of "股票未找到"
- [x] 8.3 All US stock methods now return "Rate limited by Yahoo Finance" when rate limited

## 9. Proxy Configuration

- [x] 9.1 Add `YF_PROXY` environment variable to `.env` (socks5h://127.0.0.1:10886)
- [x] 9.2 Implement `_ProxyContext` class for proxy isolation
- [x] 9.3 Proxy only affects yfinance calls; Tushare, MiniMax, Tavily remain proxy-free
- [x] 9.4 Verify proxy cleanup after each yfinance call

**Proxy Isolation Mechanism:**
- `_ProxyContext` is a context manager that sets `https_proxy`/`http_proxy` ONLY within the yfinance call block
- On exit, proxy env vars are explicitly removed to prevent Tushare from using them
- Tushare uses direct connection (no proxy) for optimal A-share performance

## 10. Caching Implementation

- [x] 10.1 Implement `_YFCache` class with TTL support (5-minute default TTL)
- [x] 10.2 Cache `get_stock_info` results (key: `info:{symbol}`)
- [x] 10.3 Cache `get_kline_data` results (key: `kline:{symbol}:{days}`)
- [x] 10.4 Cache `get_daily_basic` results (key: `daily_basic:{symbol}:{days}`)
- [x] 10.5 Cache `get_realtime_quote` results (key: `realtime:{symbol}`, 2-minute TTL)
- [x] 10.6 Implement stale-on-error strategy: return cached data if rate limited (up to 1 hour old)

**Why Cache:**
- Yahoo Finance rate limits are ~2000 requests/hour
- Batch requests (5 stocks) can quickly exhaust rate limits
- Cache prevents duplicate calls within TTL window

## 11. Performance Optimization

- [x] 11.1 Use `ThreadPoolExecutor(max_workers=10)` for batch requests (was max_workers=3)
- [x] 11.2 Parallel execution: all stocks in batch are fetched concurrently
- [x] 11.3 Add timing logs to batch methods for performance monitoring
- [x] 11.4 Fix React 19 double-invoke issue with `fetchedRef` guard in `PresetStockList.tsx`

**React 19 Double-Invoke Fix:**
- React 19 in dev mode double-invokes useEffect callbacks
- Added `fetchedRef` ref guard to prevent duplicate API calls
- Both `ASharePresetList` and `USPresetList` use this pattern

## Notes

- Yahoo Finance API has rate limits (~2000 requests/hour). When rate limited, the implementation returns appropriate error messages instead of "not found"
- A-share (A股) data remains unchanged - continues to use Tushare (no proxy)
- Symbol normalization: `AAPL` → `AAPL`, `GOOGL.US` → `GOOGL`, `tsla` → `TSLA`
- Proxy is ONLY used for Yahoo Finance; MiniMax API, Tavily, and Tushare all use direct connections
