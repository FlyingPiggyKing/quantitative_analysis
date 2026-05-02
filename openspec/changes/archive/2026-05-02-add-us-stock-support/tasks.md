# Implementation Tasks

## 1. Backend - Refactor akshare_service.py

- [x] 1.1 Create `AShareService` class from existing `AkshareService` methods (rename original, keep A-share specific logic)
- [x] 1.2 Create `USStockService` class with `get_stock_info()`, `get_kline_data()`, `get_realtime_quote()`, `get_daily_basic()`
- [x] 1.3 Add `_us_symbol_to_ts_code()` function in `USStockService` for US symbol normalization
- [x] 1.4 Add `get_us_daily_basic_batch()` for batch US stock valuation
- [x] 1.5 Add `get_us_stock_info_batch()` for batch US stock info
- [x] 1.6 Export both classes from `akshare_service.py` for backward compatibility

## 2. Backend - Refactor stock_trend_agent.py

- [x] 2.1 Create `AShareTrendAgent` class from existing `StockTrendAgent` methods
- [x] 2.2 Create `USStockTrendAgent` class with US-specific analysis logic
- [x] 2.3 Ensure `USStockTrendAgent` passes market type context to AI prompts
- [x] 2.4 Export both classes from `stock_trend_agent.py`

## 3. Backend - Batch API Updates

- [x] 3.1 Update batch valuation logic to route A-share symbols to `AShareService` and US symbols to `USStockService`
- [x] 3.2 Update batch info logic to route symbols by market type
- [x] 3.3 Update `/api/stock/batch/valuation` endpoint to handle mixed market requests
- [x] 3.4 Update `/api/stock/batch/info` endpoint to handle mixed market requests

## 4. Backend - Watchlist Database

- [x] 4.1 Add `market` column to `user_watchlist` table (TEXT DEFAULT 'A')
- [x] 4.2 Update `add_stock()` to accept and store market type
- [x] 4.3 Update `get_watchlist()` to filter by market type when specified
- [x] 4.4 Ensure backward compatibility for existing entries (market IS NULL = 'A')

## 5. Frontend - StockMarketTabs Component

- [x] 5.1 Create reusable `StockMarketTabs` component in `components/`
- [x] 5.2 Component accepts `aShareContent` and `usContent` render props
- [x] 5.3 Component manages active tab state (defaults to "A股")
- [x] 5.4 Component applies consistent tab styling with active state indicator

## 6. Frontend - WatchList Updates

- [x] 6.1 Wrap WatchList content in `StockMarketTabs` component
- [x] 6.2 Pass A-share stocks as `aShareContent` (filtered by market='A' or null)
- [x] 6.3 Pass US stocks as `usContent` (filtered by market='US')
- [x] 6.4 Update API calls to include market filter parameter

## 7. Frontend - PresetStockList Updates

- [x] 7.1 Add `US_PRESET_STOCKS` constant in `config/presetStocks.ts`
- [x] 7.2 Wrap PresetStockList content in `StockMarketTabs` component
- [x] 7.3 Render A-share presets in `aShareContent` (existing PRESET_STOCKS)
- [x] 7.4 Render US presets in `usContent` (new US_PRESET_STOCKS)
- [x] 7.5 Update batch API calls to use correct symbol format for each market

## 8. Frontend - Watchlist API Service

- [x] 8.1 Update `getWatchlist()` to accept optional `market` filter parameter
- [x] 8.2 Update `addStock()` to accept and send `market` parameter

## 9. Integration & Testing

- [x] 9.1 Test US stock symbol "GOOGL" fetches correct data from Tushare
- [x] 9.2 Test adding US stock to watchlist stores correct market type
- [x] 9.3 Test tab switching displays correct stock list
- [x] 9.4 Test guest view shows both A-share and US presets
- [x] 9.5 Verify existing A-share functionality unchanged
