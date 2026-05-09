## Context

Currently, US stock data is fetched via Yahoo Finance through `USStockService` in `backend/services/akshare_service.py`. Yahoo Finance has known performance and reliability issues (rate limiting, slow responses). The user wants to switch to Futu OpenAPI for better performance.

**Current State:**
- `USStockService` uses `yfinance` library with `_ProxyContext` for proxy handling
- Caching via `_YFCache` with 5-minute TTL
- Data includes: stock info, K-line, realtime quotes, valuation metrics (PE, PB, turnover rate)

**Target State:**
- Replace `USStockService` implementation to use Futu OpenAPI
- Reuse existing API endpoints (`/api/stock/{symbol}/valuation`, `/api/stock/{symbol}/kline`, etc.)
- Maintain backward compatibility with existing response formats

## Goals / Non-Goals

**Goals:**
- Replace Yahoo Finance with Futu OpenAPI for US stock queries
- Maintain API contract (endpoints, response format)
- Support PE, PB, turnover rate via Futu snapshot API
- Support historical K-line data via Futu
- Support realtime quotes via Futu
- Leverage existing caching patterns

**Non-Goals:**
- Modifying A-share data fetching (continues to use Tushare)
- Supporting other markets (HK, SG) in this change
- Changing existing API endpoint signatures

## Decisions

### Decision 1: Use Futu OpenAPI SDK directly
**Chosen approach:** Use `futu-api` Python SDK via `OpenQuoteContext`

**Rationale:** Futu provides a well-documented Python SDK (`futu-api`) with:
- `get_snapshot` for PE, PB, turnover rate
- `get_kline` for historical K-line data
- `get_stock_info` for basic info
- Better reliability and performance than Yahoo Finance

**Alternatives considered:**
- Use Futu HTTP API directly: Rejected - SDK is more convenient and handles connection management
- Use yfinance with better caching: Doesn't solve the underlying reliability issue

### Decision 2: Futu connection via `OpenQuoteContext`
**Chosen approach:** Create a shared `OpenQuoteContext` connection for US stock queries

```python
from futu import OpenQuoteContext

# Create context once, reuse for multiple calls
quote_ctx = OpenQuoteContext(host=FUTU_OPEND_HOST, port=FUTU_OPEND_PORT)
```

**Rationale:**
- `OpenQuoteContext` handles connection pooling and reconnection
- Multiple stocks can be queried in a single context
- No authentication required for market data (only for trading)

**Alternatives considered:**
- Create new context per request: Inefficient, increases connection overhead
- Use environment variables for host/port: Already standard pattern in codebase

### Decision 3: Reuse existing caching mechanism
**Chosen approach:** Adapt `_YFCache` for Futu with similar TTL (5 minutes)

**Rationale:**
- Existing `_YFCache` pattern is proven and tested
- Futu API has rate limits; caching mitigates this
- Maintains consistent behavior with A-share service

### Decision 4: Map Futu response to existing API format
**Chosen approach:** Transform Futu response to match existing `USStockService` response format

**Rationale:**
- Existing frontend code expects specific field names
- Changing response format would require frontend modifications
- Futu's field names are similar enough to map easily

**Field mapping:**
- Futu snapshot fields: `pe_ttm`, `pb`, `turnover_rate`, `market_val` → existing format
- Futu K-line fields: `time`, `open`, `close`, `high`, `low`, `volume` → existing `date`, `open`, `close`, `high`, `low`, `volume`

## Risks / Trade-offs

[Risk] Futu OpenD must be running → **Mitigation**: Check OpenD connectivity at startup, show clear error if not available

[Risk] Futu API rate limits → **Mitigation**: Implement caching with 5-minute TTL, similar to existing Yahoo Finance caching

[Risk] Different data availability (Futu may not have all stocks) → **Mitigation**: Return appropriate error messages, fallback to cached data if available

[Risk] Network connectivity to Futu OpenD → **Mitigation**: Use environment variables for host/port configuration, implement retry logic

## Migration Plan

1. Add `futu-api` to `requirements.txt` (or `pyproject.toml`)
2. Add `FUTU_OPEND_HOST` and `FUTU_OPEND_PORT` to `.env`
3. Create new `FutuQuoteService` class in `backend/services/futu_quote_service.py`
4. Modify `USStockService` to delegate to `FutuQuoteService`
5. Test all endpoints with existing test cases
6. Remove `yfinance` dependency if no longer needed

## Open Questions

1. Should we support both Yahoo Finance and Futu with a fallback mechanism?
2. Do we need to handle Futu's market state (US market hours)?
3. Should we use Futu's websocket push instead of polling for realtime data?
