## Context

Currently US stocks (美股) are fetched via Tushare Pro API using `us_basic` and `us_daily` endpoints in `backend/services/akshare_service.py`. The `USStockService` class wraps these calls.

**Problem**: Tushare's US stock data has poor quality:
- Fundamental metrics (PE, PB, EPS) frequently return `null`
- K-line data reliability is inconsistent
- Data updates may be delayed

**Yahoo Finance** (via `yfinance` library) provides comprehensive US stock data with:
- Reliable `ticker.info` containing all fundamental metrics
- High-quality `ticker.history()` for OHLCV daily data
- No API token required (uses public Yahoo Finance API)

## Goals / Non-Goals

**Goals:**
- Replace Tushare US stock data with Yahoo Finance
- Maintain 100% API compatibility (same endpoints, same response format)
- Provide reliable fundamental metrics: trailingPE, priceToBook, trailingEps, dividendYield, marketCap
- A-share (A股) data via Tushare remains unchanged
- Optimize performance with caching and parallel execution

**Non-Goals:**
- Not changing frontend components
- Not modifying database schema
- Not adding new API endpoints
- Not affecting watchlist or portfolio functionality

## Decisions

### Decision 1: Use `yfinance` library over direct Yahoo Finance API

**Chosen**: `yfinance` Python package

**Alternatives considered**:
- Direct Yahoo Finance v7/v8 REST API — requires API key, more complex error handling
- `yahoo-fin` library — less maintained, fewer features
- `yfinance-mcp` — for AI agent use, not backend service

**Rationale**: `yfinance` is the de facto standard Python library for Yahoo Finance data, well-maintained, no API key required, supports both `info` (fundamentals) and `history()` (OHLCV).

### Decision 2: Keep `USStockService` class structure, replace internals

**Chosen**: Refactor `USStockService` method implementations, keep public API signature

**Rationale**: This minimizes changes to the API router in `backend/api/stock.py` which already delegates to `USStockService` based on symbol detection. No frontend changes needed.

### Decision 3: Symbol handling

**Chosen**: Keep existing `_is_us_stock_symbol()` detection and `_us_symbol_to_ts_code()` normalization

**Rationale**: These helper functions work with the existing symbol format (e.g., `AAPL`, `GOOGL.US`). Yahoo Finance accepts symbols without `.US` suffix for US exchanges. Will need to strip `.US` suffix before calling yfinance.

### Decision 4: Proxy isolation with `_ProxyContext`

**Chosen**: Use a context manager to temporarily set proxy environment variables only for yfinance calls

```python
class _ProxyContext:
    def __enter__(self):
        if self._proxy:
            os.environ["https_proxy"] = self._proxy
            os.environ["http_proxy"] = self._proxy
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._proxy:
            os.environ.pop("https_proxy", None)
            os.environ.pop("http_proxy", None)
        return False
```

**Rationale**:
- Yahoo Finance may be blocked in China; proxy (Trojan/SOCKS5) is required
- Tushare must NOT use proxy (China direct connection is faster)
- Other services (MiniMax, Tavily) must NOT use proxy (already accessible)
- The context manager ensures proxy is only set within yfinance call and cleaned up immediately after

### Decision 5: In-memory caching with stale-on-error strategy

**Chosen**: Implement `_YFCache` class with 5-minute TTL and stale-on-error fallback

```python
class _YFCache:
    def __init__(self, ttl: int = 300):
        self._ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def on_error_return_stale(self, key: str, fetch_func, max_stale_seconds: int = 3600):
        try:
            return self.get_or_fetch(key, fetch_func)
        except Exception:
            # On error (rate limit), return stale cache if available
            with self._lock:
                if key in self._cache:
                    entry = self._cache[key]
                    if time.time() - entry["timestamp"] < max_stale_seconds:
                        return entry["data"]
            raise
```

**Cache keys:**
| Method | Cache Key | TTL |
|--------|-----------|-----|
| `get_stock_info` | `info:{symbol}` | 5 min |
| `get_kline_data` | `kline:{symbol}:{days}` | 5 min |
| `get_daily_basic` | `daily_basic:{symbol}:{days}` | 5 min |
| `get_realtime_quote` | `realtime:{symbol}` | 2 min |

**Rationale**:
- Yahoo Finance rate limits (~2000 requests/hour) are easily hit with batch requests
- Caching reduces duplicate API calls within TTL window
- Stale-on-error ensures users see data even if rate limited (up to 1 hour old)
- Thread-safe implementation supports concurrent requests

### Decision 6: Parallel batch execution

**Chosen**: Use `ThreadPoolExecutor(max_workers=10)` for all batch operations

**Rationale**:
- Yahoo Finance requests have high latency (~1-5 seconds each)
- Parallel execution reduces total batch time from ~20s (sequential) to ~5s (parallel)
- max_workers=10 allows concurrent fetching of 5+ stocks efficiently
- ThreadPoolExecutor with `as_completed()` collects results as they finish

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Yahoo Finance rate limiting | Caching with stale-on-error; reduce polling frequency |
| Missing data fields | Use `.get()` with sensible defaults; log warnings for missing critical fields |
| Network failures | Graceful error handling; return meaningful error messages |
| yfinance breaking changes | Pin version in requirements.txt; monitor library releases |
| Proxy affecting other services | `_ProxyContext` isolates proxy to yfinance only |
| React 19 double-invoke | `fetchedRef` guard in frontend components |

## Migration Plan

1. **Add dependency**: Add `yfinance>=0.2.40` to `backend/pyproject.toml`
2. **Configure proxy**: Add `YF_PROXY=socks5h://127.0.0.1:10886` to `.env`
3. **Refactor USStockService**: Replace Tushare calls with yfinance equivalents
4. **Add caching**: Implement `_YFCache` with TTL and stale-on-error
5. **Test locally**: Verify all US stocks (AAPL, GOOGL, TSLA, etc.) return correct data
6. **Verify A-share unchanged**: Ensure A股 data still works via Tushare (no proxy)
7. **Deploy**: Standard deployment process, no database migration needed
8. **Rollback**: Revert to previous `akshare_service.py` if issues arise

## Service Proxy Configuration

| Service | Connection | Proxy |
|---------|------------|-------|
| Yahoo Finance (yfinance) | Via SOCKS5 proxy | `socks5h://127.0.0.1:10886` |
| Tushare (A-share) | Direct to China | None (fastest) |
| MiniMax API | Direct to api.minimax.chat | None |
| Tavily Search | Direct to tavily.dev | None |
| LangChain/LangSmith | Tracing only | None |

## Performance Benchmarks

| Operation | Before (Tushare) | After (Yahoo Finance + Cache) |
|-----------|------------------|-------------------------------|
| Single stock info | ~1-2s | ~1-3s (first), <10ms (cached) |
| 5-stock batch info | ~5-8s | ~5s parallel, <1s cached |
| Single stock kline | ~2-3s | ~2-4s (first), <10ms (cached) |
| Rate limit impact | Low (Tushare generous) | High (Yahoo 2000/hr) → mitigated by cache |

## Open Questions (Resolved)

- ~~Should we cache `ticker.info` results?~~ **Yes** - implemented with 5-min TTL and stale-on-error
- ~~Do we need to support batch fetching?~~ **Yes** - using ThreadPoolExecutor for parallel requests
