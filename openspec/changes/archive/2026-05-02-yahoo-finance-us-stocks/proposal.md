## Why

Currently US stocks (美股) data is fetched via Tushare Pro API using `us_basic` and `us_daily` endpoints. However, Tushare's US stock data has limited fundamental metrics (PE, PB, EPS often return `null`) and unreliable K-line data quality. Yahoo Finance provides comprehensive, well-maintained US stock data with excellent availability of valuation metrics and historical OHLCV data.

## What Changes

- **Replace** `USStockService` data source from Tushare to Yahoo Finance for US stocks
- **Keep A-share (A股) data unchanged** — continues to use Tushare via `AShareService`
- **Add** `yfinance` Python package as a new dependency
- **Enhance** US stock fundamental data with reliable: `trailingPE`, `priceToBook`, `trailingEps`, `dividendYield`, `marketCap`
- **Improve** daily K-line (OHLCV) data quality using `ticker.history()`
- **API compatibility maintained** — existing endpoints `/api/stock/{symbol}` and `/api/stock/{symbol}/kline` unchanged

## Capabilities

### New Capabilities
- `yahoo-finance-data-source`: Fetch US stock fundamental metrics and historical K-line data from Yahoo Finance API. Covers `ticker.info` for fundamentals and `ticker.history()` for OHLCV daily data.

### Modified Capabilities
- `us-stock-data`: Change data provider from Tushare to Yahoo Finance. Existing spec behavior (API endpoints, data format) remains the same — only the upstream source changes.

## Impact

**Code changes:**
- `backend/services/akshare_service.py` — `USStockService` class refactored to use `yfinance`
- `backend/requirements.txt` or `pyproject.toml` — add `yfinance` dependency

**No breaking changes:**
- Frontend unchanged (same API interface)
- A-share functionality unchanged
- Database schema unchanged
