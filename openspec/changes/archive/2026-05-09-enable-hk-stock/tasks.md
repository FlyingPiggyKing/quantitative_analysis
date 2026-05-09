## 1. Symbol Conversion (FutuQuoteService)

- [x] 1.1 Add `_symbol_to_hk_futu_code(symbol)` function in `futu_quote_service.py` — converts `00700` → `HK.00700`, preserves `HK.00700` as-is, strips leading zeros NOT
- [x] 1.2 Add `_hk_futu_code_to_symbol(futu_code)` function in `futu_quote_service.py` — converts `HK.00700` → `00700`
- [x] 1.3 Verify existing `_symbol_to_futu_code` (US) is unchanged

## 2. Market Field in Responses (FutuQuoteService)

- [x] 2.1 Update `get_stock_info` to return `market: "HK"` for HK stock responses (pass a market parameter or detect from symbol)
- [x] 2.2 Update `get_realtime_quote` to return `market: "HK"` for HK stock responses
- [x] 2.3 Update `get_snapshot` to include market in response

## 3. HK Symbol Detection (akshare_service.py)

- [x] 3.1 Add `_is_hk_stock_symbol(symbol)` function — returns `True` for 4-5 digit symbols, `False` for 6-digit (A-share) or letter (US) symbols
- [x] 3.2 Test detection: `00700` → True, `9988` → True, `600938` → False, `AAPL` → False

## 4. HKStockService Wrapper (akshare_service.py)

- [x] 4.1 Add `HKStockService` class mirroring `USStockService` structure — methods: `get_stock_info`, `get_kline_data`, `get_realtime_quote`, `get_daily_basic`, `get_daily_basic_batch`, `get_stock_info_batch`
- [x] 4.2 Each method delegates to `FutuQuoteService` with the appropriate HK symbol

## 5. Service Layer Routing (akshare_service.py)

- [x] 5.1 Update `get_stock_info` routing to include HK: `if _is_hk_stock_symbol(symbol): return HKStockService.get_stock_info(symbol)`
- [x] 5.2 Update `get_kline_data` routing to include HK
- [x] 5.3 Update `get_realtime_quote` routing to include HK
- [x] 5.4 Update `get_daily_basic` routing to include HK
- [x] 5.5 Verify A-share routing (Tushare) is unchanged

## 6. Verification

- [x] 6.1 Restart backend and verify no import errors
- [x] 6.2 Test `GET /api/stock/00700` — returns `{"symbol":"00700","name":"TENCENT","market":"HK","sector":"未知"}`
- [x] 6.3 Test `GET /api/stock/00700/kline?days=10` — returns K-line data with date, open, close, high, low, volume, change_pct
- [x] 6.4 Test `GET /api/stock/00700/realtime` — returns `{"symbol":"00700","name":"TENCENT","market":"HK","price":471.4,"change_pct":-1.256...}`
- [x] 6.5 Test `GET /api/stock/00700/valuation` — returns valuation metrics with pe_ttm, pb, turnover_rate, total_mv
- [x] 6.6 Test `GET /api/stock/00700/indicators` — returns MACD, RSI, MA indicators
- [x] 6.7 Verify US stock `GET /api/stock/AAPL` still works and returns `market="US"`
- [x] 6.8 Verify A-share `GET /api/stock/600938` still works and returns `market="A"`
