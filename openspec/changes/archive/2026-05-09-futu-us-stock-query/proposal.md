## Why

Currently, US stock data (PE, PB, turnover rate, K-line) is fetched via Yahoo Finance, which has poor performance and reliability issues. Futu OpenAPI provides a faster, more reliable alternative with comprehensive US stock data including real-time quotes, valuation metrics, and historical K-line data.

## What Changes

- Replace Yahoo Finance data fetching with Futu OpenAPI for US stock queries
- Support fetching PE, PB, turnover rate via Futu snapshot API
- Support fetching historical K-line data (daily, weekly, monthly) via Futu
- Support US stock real-time quotes and basic info via Futu
- Maintain API compatibility with existing `/api/stock/{symbol}/valuation` and `/api/stock/{symbol}/kline` endpoints

## Capabilities

### New Capabilities

- `futu-us-stock-query`: Fetch US stock valuation metrics (PE, PB, turnover rate) and K-line data via Futu OpenAPI. Replaces the existing tushare-based `us-stock-data` capability for real-time queries.

### Modified Capabilities

- `us-stock-data`: Change data source from Tushare Pro to Futu OpenAPI for better performance and reliability on US stock data. No change to API contract (endpoints remain the same).

## Impact

- **Files modified**: `services/stock_query.py`, `services/us_stock_data.py`, or equivalent
- **Dependencies**: Requires `futu-api` Python SDK >= 10.4.6408, OpenD running
- **API endpoints unchanged**: `/api/stock/{symbol}/valuation`, `/api/stock/{symbol}/kline` continue to work
- **Configuration**: New env vars `FUTU_OPEND_HOST`, `FUTU_OPEND_PORT` for OpenD connection
