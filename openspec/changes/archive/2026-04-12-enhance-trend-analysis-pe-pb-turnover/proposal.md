## Why

The trend analysis agent currently relies solely on price and volume-based technical indicators (RSI, MACD, MA, Bollinger Bands). Without valuation context, the agent cannot distinguish a cheap oversold stock from an expensive one—making RSI=30 on a PE=100 stock indistinguishable from RSI=30 on a PE=8 stock. Adding PE(TTM), PB, and turnover rate (换手率) from Tushare's `daily_basic` API provides the missing valuation layer that A-share traders rely on heavily for short-term and medium-term signals.

## What Changes

- **New**: `get_daily_basic()` method in `AkshareService` fetches PE(TTM), PB, turnover rate, total market cap, circulation market cap from Tushare `pro.daily_basic()`
- **New**: `/api/stock/{symbol}/valuation` REST endpoint exposing daily valuation metrics
- **Modified**: LLM agent context builder (`format_data_context`) includes latest valuation metrics so the agent reasons over PE, PB, and turnover alongside price signals
- **New**: Frontend valuation section on the stock detail/analysis page displaying PE(TTM), PB, turnover rate, and total market cap with mini sparkline for PE history

## Capabilities

### New Capabilities
- `stock-valuation-metrics`: Fetch and expose daily valuation metrics (PE TTM, PB, turnover rate, total market cap, circulation market cap) per stock via Tushare daily_basic API

### Modified Capabilities
- `stock-trend-analysis-agent`: LLM agent context now includes valuation metrics (PE, PB, turnover rate) alongside existing technical indicators, enabling valuation-aware trend reasoning

## Impact

- **Backend**: `app/services/akshare_service.py` — new static method; `app/routers/stock.py` — new endpoint; `app/services/agent_service.py` (or equivalent) — updated context builder
- **Frontend**: Stock analysis/detail page component — new valuation section with sparkline
- **Dependencies**: Tushare Pro API (already integrated), requires 120+ points for `daily_basic` access
- **No breaking changes**: Additive only; existing endpoints and agent behavior unaffected if valuation data is unavailable
