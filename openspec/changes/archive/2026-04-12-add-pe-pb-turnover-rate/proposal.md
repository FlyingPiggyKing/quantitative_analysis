## Why

Traders monitoring stocks need quick access to valuation metrics (PE, PB) and liquidity data (turnover rate) to make informed decisions. Currently, the watch list and stock detail pages lack these fundamental metrics, requiring users to manually look up this information elsewhere.

## What Changes

- **Watch List Enhancement**: Add PE and PB columns showing the latest available values (today or most recent trading day)
- **Stock Detail Page Enhancement**: Display current PE, PB, and turnover rate in the header area
- **PE/PB Charts**: Add daily PE and PB line charts below the existing volume histogram on the detail page
- **New API Endpoint**: Create backend endpoint to fetch PE, PB, and turnover rate data series for charting

## Capabilities

### New Capabilities

- `stock-valuation-metrics`: Fetch and display PE (Price-to-Earnings), PB (Price-to-Book), and turnover rate (换手率) data from Tushare Pro API. Includes:
  - Current/latest value display on watch list and detail page
  - Historical daily values for charting
  - Graceful handling when data is unavailable (e.g., new listings without PE)

### Modified Capabilities

- `kline-chart`: Extend the chart component to support additional line series (PE, PB) displayed below the volume histogram
- `stock-query`: Minor extension to include valuation metrics in stock info responses where applicable

## Impact

- **Backend**: New service method in `akshare_service.py` to fetch valuation data via Tushare `daily_basic` endpoint
- **API**: New endpoint `/api/stock/{symbol}/valuation` returning current metrics and historical daily series
- **Frontend Components**:
  - `WatchList.tsx`: Add PE, PB columns to the table
  - `StockChart.tsx`: Extend to support additional line chart series for PE/PB
  - `stock/[symbol]/page.tsx`: Add valuation metrics display in header and new chart section
- **Dependencies**: Tushare Pro API token required (already in use for existing stock data)
