## Why

The index page exhibits a classic N+1 query problem: displaying a watchlist or preset stock list requires making one API request per stock to fetch valuation data. The logs show 20+ sequential requests (4 stocks × 2 requests + watchlist) when loading the page. This causes slow page loads, excessive network overhead, and puts unnecessary load on the Tushare API.

## What Changes

- **New batch API endpoint**: Add `/api/stock/batch/valuation` that accepts multiple stock symbols in a single request
- **New batch stock info endpoint**: Add `/api/stock/batch/info` that accepts multiple stock symbols in a single request
- **Backend batch service**: Modify `AkshareService` to support batch fetching of daily_basic data from Tushare
- **Frontend refactor**: Update `WatchList.tsx` and `PresetStockList.tsx` to use batch APIs instead of per-stock requests
- **Database caching (optional)**: Consider caching valuation data to reduce Tushare API calls

## Capabilities

### New Capabilities
- `batch-stock-valuation-query`: Batch query endpoint to fetch valuation metrics for multiple stocks in a single request. Accepts a list of stock symbols and returns aggregated valuation data for all symbols.

### Modified Capabilities
- `stock-valuation-metrics`: Add batch query support to existing valuation metrics capability - the single-symbol endpoint remains, but a new batch endpoint is added alongside it.

## Impact

- **Backend**: New batch endpoints in `backend/api/stock.py`, modified `AkshareService.get_daily_basic()` to support batch operations
- **Frontend**: Refactored `WatchList.tsx` and `PresetStockList.tsx` components to use batch APIs
- **Performance**: Reduces index page load from N+1 requests to 1-3 requests (batch valuation + batch info)
