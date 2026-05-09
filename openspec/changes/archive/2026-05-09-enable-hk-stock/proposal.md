## Why

Enable Hong Kong (HK) stock market data via the existing Futu OpenAPI infrastructure, providing parity with US stock functionality. HK stocks are commonly requested (e.g., 00700 for Tencent, 9988 for Alibaba) and can be served through the same Futu OpenD connection already used for US stocks, with no impact on existing A-share or US stock services.

## What Changes

- Add HK stock market to `FutuQuoteService` — same service class, differentiated by market prefix `HK.` instead of `US.`
- Add `_is_hk_stock_symbol()` detection: 4-5 digit symbols (e.g., `00700`, `9988`) that are not 6-digit A-share codes
- Add `HKStockService` wrapper mirroring `USStockService` structure in `akshare_service.py`
- Extend symbol routing in all stock service functions to include HK stock detection
- Batch endpoints already support mixed markets — no changes needed to batch logic
- No changes to API routes (the routing is symbol-based, not market-based in the route layer)

## Capabilities

### New Capabilities
- `hk-stock-data`: Enable HK stock data (info, K-line, realtime quote, valuation metrics) via Futu OpenAPI. Mirrors `us-stock-data` capability with market identifier `HK` and Futu code prefix `HK.`.

### Modified Capabilities
- (none — all changes are additive and backward-compatible)

## Impact

- **New file**: `backend/services/futu_quote_service.py` — extended with HK symbol conversion (`_symbol_to_hk_futu_code`, `_hk_futu_code_to_symbol`), market parameter added to `get_snapshot`/`get_stock_info` to return `market: "HK"`
- **Modified file**: `backend/services/akshare_service.py` — add `_is_hk_stock_symbol()`, `HKStockService` class, update routing in `get_stock_info`, `get_kline_data`, `get_realtime_quote`, `get_daily_basic` to dispatch HK symbols to `HKStockService`
- **No changes**: A-share (Tushare) path, US stock path, API routes, batch endpoints, frontend
- **Dependencies**: Same Futu OpenD connection; no new dependencies
