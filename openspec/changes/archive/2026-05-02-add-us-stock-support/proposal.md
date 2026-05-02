## Why

Users want to track US stocks (Google, Microsoft, NVIDIA, Tesla, Coca-Cola) alongside their A-share holdings. Currently the system only supports Chinese A-share stocks. Adding US stock support will enable users to monitor both markets in a single interface, with AI trend analysis working across both markets.

## What Changes

- **Backend**:
  - Extend `akshare_service.py` to support US stock data fetching via Tushare Pro US stock API
  - Add US stock symbol normalization (e.g., `GOOGL` → `GOOGL.US`, `TSLA` → `TSLA.US`)
  - Add market type field to distinguish A-share vs US stocks

- **Frontend - User Watchlist**:
  - Add tab switching (A股/美股) in `WatchList` component
  - Store market type with each watchlist item
  - Filter watchlist by market when switching tabs

- **Frontend - Guest View**:
  - Add tab switching (A股/美股) in `PresetStockList` component
  - A股 tab: existing preset stocks (中国平安, 宁德时代, etc.)
  - 美股 tab: Google, Microsoft, NVIDIA, Tesla, Coca-Cola

- **Trend Analysis**:
  - Ensure batch trend analysis processes both A-share and US stocks
  - AI analysis adapts to US stock market context (different trading hours, currency, etc.)

## Capabilities

### New Capabilities
- `us-stock-data`: Fetching US stock data from Tushare Pro API, including real-time quotes, K-line data, and valuation metrics. Each US stock symbol is normalized with `.US` suffix for Tushare API calls.
- `stock-market-tabs`: Tab-based UI switching between A-share (A股) and US stock (美股) markets in both authenticated WatchList and guest PresetStockList views. Each market tab displays its respective stock list with consistent formatting.
- `us-stock-presets`: Guest view preset US stocks (GOOGL, MSFT, NVDA, TSLA, KO) displayed in the 美股 tab alongside existing A-share presets.

### Modified Capabilities
- `watch-list-display`: Modified to support market type filtering and tab-based display. The existing watchlist columns and PE trend functionality remain unchanged.
- `batch-stock-valuation-query`: Extended to handle mixed A-share and US stock symbols in batch requests without breaking existing A-share functionality.

## Impact

- **Backend**: `backend/services/akshare_service.py` - refactored into `AShareService` and `USStockService` classes
- **Backend**: `backend/services/stock_trend_agent.py` - refactored into `AShareTrendAgent` and `USStockTrendAgent` classes
- **Backend**: `backend/services/watchlist_service.py` - may need market type column
- **Frontend**: `frontend/src/components/WatchList.tsx` - tab switching UI
- **Frontend**: `frontend/src/components/PresetStockList.tsx` - tab switching and US presets
- **Frontend**: `frontend/src/components/StockMarketTabs.tsx` - new reusable tab component
- **Frontend**: `frontend/src/config/presetStocks.ts` - US stock preset configuration
- **API**: No new endpoints required; existing endpoints work with US stock symbols
