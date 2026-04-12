## Context

The current trend analysis pipeline fetches price/volume OHLCV data and computes technical indicators (RSI, MACD, MA, Bollinger Bands). This data is formatted into a text context block and passed to an LLM agent for trend prediction. Tushare Pro (`daily_basic`) provides daily valuation metrics (PE TTM, PB, turnover rate, market cap) which are not yet fetched or surfaced. The existing `AkshareService` already uses Tushare Pro for price data, so adding `daily_basic` is a low-risk additive change. The frontend stock detail page currently shows technical charts but no valuation panel.

## Goals / Non-Goals

**Goals:**
- Add `get_daily_basic()` to `AkshareService` to fetch PE(TTM), PB, turnover rate, total/circulation market cap from Tushare `pro.daily_basic()`
- Expose a `/api/stock/{symbol}/valuation` endpoint returning the historical + latest valuation data
- Inject valuation context (PE, PB, turnover rate, market cap) into the LLM agent's `format_data_context()` so the agent can reason over valuation alongside price signals
- Add a frontend valuation panel on the stock analysis page with PE(TTM) sparkline, PB, turnover rate, and total market cap

**Non-Goals:**
- Historical valuation charting beyond a mini PE sparkline (full chart is separate work)
- Peer/sector PE comparison
- Automatic alerts based on valuation thresholds
- Support for non-A-share markets (no `daily_basic` equivalent for HK/US stocks in Tushare)

## Decisions

### D1: Fetch valuation in the existing analysis pipeline, not as a separate async call
**Decision**: `get_daily_basic()` is called in the same backend flow that fetches price and technical indicator data before LLM analysis.  
**Rationale**: Keeps the agent context assembly in one place and avoids frontend-initiated parallel fetches that could race. The `daily_basic` call is cheap (<100ms typical).  
**Alternative considered**: Lazy-load valuation separately in the frontend — rejected because the LLM agent needs it server-side before generating the text context.

### D2: Graceful degradation when `daily_basic` fails
**Decision**: If Tushare returns no data or raises an exception, the service returns `{"symbol": ..., "error": "..."}`. The agent context builder checks for the `error` key and skips valuation lines rather than hard-failing.  
**Rationale**: Tushare point quotas can be exhausted or the API can be temporarily unavailable. The existing technical indicators are still valid for analysis without valuation.

### D3: Expose raw `daily_basic` fields via API endpoint
**Decision**: Return both a `data` array (historical records) and a `latest` dict (most recent day) so the frontend can render a sparkline from `data` and a summary from `latest` without extra transformation.  
**Rationale**: Minimizes frontend logic; matches the pattern used by other stock data endpoints in this codebase.

### D4: PE(TTM) sparkline rendered as a lightweight inline chart
**Decision**: Use the same mini-chart component already used for price sparklines on the watchlist, passing PE values from `data`.  
**Rationale**: Reuse existing UI component to minimize new frontend code. Full charting is out of scope.

## Risks / Trade-offs

- **Tushare point consumption** → The `daily_basic` endpoint costs points per call. Mitigation: Cache results with a 30-minute TTL (same as existing price data caching strategy). If no cache exists yet, add a simple in-memory cache with `functools.lru_cache` or a dict-based TTL cache.
- **Missing data for newer/suspended stocks** → Some stocks may have gaps in `daily_basic`. Mitigation: Graceful degradation (D2) ensures no breakage; the UI shows "N/A" for missing fields.
- **LLM context length increase** → Adding ~4 lines of valuation context per stock is negligible (~50 tokens). No risk to context limits.
- **Frontend layout shift** → Adding a valuation panel below/beside the existing chart may affect layout on smaller screens. Mitigation: Use collapsible card or place it in the existing metrics row.
